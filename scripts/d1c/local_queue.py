#!/usr/bin/env python3
"""Keep one local worker occupied with its remaining assigned components."""
import argparse
import fcntl
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from cloud_benchmark import supervise
from collect_parallel import (CLOUD_PATH, UPSTREAM_COMMIT, validate_assignment)
from run_component import git, verify_published_source
from run_state import atomic_json

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = (3, 7)


def process_info(pid):
    result = subprocess.run(["ps", "-p", str(pid), "-o", "ppid=,pgid=,stat=,command="],
                            capture_output=True, text=True, check=False)
    fields = result.stdout.strip().split(None, 3)
    if len(fields) != 4 or fields[2].startswith("Z"):
        return None
    return dict(ppid=int(fields[0]), pgid=int(fields[1]), state=fields[2], command=fields[3])


def retire_supervisor(parent, child, parent_marker, child_marker):
    """Retire only an identified parent, keeping its independent worker alive."""
    supervisor, worker = process_info(parent), process_info(child)
    if (not supervisor or not worker or parent_marker not in supervisor["command"]
            or child_marker not in worker["command"] or worker["ppid"] != parent
            or worker["pgid"] != child or supervisor["pgid"] == child):
        raise RuntimeError("Supervisor/worker identity or group differs; refusing handoff")
    os.kill(parent, signal.SIGSTOP)
    try:
        if process_info(child) != worker:
            # The scheduling state may change; all identity fields must persist.
            current = process_info(child)
            if not current or any(current[k] != worker[k] for k in ("ppid", "pgid", "command")):
                raise RuntimeError("Worker identity changed during handoff")
        os.kill(parent, signal.SIGKILL)  # No graceful handler: it would stop the worker.
    except BaseException:
        if process_info(parent):
            os.kill(parent, signal.SIGCONT)
        raise
    for _ in range(100):
        if process_info(parent) is None:
            break
        time.sleep(.05)
    else:
        raise RuntimeError("Old supervisor did not stop")
    current = process_info(child)
    if not current or current["pgid"] != child or current["command"] != worker["command"]:
        raise RuntimeError("Adopted worker did not survive supervisor retirement")
    return dict(previous_supervisor_pid=parent, adopted_worker_pid=child,
                previous_supervisor=supervisor, worker=current,
                transferred_at=datetime.now(timezone.utc).isoformat())


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
    parser.add_argument("--replace-supervisor", type=int)
    args = parser.parse_args()
    paths = ["scripts/d1c/local_queue.py", "scripts/d1c/run_component.py", "scripts/d1c/README.md",
             "scripts/d1c/cloud_benchmark.py", "scripts/d1c/collect_parallel.py"]
    verify_published_source(args.source, paths)
    canonical = json.loads(git("show", f"{UPSTREAM_COMMIT}:{CLOUD_PATH}/checkpoints/manifest.json"))
    directory = ROOT / "results/d1c/local-queue-20261010"
    directory.mkdir(parents=True, exist_ok=True)
    previous = None
    handoff = None
    if args.replace_supervisor:
        previous = json.loads((directory / "progress.json").read_text())
        if (previous["pid"] != args.replace_supervisor or previous["state"] != "running"
                or previous["current_component"] != 3 or previous["assigned"] != [3, 4, 5, 6, 7]):
            raise RuntimeError("Expected the original queue running component 3")
        runtime = json.loads((ROOT / "results/d1c/local-component-003-20261010/runtime.json").read_text())
        if runtime["pid"] != previous["current_worker_pid"] or runtime["state"] != "running":
            raise RuntimeError("Expected the original running worker")
        handoff = retire_supervisor(args.replace_supervisor, runtime["pid"],
                    f"scripts/d1c/local_queue.py --source {previous['source_commit']}",
                    f"--source {runtime['source_commit']} --location local --component 3")
        atomic_json(directory / "handoff.json", dict(**handoff, previous_queue=previous))
    state = dict(state="running", source_commit=args.source, pid=os.getpid(),
                 started_at=datetime.now(timezone.utc).isoformat(), assigned=list(COMPONENTS),
                 completed=[], current_component=None, current_worker_pid=None,
                 scope="Components 3 and 7 of cell 10, replicate 0 only; one local worker",
                 handoff=handoff)

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
        if component == 3 and handoff:
            pid = handoff["adopted_worker_pid"]
            state.update(current_component=component, current_worker_pid=pid)
            publish()
            print(f"Observing adopted component 3 worker {pid}", flush=True)
            while True:
                runtime = json.loads((ROOT / "results/d1c/local-component-003-20261010/runtime.json").read_text())
                if runtime["state"] == "component_complete":
                    return 0
                current = process_info(pid)
                if (runtime["state"] != "running" or not current
                        or current["command"] != handoff["worker"]["command"]):
                    raise RuntimeError("Adopted worker stopped without completion; no retry")
                time.sleep(10)
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
