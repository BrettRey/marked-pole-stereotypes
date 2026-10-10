#!/usr/bin/env python3
"""Keep one local worker occupied with the five remaining assigned components."""
import argparse
import fcntl
import json
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

from cloud_benchmark import supervise
from collect_parallel import (CLOUD_PATH, UPSTREAM_COMMIT, validate_assignment)
from run_component import git, verify_published_source
from run_state import atomic_json

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = (3, 4, 5, 6, 7)


def advance(components, completed, execute):
    """Completed diagnostic failures count as done; execution errors halt."""
    for component in components:
        if completed(component):
            continue
        if execute(component) != 0:
            raise RuntimeError(f"Component {component} failed to execute; no automatic retry")
        if not completed(component):
            raise RuntimeError(f"Component {component} returned without a valid saved result")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    paths = ["scripts/d1c/local_queue.py", "scripts/d1c/run_component.py", "scripts/d1c/README.md",
             "scripts/d1c/cloud_benchmark.py", "scripts/d1c/collect_parallel.py"]
    verify_published_source(args.source, paths)
    canonical = json.loads(git("show", f"{UPSTREAM_COMMIT}:{CLOUD_PATH}/checkpoints/manifest.json"))
    directory = ROOT / "results/d1c/local-queue-20261010"
    directory.mkdir(parents=True, exist_ok=True)
    state = dict(state="running", source_commit=args.source, pid=os.getpid(),
                 started_at=datetime.now(timezone.utc).isoformat(), assigned=list(COMPONENTS),
                 completed=[], current_component=None, current_worker_pid=None,
                 scope="Components 3–7 of cell 10, replicate 0 only; one local worker")

    def publish():
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        atomic_json(directory / "progress.json", state)

    def completed(component):
        result = ROOT / "results/d1c" / f"local-component-{component:03d}-20261010"
        if not (result / "checkpoints/component-" f"downstream-{component:03d}.json").exists():
            return False
        valid = validate_assignment(result, "local", component, canonical)
        if valid is None:
            return False
        if component not in state["completed"]:
            state["completed"].append(component)
        publish()
        return True

    def execute(component):
        state.update(current_component=component, current_worker_pid=None)
        publish()
        log = ROOT / "logs" / f"d1c-local-component-{component:03d}-20261010-stdout.txt"
        if log.exists():
            raise RuntimeError("An earlier incomplete attempt exists; inspect before retrying")
        def tick(pid):
            if state["current_worker_pid"] != pid:
                state["current_worker_pid"] = pid
                publish()
        print(f"Starting assigned local component {component}", flush=True)
        with log.open("x") as output:
            return supervise([sys.executable, "-u", str(ROOT / "scripts/d1c/run_component.py"),
                              "--source", args.source, "--location", "local", "--component", str(component)],
                             output, tick)

    def interrupted(signum, frame):
        raise InterruptedError(f"Queue interrupted by signal {signum}")
    signal.signal(signal.SIGTERM, interrupted)
    with (directory / "writer.lock").open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        publish()
        try:
            advance(COMPONENTS, completed, execute)
            state.update(state="complete", current_component=None, current_worker_pid=None)
        except BaseException as exc:
            state.update(state="stopped", error=repr(exc))
            raise
        finally:
            state["ended_at"] = datetime.now(timezone.utc).isoformat()
            publish()


if __name__ == "__main__":
    main()
