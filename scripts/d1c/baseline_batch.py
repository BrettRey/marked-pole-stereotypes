#!/usr/bin/env python3
"""Run the fixed 12-cell extension; preserve the running paired batch."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import d1c
import grid
import paired_batch as paired
from assemble_cut import ReadOnlyComponents, replay
from collect_parallel import verify_component
from component_state import ComponentState
from hf_batch import dispatch
from run_component import run_one, verify_published_source
from run_state import atomic_json, digest

ROOT = d1c.ROOT
BATCH = ROOT / "results/d1c/baseline-batch-20261010"
CUT_CELLS = (6, 18, 22, 126, 138, 142)
JOINT_CELLS = (0, 12, 16, 120, 132, 136)
REUSED_CELLS = (4, 10, 124, 130)
PATHS = (*paired.PATHS, "scripts/d1c/baseline_batch.py", "scripts/d1c/baseline_batch.sh",
    "scripts/d1c/BASELINE-BATCH.md", "scripts/d1c/launch_baseline_batch.py",
    "scripts/d1c/monitor_baseline_batch.py")


def jobs():
    return {c["cell"]: dict(c, rep=0) for c in d1c.cells() if c["scenario"] == "baseline"
            and c["prior"] == 1 and c["reliability"] in (0, .8)}


def module_name(cell, key):
    return f"c{cell:03d}-{key}"


def modules():
    cells, result = jobs(), {}
    for cell in JOINT_CELLS:
        result[module_name(cell, "joint")] = dict(job=cells[cell], key="joint", mode="joint", component=None)
    for cell in CUT_CELLS:
        result[module_name(cell, "upstream")] = dict(job=cells[cell], key="upstream", mode="upstream", component=None)
        for i in range(8):
            key = f"downstream-{i:03d}"
            result[module_name(cell, key)] = dict(job=cells[cell], key=key, mode="downstream", component=i)
    return result


def hosts():
    result = {}
    # Upstream hosts first so any provider capacity limit never strands them
    # behind waiting consumers. All accepted hosts run immediately.
    for cell in CUT_CELLS:
        result[f"cut-{cell:03d}-0"] = [module_name(cell, "upstream"),
            module_name(cell, "downstream-000"), module_name(cell, "downstream-001")]
    for i in range(3):
        result[f"joint-{i}"] = [module_name(c, "joint") for c in JOINT_CELLS[2*i:2*i+2]]
    for shard in range(1, 4):
        for cell in CUT_CELLS:
            result[f"cut-{cell:03d}-{shard}"] = [module_name(cell, f"downstream-{i:03d}")
                                                for i in range(2*shard, 2*shard+2)]
    return result


def specification(source):
    original = grid.specification(1, 4000, 2000, 8000)
    return dict(schema=1, source_commit=source, modules=modules(), hosts=hosts(),
        reused_cells=list(REUSED_CELLS), sampler=original["sampler"], packages=original["packages"],
        root_seed=original["root_seed"], python=sys.version, platform=platform.platform(),
        sources={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in PATHS})


def module_spec(spec, name):
    return dict(batch_signature=digest(paired.scientific_identity(spec)), **spec["modules"][name],
        sampler=spec["sampler"], sources=spec["sources"], packages=spec["packages"], root_seed=spec["root_seed"])


def check_module(directory, spec, name):
    info = spec["modules"][name]
    loaded = verify_component(directory / "checkpoints", info["key"])
    if loaded is None:
        raise ValueError(f"Incomplete module {name}")
    manifest, record, arrays = loaded
    if manifest["signature"] != digest(module_spec(spec, name)):
        raise ValueError(f"Module identity differs: {name}")
    job = info["job"]
    if info["mode"] == "upstream":
        shapes = {n: (8, 400) for n in ("z", "v", "s")}
        if job["reliability"]:
            shapes["h"] = (8, 400, 3)
        seed, draws = d1c.seed(2, job["cell"], job["rep"]), 8000
    else:
        shapes = {n: (16000,) for n in ("h2", "h1_fixed_usage", "b_z", "marking")}
        seed = (d1c.seed(2, job["cell"], job["rep"]) if info["mode"] == "joint" else
                d1c.seed(4, job["cell"], job["rep"], info["component"]))
        draws = 4000
    if set(arrays) != set(shapes) or any(a.shape != shapes[n] or not np.isfinite(a).all() for n, a in arrays.items()):
        raise ValueError(f"Invalid arrays: {name}")
    diag = record["metadata"]["diagnostic"]
    if (diag["mode"], diag["seed"], diag["draws"], diag["tune"]) != (info["mode"], seed, draws, 2000):
        raise ValueError(f"Sampler or seed differs: {name}")
    return record, arrays


def worker(source, host, name):
    verify_published_source(source, PATHS)
    grid.configure_sampler(4000, 2000, 8000)
    base = BATCH / host
    spec = json.loads((base / "specification.json").read_text())
    if spec != specification(source) or name not in spec["hosts"][host]:
        raise ValueError("Worker assignment differs")
    info = spec["modules"][name]
    directory = base / "modules" / name
    directory.mkdir(parents=True, exist_ok=False)
    runtime = dict(state="running", host=host, module=name, job=info["job"], mode=info["mode"],
        source_commit=source, pid=os.getpid(), started_at=datetime.now(timezone.utc).isoformat())
    atomic_json(directory / "runtime.json", runtime)
    started = time.monotonic()
    try:
        with ComponentState(directory / "checkpoints", module_spec(spec, name)) as store:
            if info["mode"] == "upstream":
                try:
                    d1c.fit(info["job"], components=paired.UpstreamBoundary(store))
                except paired.UpstreamReady:
                    pass
                else:
                    raise RuntimeError("Upstream boundary was not reached")
            elif info["mode"] == "downstream":
                upname = module_name(info["job"]["cell"], "upstream")
                upstream, selected = check_module(base / "modules" / upname, spec, upname)
                run_one(info["job"], info["component"], upstream["metadata"], selected, store)
            else:
                rows, status = d1c.fit(info["job"], components=store)
                _, arrays = store.load("joint")
                atomic_json(directory / "result.json", paired.clean_joint(rows, status, arrays))
        record, _ = check_module(directory, spec, name)
        runtime.update(state="complete", diagnostic=record["metadata"]["diagnostic"],
                       archive_sha256=record["archive_sha256"])
    except BaseException as exc:
        runtime.update(state="failed", error=repr(exc))
        raise
    finally:
        runtime.update(ended_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic()-started,
            peak_process_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss *
                (1 if sys.platform == "darwin" else 1024))
        atomic_json(directory / "runtime.json", runtime)


def receive_upstream(base, spec, cell, shared, pause, timeout=3600):
    owner = shared / f"cut-{cell:03d}-0"
    deadline = time.monotonic() + timeout
    while True:
        try:
            ready = json.loads((owner / "upstream-ready.json").read_text())
            break
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        try:
            state = json.loads((owner / "progress.json").read_text()).get("state")
        except (FileNotFoundError, json.JSONDecodeError):
            state = None
        if state == "failed":
            raise RuntimeError(f"Upstream host for cell {cell} failed")
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Upstream cell {cell} not published within one hour")
        pause()
    if ready["batch_signature"] != digest(paired.scientific_identity(spec)):
        raise ValueError("Different upstream batch")
    name = module_name(cell, "upstream")
    target = base / "modules" / name / "checkpoints"
    target.mkdir(parents=True, exist_ok=False)
    for filename in ("manifest.json", "component-upstream.npz", "component-upstream.json"):
        shutil.copyfile(owner / "modules" / name / "checkpoints" / filename, target / filename)
    record, _ = check_module(target.parent, spec, name)
    if record["archive_sha256"] != ready["archive_sha256"]:
        raise ValueError("Upstream checksum differs")


def assemble_cell(base, spec, cell):
    directory = base / "cells" / f"cell-{cell:03d}"
    destination = directory / "result.json"
    if destination.exists():
        return json.loads(destination.read_text())
    job = jobs()[cell]
    records, hashes = {}, {}
    for name, info in spec["modules"].items():
        if info["job"]["cell"] != cell:
            continue
        record, arrays = check_module(base / "modules" / name, spec, name)
        records[info["key"]] = (record["metadata"], arrays)
        hashes[info["key"]] = record["archive_sha256"]
    directory.mkdir(parents=True, exist_ok=True)
    if job["feedback"] == "cut":
        rows, status, stacked = replay(ReadOnlyComponents(records), job)
        np.savez_compressed(directory / "contrasts.npz", **stacked)
        result = dict(rows=rows, status=status, archive_sha256=hashes)
    else:
        if set(records) != {"joint"}:
            raise ValueError("Missing joint module")
        result = json.loads((base / "modules" / module_name(cell, "joint") / "result.json").read_text())
        result["archive_sha256"] = hashes
    atomic_json(destination, result)
    return result


def controller(source, host, destination):
    verify_published_source(source, PATHS)
    grid.configure_sampler(4000, 2000, 8000)
    spec = specification(source)
    assigned = spec["hosts"][host]
    base = BATCH / host
    base.mkdir(parents=True, exist_ok=True)
    if (base / "progress.json").exists():
        raise RuntimeError("Host already attempted; no automatic model retry")
    atomic_json(base / "specification.json", spec)
    progress = dict(state="running", host=host, assigned=assigned, source_commit=source,
                    pid=os.getpid(), started_at=datetime.now(timezone.utc).isoformat())
    copied, processes, completed_all = {}, {}, []
    def publish(pending, active, completed, failed):
        progress.update(pending=list(pending), active={n: p.pid for n,p in active.items()},
            completed=completed_all+list(completed), failed=list(failed),
            updated_at=datetime.now(timezone.utc).isoformat())
        peak = Path("/sys/fs/cgroup/memory.peak")
        if peak.exists():
            progress["container_memory_peak_bytes"] = int(peak.read_text())
        atomic_json(base / "progress.json", progress)
        paired.export_snapshot(base, destination, copied)
        print(json.dumps(progress), flush=True)
    def launch(name):
        stream = (base / f"{name}-stdout.txt").open("x")
        process = subprocess.Popen([sys.executable, "-u", str(Path(__file__).resolve()),
            "--source", source, "--host", host, "--worker", name], cwd=ROOT,
            stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        processes[name] = (process, stream)
        return process
    def valid(name):
        check_module(base / "modules" / name, spec, name)
        return True
    def pause():
        paired.export_snapshot(base, destination, copied)
        time.sleep(2)
    def interrupted(signum, frame):
        raise InterruptedError(f"Host interrupted by {signum}")
    signal.signal(signal.SIGTERM, interrupted)
    publish(assigned, {}, [], [])
    try:
        owns_upstream = spec["modules"][assigned[0]]["mode"] == "upstream"
        if host.startswith("cut-") and not owns_upstream:
            receive_upstream(base, spec, spec["modules"][assigned[0]]["job"]["cell"], destination.parent, pause)
        stages = [([assigned[0]], 1), (assigned[1:], 2)] if owns_upstream else [(assigned, 2)]
        for names, limit in stages:
            completed_all.extend(dispatch(names, launch, lambda p:p.poll(), valid, publish, pause, limit))
            if len(names) == 1 and spec["modules"][names[0]]["mode"] == "upstream":
                record, _ = check_module(base / "modules" / names[0], spec, names[0])
                paired.export_snapshot(base, destination, copied)
                atomic_json(base / "upstream-ready.json", dict(batch_signature=digest(paired.scientific_identity(spec)),
                    archive_sha256=record["archive_sha256"]))
                paired.export_snapshot(base, destination, copied)
        progress.update(state="complete", completed=completed_all)
    except BaseException as exc:
        progress.update(state="failed", error=repr(exc))
        raise
    finally:
        for process, stream in processes.values():
            if process.poll() is None:
                paired.stop_group(process)
            stream.close()
        progress.update(ended_at=datetime.now(timezone.utc).isoformat())
        atomic_json(base / "progress.json", progress)
        paired.export_snapshot(base, destination, copied)
        print(json.dumps(progress), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--host", choices=hosts(), required=True)
    parser.add_argument("--export-directory", type=Path)
    parser.add_argument("--worker", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        worker(args.source, args.host, args.worker)
    elif args.export_directory is None:
        parser.error("Persistent export directory required")
    else:
        controller(args.source, args.host, args.export_directory)


if __name__ == "__main__":
    main()
