#!/usr/bin/env python3
"""Bounded registered joint/cut comparisons with durable module checkpoints."""
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
from assemble_cut import FIELDS, ReadOnlyComponents, replay
from cloud_benchmark import stop_group
from collect_parallel import verify_component
from component_state import ComponentState
from hf_batch import dispatch
from run_component import run_one, verify_published_source
from run_state import atomic_json, digest

ROOT = d1c.ROOT
BATCH = ROOT / "results/d1c/paired-batch-20261010"
SCIENTIFIC_PATHS = tuple(grid.specification(1, 4000, 2000, 8000)["sources"])
PATHS = (*SCIENTIFIC_PATHS, "scripts/d1c/run_component.py", "scripts/d1c/assemble_cut.py",
    "scripts/d1c/collect_parallel.py", "scripts/d1c/cloud_benchmark.py", "scripts/d1c/hf_batch.py",
    "scripts/d1c/paired_batch.py", "scripts/d1c/PAIRED-BATCH.md",
    "scripts/d1c/launch_paired_batch.py", "scripts/d1c/monitor_paired_batch.py",
    "scripts/d1c/paired_batch.sh", "requirements-d1.txt")


def base_directory(location, shard=0):
    return BATCH / (f"hf-shard-{shard}" if location == "hf" else location)


def shard_modules(shard):
    if shard not in range(4):
        raise ValueError("Require one of four fixed shards")
    return [f"downstream-{i:03d}" for i in range(2*shard, 2*shard+2)]


def scientific_identity(spec):
    return {k: v for k, v in spec.items() if k not in {"python", "platform"}}


def assignments(location):
    cells = {c["cell"]: dict(c, rep=0) for c in d1c.cells()}
    if location == "local":
        return {"joint-004": dict(job=cells[4], mode="joint", component=None)}
    if location == "hf-joint":
        return {"joint-124": dict(job=cells[124], mode="joint", component=None)}
    if location == "hf":
        return {"upstream": dict(job=cells[130], mode="upstream", component=None),
                **{f"downstream-{i:03d}": dict(job=cells[130], mode="downstream", component=i) for i in range(8)}}
    raise ValueError("Unknown location")


def specification(source, location):
    base = grid.specification(1, 4000, 2000, 8000)
    return dict(schema=1, source_commit=source, location=location, modules=assignments(location),
        sampler=base["sampler"], packages=base["packages"], root_seed=base["root_seed"],
        sources={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in PATHS},
        python=sys.version, platform=platform.platform())


def module_spec(spec, name):
    return dict(batch_signature=digest(scientific_identity(spec)), **spec["modules"][name], sampler=spec["sampler"],
                sources=spec["sources"], packages=spec["packages"], root_seed=spec["root_seed"])


class UpstreamReady(Exception):
    pass


class UpstreamBoundary:
    """Use the unchanged fit function, stopping before any downstream sample."""
    def __init__(self, store):
        self.store = store

    def load(self, key):
        if key.startswith("downstream-"):
            raise UpstreamReady()
        if key != "upstream":
            raise ValueError("Unexpected upstream-boundary lookup")
        return self.store.load(key)

    def save(self, key, metadata, arrays):
        if key != "upstream":
            raise ValueError("Upstream worker cannot save downstream results")
        self.store.save(key, metadata, arrays)


def check_module(directory, spec, name):
    info = spec["modules"][name]
    key = "joint" if info["mode"] == "joint" else name
    loaded = verify_component(directory / "checkpoints", key)
    if loaded is None:
        raise ValueError(f"Missing completed module {name}")
    manifest, record, arrays = loaded
    if manifest["signature"] != digest(module_spec(spec, name)):
        raise ValueError(f"Module specification differs: {name}")
    if info["mode"] == "upstream":
        shapes = dict(z=(8, 400), v=(8, 400), s=(8, 400), h=(8, 400, 3))
        seed = d1c.seed(2, info["job"]["cell"], 0)
        draws = 8000
    else:
        shapes = {n: (16000,) for n in ("h2", "h1_fixed_usage", "marking", "b_z")}
        seed = (d1c.seed(2, info["job"]["cell"], 0) if info["mode"] == "joint" else
                d1c.seed(4, info["job"]["cell"], 0, info["component"]))
        draws = 4000
    if set(arrays) != set(shapes) or any(a.shape != shapes[n] or not np.isfinite(a).all() for n, a in arrays.items()):
        raise ValueError(f"Invalid module arrays: {name}")
    diag = record["metadata"]["diagnostic"]
    if diag["mode"] != info["mode"] or diag["seed"] != seed or diag["draws"] != draws or diag["tune"] != 2000:
        raise ValueError(f"Module seed or sampler differs: {name}")
    return record, arrays


def clean_joint(rows, status, arrays):
    clean = []
    for row in rows:
        key = "h2" if row["estimand"].startswith("h2_") else row["estimand"]
        item = {k: row[k] for k in FIELDS if k != "median"}
        item["median"] = float(np.median(arrays[key]))
        clean.append(item)
    return dict(rows=clean, status=status)


def worker(source, location, name, shard=0):
    verify_published_source(source, PATHS)
    grid.configure_sampler(4000, 2000, 8000)
    base = base_directory(location, shard)
    spec = json.loads((base / "specification.json").read_text())
    if spec != specification(source, location) or name not in spec["modules"]:
        raise ValueError("Worker specification differs")
    info = spec["modules"][name]
    directory = base / "modules" / name
    directory.mkdir(parents=True, exist_ok=False)
    runtime = dict(state="running", module=name, source_commit=source, pid=os.getpid(),
        started_at=datetime.now(timezone.utc).isoformat(), job=info["job"], mode=info["mode"])
    atomic_json(directory / "runtime.json", runtime)
    started = time.monotonic()
    try:
        with ComponentState(directory / "checkpoints", module_spec(spec, name)) as store:
            if info["mode"] == "upstream":
                try:
                    d1c.fit(info["job"], components=UpstreamBoundary(store))
                except UpstreamReady:
                    pass
                else:
                    raise RuntimeError("Upstream boundary was not reached")
            elif info["mode"] == "downstream":
                upstream, selected = check_module(base / "modules/upstream", spec, "upstream")
                run_one(info["job"], info["component"], upstream["metadata"], selected, store)
            else:
                rows, status = d1c.fit(info["job"], components=store)
                metadata, arrays = store.load("joint")
                atomic_json(directory / "result.json", clean_joint(rows, status, arrays))
        record, _ = check_module(directory, spec, name)
        runtime.update(state="complete", diagnostic=record["metadata"]["diagnostic"],
                       archive_sha256=record["archive_sha256"])
    except BaseException as exc:
        runtime.update(state="failed", error=repr(exc))
        raise
    finally:
        runtime.update(ended_at=datetime.now(timezone.utc).isoformat(),
            elapsed_seconds=time.monotonic()-started,
            peak_process_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss *
                (1 if sys.platform == "darwin" else 1024))
        atomic_json(directory / "runtime.json", runtime)


def export_snapshot(source, destination, copied):
    """Export only this run; complete archives precede their JSON markers."""
    if destination is None:
        return
    files = [p for p in source.rglob("*") if p.is_file() and p.suffix in {".json", ".npz", ".txt", ".md", ".csv"}]
    def order(p):
        return (0 if p.suffix == ".npz" else 1 if p.name == "manifest.json" else
                2 if p.name.startswith("component-") else 3, str(p))
    for p in sorted(files, key=order):
        stat = p.stat()
        identity = (stat.st_mtime_ns, stat.st_size)
        if copied.get(str(p)) == identity:
            continue
        if p.suffix == ".json" and p.name.startswith("component-"):
            verify_component(p.parent, p.stem.removeprefix("component-"))
        target = destination / p.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = p.read_bytes()
        target.write_bytes(payload)
        # Logs can grow while copied; completed/checkpoint files are immutable
        # or replaced atomically by the writer and are checked byte for byte.
        if p.suffix != ".txt" and hashlib.sha256(payload).digest() != hashlib.sha256(target.read_bytes()).digest():
            raise OSError(f"Export changed while copying: {p.name}")
        copied[str(p)] = identity


def final_results(base, spec):
    if spec["location"] != "hf":
        results = []
        for name in spec["modules"]:
            check_module(base / "modules" / name, spec, name)
            results.append(json.loads((base / "modules" / name / "result.json").read_text()))
    else:
        records, provenance = {}, {}
        for name in spec["modules"]:
            record, arrays = check_module(base / "modules" / name, spec, name)
            records[name] = (record["metadata"], arrays)
            provenance[name] = record["archive_sha256"]
        rows, status, stacked = replay(ReadOnlyComponents(records), spec["modules"]["upstream"]["job"])
        np.savez_compressed(base / "cut-contrasts.npz", **stacked)
        results = [dict(rows=rows, status=status, components=provenance)]
    atomic_json(base / "results.json", dict(results=results, source_commit=spec["source_commit"],
        note="One artificial dataset per design; joint/cut fits are paired, not replications."))


def receive_upstream(base, spec, shared, pause, timeout=3600):
    deadline = time.monotonic() + timeout
    marker = shared / "hf-shard-0/upstream-ready.json"
    while True:
        try:
            ready = json.loads(marker.read_text())
            break
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        failed = shared / "hf-shard-0/progress.json"
        try:
            upstream_state = json.loads(failed.read_text()).get("state")
        except (FileNotFoundError, json.JSONDecodeError):
            upstream_state = None
        if upstream_state == "failed":
            raise RuntimeError("Upstream host failed; no downstream fit started")
        if time.monotonic() >= deadline:
            raise TimeoutError("Upstream was not published within one hour")
        pause()
    if ready["batch_signature"] != digest(scientific_identity(spec)):
        raise ValueError("Shared upstream belongs to a different batch")
    target = base / "modules/upstream/checkpoints"
    target.mkdir(parents=True, exist_ok=False)
    for name in ("manifest.json", "component-upstream.npz", "component-upstream.json"):
        shutil.copyfile(shared / "hf-shard-0/modules/upstream/checkpoints" / name, target / name)
    record, _ = check_module(target.parent, spec, "upstream")
    if record["archive_sha256"] != ready["archive_sha256"]:
        raise ValueError("Shared upstream checksum differs")


def controller(source, location, destination, shard=0):
    verify_published_source(source, PATHS)
    grid.configure_sampler(4000, 2000, 8000)
    base = base_directory(location, shard)
    base.mkdir(parents=True, exist_ok=True)
    if (base / "progress.json").exists():
        raise RuntimeError("Batch already attempted; inspect instead of automatically restarting")
    spec = specification(source, location)
    atomic_json(base / "specification.json", spec)
    progress = dict(state="running", location=location, source_commit=source, pid=os.getpid(),
                    shard=shard, started_at=datetime.now(timezone.utc).isoformat(),
                    assigned=(list(spec["modules"]) if location != "hf" else
                              (["upstream"] if shard == 0 else []) + shard_modules(shard)))
    copied, processes, all_completed = {}, {}, []
    def publish(pending, active, completed, failed):
        progress.update(pending=list(pending), active={n: p.pid for n, p in active.items()},
            completed=all_completed + list(completed), failed=list(failed),
            updated_at=datetime.now(timezone.utc).isoformat())
        peak = Path("/sys/fs/cgroup/memory.peak")
        if peak.exists():
            progress["container_memory_peak_bytes"] = int(peak.read_text())
        atomic_json(base / "progress.json", progress)
        export_snapshot(base, destination, copied)
        print(json.dumps(progress), flush=True)
    def launch(name):
        log = base / f"{name}-stdout.txt"
        stream = log.open("x")
        process = subprocess.Popen([sys.executable, "-u", str(Path(__file__).resolve()),
            "--source", source, "--location", location, "--shard", str(shard), "--worker", name], cwd=ROOT,
            stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        processes[name] = (process, stream)
        return process
    def valid(name):
        check_module(base / "modules" / name, spec, name)
        return True
    def pause():
        export_snapshot(base, destination, copied)
        time.sleep(2)
    def interrupted(signum, frame):
        raise InterruptedError(f"Batch interrupted by signal {signum}")
    signal.signal(signal.SIGTERM, interrupted)
    publish(progress["assigned"], {}, [], [])
    try:
        if location == "hf" and shard != 0:
            receive_upstream(base, spec, destination.parent, pause)
        stages = ([(list(spec["modules"]), 1)] if location != "hf" else
                  ([(["upstream"], 1)] if shard == 0 else []) + [(shard_modules(shard), 2)])
        for modules, limit in stages:
            completed = dispatch(modules, launch, lambda p: p.poll(), valid, publish, pause, limit)
            all_completed.extend(completed)
            if modules == ["upstream"]:
                record, _ = check_module(base / "modules/upstream", spec, "upstream")
                export_snapshot(base, destination, copied)
                # Created only after the complete immutable archive is exported.
                atomic_json(base / "upstream-ready.json", dict(
                    batch_signature=digest(scientific_identity(spec)), archive_sha256=record["archive_sha256"]))
                export_snapshot(base, destination, copied)
        if location != "hf":
            final_results(base, spec)
        progress.update(state="complete", completed=all_completed)
    except BaseException as exc:
        progress.update(state="failed", error=repr(exc))
        raise
    finally:
        for process, stream in processes.values():
            if process.poll() is None:
                stop_group(process)
            stream.close()
        progress.update(ended_at=datetime.now(timezone.utc).isoformat())
        atomic_json(base / "progress.json", progress)
        export_snapshot(base, destination, copied)
        print(json.dumps(progress), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--location", choices=["local", "hf", "hf-joint"], required=True)
    parser.add_argument("--export-directory", type=Path)
    parser.add_argument("--worker", help=argparse.SUPPRESS)
    parser.add_argument("--shard", type=int, choices=range(4), default=0)
    args = parser.parse_args()
    if args.worker:
        worker(args.source, args.location, args.worker, args.shard)
    else:
        if args.location != "local" and args.export_directory is None:
            parser.error("HF requires persistent exports")
        controller(args.source, args.location, args.export_directory, args.shard)


if __name__ == "__main__":
    main()
