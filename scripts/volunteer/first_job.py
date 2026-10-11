#!/usr/bin/env python3
"""One archived fit for volunteer timing; never contributes a calibration replicate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/d1c"))
from cloud_benchmark import stop_group
from run_state import atomic_json

ASSIGNMENT = "volunteer-001-timing-20261011"
DIRECTORY = ROOT / "results/volunteer" / ASSIGNMENT
REFERENCE = "results/d1c/baseline-recovery-20261011/collected/modules/c012-joint/checkpoints/manifest.json"
MAX_SECONDS = 6 * 3600
RSS_LIMIT = 10 * 2**30
PATHS = ("scripts/volunteer/first_job.py", "scripts/volunteer/preflight.py",
         "scripts/volunteer/FIRST-JOB.md", "scripts/d1c/d1c.py", "scripts/d1c/grid.py",
         "scripts/d1c/run_state.py", "scripts/d1c/component_state.py",
         "scripts/d1c/diagnostic_chunks.py", "scripts/d1c/cloud_benchmark.py",
         "scripts/d1c/run_component.py", "scripts/d1/bin/clang++", "requirements-d1.txt", REFERENCE)


def now():
    return datetime.now(timezone.utc).isoformat()


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def specification():
    import d1c
    import grid
    archived = json.loads((ROOT / REFERENCE).read_text())["specification"]
    current = grid.specification(1, 4000, 2000, 8000)
    job = dict(next(c for c in d1c.cells() if c["cell"] == 12), rep=0)
    for name in ("sampler", "packages", "root_seed"):
        if current[name] != archived[name]:
            raise ValueError(f"Archived {name} differs")
    if job != archived["job"]:
        raise ValueError("Archived job differs")
    for path, actual in current["sources"].items():
        if actual != archived["sources"][path]:
            raise ValueError(f"Archived scientific source differs: {path}")
    return dict(assignment=ASSIGNMENT, purpose="hardware timing and portability only",
                calibration_replicate=False, job=job,
                **{k: current[k] for k in ("sampler", "packages", "root_seed")},
                seeds=dict(data=d1c.seed(1, 0, 0, 1, 0), fit=d1c.seed(2, 12, 0),
                           selection=d1c.seed(3, 12, 0)),
                sources={p: file_hash(ROOT / p) for p in PATHS},
                archived_reference=REFERENCE, retries=0, workers=1,
                max_elapsed_seconds=MAX_SECONDS, sampled_rss_stop_bytes=RSS_LIMIT)


def group_rss(pid):
    result = subprocess.run(["/bin/ps", "-axo", "pgid=,rss="], check=True,
                            capture_output=True, text=True, timeout=10)
    return sum(int(rss) * 1024 for group, rss in
               (line.split() for line in result.stdout.splitlines()) if int(group) == pid)


def bounded_run(command, directory, report, *, max_seconds=MAX_SECONDS,
                rss_limit=RSS_LIMIT, interval=2, measure=group_rss):
    """Own exactly one process group and retain a receipt even on interruption."""
    started = time.monotonic()
    process = None
    last_update = 0
    report.update(state="running", started_at=now(), peak_sampled_group_rss_bytes=0)
    atomic_json(directory / "receipt.json", report)
    try:
        with (directory / "worker-stdout.txt").open("x") as output:
            process = subprocess.Popen(command, cwd=ROOT, stdout=output,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            while process.poll() is None:
                elapsed = time.monotonic() - started
                rss = measure(process.pid)
                report["peak_sampled_group_rss_bytes"] = max(report["peak_sampled_group_rss_bytes"], rss)
                if elapsed >= max_seconds:
                    raise TimeoutError("Six-hour timing limit reached; no retry")
                if rss >= rss_limit:
                    raise MemoryError("Sampled worker RSS reached 10 GiB; no retry")
                if elapsed - last_update >= 30:
                    report.update(elapsed_seconds=round(elapsed, 1), updated_at=now())
                    atomic_json(directory / "receipt.json", report)
                    lines = (directory / "worker-stdout.txt").read_text(errors="replace").splitlines()
                    print(f"Running: {elapsed / 60:.1f} min; worker RSS {rss / 2**30:.2f} GiB", flush=True)
                    if lines:
                        print(lines[-1], flush=True)
                    last_update = elapsed
                time.sleep(interval)
            report.update(worker_exit_code=process.returncode,
                          state="complete" if process.returncode == 0 else "failed")
    except BaseException as error:
        report.update(state="stopped" if isinstance(error, (KeyboardInterrupt, TimeoutError, MemoryError)) else "failed",
                      stop_reason=f"{type(error).__name__}: {error}")
    finally:
        if process is not None:
            stop_group(process)
        report.update(ended_at=now(), elapsed_seconds=round(time.monotonic() - started, 2))
        atomic_json(directory / "receipt.json", report)
    return report


def worker():
    import d1c
    import grid
    from component_state import ComponentState

    spec = json.loads((DIRECTORY / "specification.json").read_text())
    if spec != specification():
        raise ValueError("Assigned specification changed")
    grid.configure_sampler(4000, 2000, 8000)
    result = dict(state="failed", started_at=now())
    try:
        with ComponentState(DIRECTORY / "checkpoints", spec) as store:
            rows, status = d1c.fit(spec["job"], components=store)
            metadata, arrays = store.load("joint")
            import numpy as np
            if (set(arrays) != {"h2", "h1_fixed_usage", "b_z", "marking"}
                    or any(a.shape != (16000,) or not np.isfinite(a).all() for a in arrays.values())):
                raise ValueError("Incomplete or non-finite contrast archive")
            if status["data_seed"] != spec["seeds"]["data"] or status["fit_seed"] != spec["seeds"]["fit"]:
                raise ValueError("Returned seeds differ from assignment")
            # Legacy threshold labels are not reported for this timing repeat.
            fields = ("estimand", "truth", "mean", "lo50", "hi50", "lo90", "hi90", "p_direction")
            result.update(state="complete", diagnostic_status=status["status"],
                          diagnostic=metadata["diagnostic"],
                          estimates=[{key: row[key] for key in fields} for row in rows],
                          archive_sha256=store.records["joint"]["archive_sha256"])
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}".replace(str(ROOT), "<project>")
        raise
    finally:
        result.update(ended_at=now(), peak_process_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        atomic_json(DIRECTORY / "worker-result.json", result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate the assignment without fitting")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    if args.worker:
        worker()
        return 0
    if DIRECTORY.exists():
        raise FileExistsError(f"This assignment was already attempted: {DIRECTORY}. No automatic rerun.")
    # Recheck the installed environment before the actual fit; no study data here.
    subprocess.run([sys.executable, str(ROOT / "scripts/volunteer/preflight.py")], check=True, cwd=ROOT)
    readiness = json.loads((ROOT / "volunteer-readiness.json").read_text())
    if not readiness["ready_for_assignment"]:
        raise RuntimeError("Environment check failed")
    from run_component import verify_published_source
    verify_published_source(readiness["source_commit"], PATHS)
    spec = specification()
    if args.check:
        print(f"PASS published assignment: {ASSIGNMENT}; cell 12, rep 0; one worker; no fit started")
        return 0
    DIRECTORY.mkdir(parents=True, exist_ok=False)
    atomic_json(DIRECTORY / "specification.json", spec)
    report = dict(assignment=ASSIGNMENT, purpose=spec["purpose"], calibration_replicate=False,
                  source_commit=readiness["source_commit"], specification_sha256=file_hash(DIRECTORY / "specification.json"),
                  job=spec["job"], seeds=spec["seeds"], sampler=spec["sampler"],
                  environment=readiness, automatic_retries=0)
    def interrupted(signum, frame):
        raise KeyboardInterrupt(f"Received signal {signum}")
    signal.signal(signal.SIGTERM, interrupted)
    print("Starting one archived timing fit. Ctrl-C stops it. No subsequent job will start.", flush=True)
    report = bounded_run([sys.executable, "-u", str(Path(__file__).resolve()), "--worker"], DIRECTORY, report)
    result = DIRECTORY / "worker-result.json"
    if result.exists():
        report["result"] = json.loads(result.read_text())
    if report["state"] == "complete" and report.get("result", {}).get("state") != "complete":
        report.update(state="failed", stop_reason="Worker exited without a complete result")
    atomic_json(DIRECTORY / "receipt.json", report)
    print(f"{report['state'].upper()}: {DIRECTORY / 'receipt.json'}", flush=True)
    print("Return receipt.json, including failures. This timing repeat is excluded from calibration.", flush=True)
    return 0 if report["state"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
