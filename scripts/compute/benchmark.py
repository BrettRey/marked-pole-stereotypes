#!/usr/bin/env python3
"""Bounded hardware repeats of archived fits; never calibration replicates."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/d1c"))
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
from run_state import atomic_json, digest

ARCHIVE_COMMIT = "b54f265f57197b81d6ba43f6c6701246052b1174"
UPSTREAM = "results/d1c/baseline-batch-20261010/collected/modules/c142-upstream/checkpoints"
JOINT = "results/d1c/baseline-recovery-20261011/collected/modules/c012-joint/checkpoints"
UPSTREAM_HASH = "28683a3209b6dfadb1054d1f8bbae142e4cf5a37816fd2cf902e4c0c6984af3e"
PROFILES = {
    "hf-two": dict(workers=2, components=list(range(6)), cell=142, mode="downstream", hours=11.5, rss_gib=28),
    "hf-three": dict(workers=3, components=list(range(6)), cell=142, mode="downstream", hours=11.5, rss_gib=28),
    "colab-one": dict(workers=1, components=[0], cell=12, mode="joint", hours=6, rss_gib=10),
}
PATHS = ("scripts/compute/benchmark.py", "scripts/compute/README.md", "scripts/compute/launch_packing.py",
         "scripts/compute/colab_bootstrap.py",
         "requirements-d1.txt", "scripts/d1c/d1c.py", "scripts/d1c/grid.py",
         "scripts/d1c/run_state.py", "scripts/d1c/component_state.py", "scripts/d1c/run_component.py",
         "scripts/d1c/diagnostic_chunks.py", "scripts/d1c/collect_parallel.py",
         "scripts/d1c/paired_batch.py", "scripts/d1c/cloud_benchmark.py", "scripts/d1/bin/clang++")


def now():
    return datetime.now(timezone.utc).isoformat()


def specification(profile):
    import d1c
    import grid
    settings = PROFILES[profile]
    reference = UPSTREAM if settings["mode"] == "downstream" else JOINT
    archived = json.loads((ROOT / reference / "manifest.json").read_text())["specification"]
    current = grid.specification(1, 4000, 2000, 8000)
    for key in ("sampler", "packages", "root_seed"):
        if current[key] != archived[key]:
            raise ValueError(f"Archived {key} differs")
    for path, checksum in current["sources"].items():
        if checksum != archived["sources"][path]:
            raise ValueError(f"Archived scientific source differs: {path}")
    job = dict(next(c for c in d1c.cells() if c["cell"] == settings["cell"]), rep=0)
    if job != archived["job"]:
        raise ValueError("Archived job differs")
    return dict(profile=profile, purpose="hardware timing and portability only", calibration_replicate=False,
                job=job, settings=settings, reference=reference, retries=0,
                **{k: current[k] for k in ("sampler", "packages", "root_seed")},
                sources={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in PATHS},
                upstream_sha256=UPSTREAM_HASH if settings["mode"] == "downstream" else None)


def import_upstream(directory):
    from collect_parallel import verify_component
    for name in ("manifest.json", "component-upstream.json", "component-upstream.npz"):
        payload = subprocess.run(["git", "show", f"{ARCHIVE_COMMIT}:{UPSTREAM}/{name}"],
                                 cwd=ROOT, check=True, capture_output=True).stdout
        (directory / name).write_bytes(payload)
    _, record, arrays = verify_component(directory, "upstream")
    if record["archive_sha256"] != UPSTREAM_HASH:
        raise ValueError("Upstream archive differs")
    return record["metadata"], arrays


def worker(profile, component, base):
    import d1c
    import grid
    import numpy as np
    from component_state import ComponentState
    from run_component import run_one
    spec = json.loads((base / "specification.json").read_text())
    if spec != specification(profile) or component not in spec["settings"]["components"]:
        raise ValueError("Worker specification differs")
    grid.configure_sampler(4000, 2000, 8000)
    directory = base / f"component-{component:03d}"
    directory.mkdir(exist_ok=False)
    report = dict(state="running", started_at=now(), component=component, job=spec["job"])
    started = time.monotonic()
    atomic_json(directory / "runtime.json", report)
    try:
        with ComponentState(directory / "checkpoints", dict(spec, component=component)) as store:
            if spec["settings"]["mode"] == "downstream":
                upstream = directory / "upstream"
                upstream.mkdir()
                metadata, selected = import_upstream(upstream)
                result = run_one(spec["job"], component, metadata, selected, store)
                key = f"downstream-{component:03d}"
            else:
                _, status = d1c.fit(spec["job"], components=store)
                report["diagnostic_status"] = status["status"]
                key = "joint"
                result, _ = store.load(key)
            _, arrays = store.load(key)
            if (set(arrays) != {"h2", "h1_fixed_usage", "b_z", "marking"}
                    or any(a.shape != (16000,) or not np.isfinite(a).all() for a in arrays.values())):
                raise ValueError("Incomplete contrast archive")
            diagnostic = result["diagnostic"]
            report.update(state="complete", diagnostic=diagnostic,
                          archive_sha256=store.records[key]["archive_sha256"])
    except BaseException as error:
        report.update(state="failed", error=repr(error))
        raise
    finally:
        report.update(ended_at=now(), elapsed_seconds=time.monotonic()-started,
                      peak_process_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss *
                      (1 if sys.platform == "darwin" else 1024))
        atomic_json(directory / "runtime.json", report)


def rss_for_groups(pids):
    listing = subprocess.run(["ps", "-axo", "pgid=,rss="], check=True, capture_output=True,
                             text=True, timeout=10).stdout
    return sum(int(rss)*1024 for group, rss in (line.split() for line in listing.splitlines())
               if int(group) in pids)


def controller(profile, source, destination=None):
    from cloud_benchmark import stop_group
    from paired_batch import export_snapshot
    from run_component import verify_published_source
    verify_published_source(source, PATHS)
    spec = specification(profile)
    settings = spec["settings"]
    base = ROOT / "results/compute/20261011" / profile
    base.mkdir(parents=True, exist_ok=False)
    atomic_json(base / "specification.json", spec)
    report = dict(state="running", source_commit=source, profile=profile, calibration_replicate=False,
                  started_at=now(), workers=settings["workers"], pending=list(settings["components"]),
                  completed=[], failed=[], peak_sampled_group_rss_bytes=0, platform=platform.platform(),
                  python=sys.version, cpu_count=os.cpu_count(), automatic_retries=0)
    report["packages"] = {line.split("==")[0]: version(line.split("==")[0])
                          for line in (ROOT / "requirements-d1.txt").read_text().splitlines() if "==" in line}
    meminfo = Path("/proc/meminfo")
    report["initial_memory"] = meminfo.read_text() if meminfo.exists() else None
    active, streams, copied = {}, {}, {}
    started, last_export = time.monotonic(), -float("inf")

    def publish():
        report.update(active={str(c): p.pid for c, p in active.items()}, updated_at=now(),
                      elapsed_seconds=time.monotonic()-started)
        atomic_json(base / "receipt.json", report)

    def export():
        try:
            export_snapshot(base, destination, copied)
            return True
        except OSError as error:
            with (base / "export-errors.txt").open("a") as stream:
                stream.write(f"{now()} {error!r}\n")
            return False

    def interrupted(signum, frame):
        raise InterruptedError(f"Signal {signum}")

    signal.signal(signal.SIGTERM, interrupted)
    try:
        while report["pending"] or active:
            if time.monotonic()-started >= settings["hours"]*3600:
                raise TimeoutError("Fixed benchmark time limit reached")
            rss = rss_for_groups({p.pid for p in active.values()})
            report["peak_sampled_group_rss_bytes"] = max(report["peak_sampled_group_rss_bytes"], rss)
            if rss >= settings["rss_gib"]*2**30:
                raise MemoryError("Fixed aggregate worker RSS limit reached")
            while report["pending"] and len(active) < settings["workers"] and not report["failed"]:
                component = report["pending"].pop(0)
                streams[component] = (base / f"component-{component:03d}-stdout.txt").open("x")
                active[component] = subprocess.Popen([sys.executable, "-u", __file__, "--profile", profile,
                    "--source", source, "--worker", str(component)], cwd=ROOT, stdout=streams[component],
                    stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
            for component, process in list(active.items()):
                if process.poll() is None:
                    continue
                del active[component]
                path = base / f"component-{component:03d}" / "runtime.json"
                valid = process.returncode == 0 and path.exists() and json.loads(path.read_text())["state"] == "complete"
                report["completed" if valid else "failed"].append(component)
                streams[component].close()
            publish()
            if time.monotonic()-last_export >= 30:
                export()
                print(json.dumps(report), flush=True)
                last_export = time.monotonic()
            if report["failed"] and not active:
                raise RuntimeError("Worker failure; pending modules will not start; no retries")
            if active:
                time.sleep(5)
        report["state"] = "complete"
    except BaseException as error:
        report.update(state="failed", error=repr(error))
    finally:
        for process in active.values():
            stop_group(process)
        for stream in streams.values():
            stream.close()
        report.update(ended_at=now(), unfinished_active=list(active))
        active.clear()
        publish()
        # Retry storage only. Never rerun a fit following storage failure.
        for attempt in range(20):
            if export():
                break
            time.sleep(15)
        else:
            report["export_failed"] = True
            publish()
    return 0 if report["state"] == "complete" and not report.get("export_failed") else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--export", type=Path)
    parser.add_argument("--worker", type=int)
    args = parser.parse_args()
    if args.worker is not None:
        worker(args.profile, args.worker, ROOT / "results/compute/20261011" / args.profile)
        return 0
    if args.check:
        print(json.dumps(specification(args.profile), indent=2))
        return 0
    return controller(args.profile, args.source, args.export)


if __name__ == "__main__":
    raise SystemExit(main())
