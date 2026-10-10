#!/usr/bin/env python3
"""Run the fixed HF assignment with two workers and durable per-component output."""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from cloud_benchmark import stop_group
from collect_parallel import CLOUD_PATH, UPSTREAM_COMMIT, validate_assignment
from run_component import git, verify_published_source
from run_state import atomic_json

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = (4, 5, 6)
WORKERS = 2


def dispatch(components, launch, poll, valid, publish, pause, limit=2):
    """Bound concurrency; retain successes and failures, never retry a process."""
    pending, active, completed, failed = list(components), {}, [], []
    while pending or active:
        while pending and len(active) < limit and not failed:
            component = pending.pop(0)
            active[component] = launch(component)
            publish(pending, active, completed, failed)
        for component, worker in list(active.items()):
            code = poll(worker)
            if code is None:
                continue
            del active[component]
            (completed if code == 0 and valid(component) else failed).append(component)
            publish(pending, active, completed, failed)
        if failed and not active:
            raise RuntimeError(f"Execution failed for {failed}; queued {pending}; no retry")
        if active:
            pause()
    return completed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verify_published_source(args.source, ["scripts/d1c/hf_batch.py", "scripts/d1c/hf_batch.sh",
        "scripts/d1c/run_component.py", "scripts/d1c/collect_parallel.py", "scripts/d1c/README.md"])
    canonical = json.loads(git("show", f"{UPSTREAM_COMMIT}:{CLOUD_PATH}/checkpoints/manifest.json"))
    batch = args.output / "batch-004-006"
    batch.mkdir(parents=True, exist_ok=True)
    if (batch / "progress.json").exists():
        raise RuntimeError("Batch already attempted; no automatic restart")
    state = dict(state="running", source_commit=args.source, pid=os.getpid(),
        started_at=datetime.now(timezone.utc).isoformat(), assigned=list(COMPONENTS), workers=WORKERS)
    processes = {}

    def publish(pending, active, completed, failed):
        state.update(pending=list(pending), active={str(c): p.pid for c, p in active.items()},
                     completed=list(completed), failed=list(failed),
                     updated_at=datetime.now(timezone.utc).isoformat())
        peak = Path("/sys/fs/cgroup/memory.peak")
        if peak.exists():
            state["container_memory_peak_bytes"] = int(peak.read_text())
        atomic_json(batch / "progress.json", state)
        print(json.dumps(state), flush=True)

    def launch(component):
        destination = args.output / f"component-{component:03d}"
        if destination.exists():
            raise RuntimeError(f"Existing component directory {component}; inspect before retry")
        destination.mkdir()
        path = ROOT / "logs" / f"d1c-hf-component-{component:03d}-stdout.txt"
        output = path.open("x")
        process = subprocess.Popen([sys.executable, "-u", str(ROOT / "scripts/d1c/run_component.py"),
             "--source", args.source, "--location", "hf", "--component", str(component),
             "--export-directory", str(destination)], cwd=ROOT, stdout=output,
             stderr=subprocess.STDOUT, start_new_session=True)
        processes[component] = dict(process=process, output=output, reader=path.open(),
                                    path=path, destination=destination)
        return process

    def drain():
        for component, record in processes.items():
            chunk = record["reader"].read()
            if chunk:
                print(f"[component {component}]\n{chunk}", end="", flush=True)
                shutil.copyfile(record["path"], record["destination"] / "worker-stdout.txt")

    def valid(component):
        directory = ROOT / "results/d1c" / f"hf-component-{component:03d}-20261010"
        return validate_assignment(directory, "hf", component, canonical) is not None

    def pause():
        drain()
        time.sleep(2)

    def interrupted(signum, frame):
        raise InterruptedError(f"Batch interrupted by signal {signum}")
    signal.signal(signal.SIGTERM, interrupted)
    publish(COMPONENTS, {}, [], [])
    try:
        dispatch(COMPONENTS, launch, lambda p: p.poll(), valid, publish, pause, WORKERS)
        state["state"] = "complete"
    except BaseException as exc:
        state.update(state="stopped", error=repr(exc))
        raise
    finally:
        for record in processes.values():
            if record["process"].poll() is None:
                stop_group(record["process"])
            record["output"].close()
        drain()
        state["ended_at"] = datetime.now(timezone.utc).isoformat()
        atomic_json(batch / "progress.json", state)
        print(json.dumps(state), flush=True)


if __name__ == "__main__":
    main()
