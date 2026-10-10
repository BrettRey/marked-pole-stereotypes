#!/usr/bin/env python3
"""One cloud component; export checkpoints as they finish, then stop."""
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

from run_state import atomic_json

ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, text=True,
                          capture_output=True, timeout=60).stdout.strip()


def stop_group(process):
    """Stop only the separate process group created for this benchmark."""
    def signal_group(sig):
        try:
            os.killpg(process.pid, sig)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            # macOS can report EPERM for an exiting orphan process group.
            # Confirm there are no live members before treating it as gone;
            # an actual permission failure on a live group must still surface.
            listing = subprocess.run(["ps", "-axo", "pgid=,stat="], check=True,
                                     capture_output=True, text=True).stdout
            for line in listing.splitlines():
                group, state = line.split()
                if int(group) == process.pid and not state.startswith("Z"):
                    raise
            return False

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGKILL):
        if not signal_group(sig):
            break
        if sig != signal.SIGKILL:
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                process.poll()
                if not signal_group(0):
                    break
                time.sleep(.1)
    process.wait()


def supervise(command, output, on_tick, *, interval=2):
    process = subprocess.Popen(command, cwd=ROOT, stdout=output,
                               stderr=subprocess.STDOUT, start_new_session=True)
    try:
        while process.poll() is None:
            on_tick(process.pid)
            time.sleep(interval)
        on_tick(process.pid)
        return process.returncode
    finally:
        # Also handles an export failure or interruption of the supervisor.
        stop_group(process)


def memory_sample(group):
    """Linux process-group RSS; shared pages may be counted more than once."""
    total = 0
    found = False
    for path in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = path.read_text().rsplit(")", 1)[1].split()
            if int(fields[2]) == group:
                total += int(fields[21]) * os.sysconf("SC_PAGE_SIZE")
                found = True
        except (OSError, ValueError, IndexError):
            continue
    return total if found else None


def export(directory, branch, label):
    """Publish only this run's inspectable records and completed archives."""
    if branch in ("master", "main", "HEAD") or git("branch", "--show-current") != branch:
        raise RuntimeError("Exports require the assigned benchmark branch")
    if git("diff", "--cached", "--name-only"):
        raise RuntimeError("Refusing to include an existing staged change")
    paths = [directory / name for name in
             ("benchmark.json", "runtime.json", "worker-result.json", "worker-stdout.txt")]
    checkpoint = directory / "checkpoints"
    paths.extend(checkpoint / name for name in ("manifest.json", "progress.json"))
    for marker in checkpoint.glob("component-*.json"):
        # JSON is the completion marker. Never export an unfinished archive.
        envelope = json.loads(marker.read_text())
        archive = checkpoint / envelope["record"]["archive"]
        if archive.parent != checkpoint or hashlib.sha256(archive.read_bytes()).hexdigest() != envelope["record"]["archive_sha256"]:
            raise ValueError("Invalid completed component archive")
        paths.extend((marker, archive))
    paths = [str(path.relative_to(ROOT)) for path in paths if path.exists()]
    if not paths:
        return
    try:
        git("add", "--", *paths)
        if git("diff", "--cached", "--name-only"):
            git("diff", "--cached", "--check")
            git("commit", "-m", f"D1c cloud benchmark: {label}", "--", *paths)
        git("push", "origin", f"HEAD:{branch}")
    finally:
        if git("diff", "--cached", "--name-only"):
            git("restore", "--staged", "--", *paths)


def worker(directory):
    import d1c
    import grid
    from component_state import ComponentLimitReached, ComponentState

    grid.configure_sampler(4000, 2000, 8000)
    full = grid.specification(1, 4000, 2000, 8000)
    job = dict(next(cell for cell in d1c.cells() if cell["cell"] == 10), rep=0)
    spec = {key: full[key] for key in
            ("sampler", "sources", "packages", "python", "platform", "root_seed")}
    spec.update(job=job, max_downstream_components=1,
                seeds=dict(data=d1c.seed(1, list(d1c.DESIGNS).index(job["design"]),
                                         d1c.SCENARIOS.index(job["scenario"]),
                                         int(job["target"] != 0), job["rep"]),
                           fit=d1c.seed(2, job["cell"], 0),
                           selection=d1c.seed(3, job["cell"], 0),
                           component=d1c.seed(4, job["cell"], 0, 0)))
    atomic_json(directory / "benchmark.json", spec)
    result = dict(state="failed", started_at=datetime.now(timezone.utc).isoformat())
    started = time.monotonic()
    try:
        with ComponentState(directory / "checkpoints", spec) as components:
            try:
                d1c.fit(job, components=components, max_downstream_components=1)
                raise RuntimeError("A one-component benchmark must not return a full cut")
            except ComponentLimitReached:
                result.update(state="component_complete", completed_components=list(components.records),
                              note="One conditional component, not a full cut estimate or calibration.")
    except BaseException as exc:
        result["error"] = repr(exc)
        raise
    finally:
        result.update(elapsed_seconds=time.monotonic()-started,
                      peak_process_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss *
                      (1 if sys.platform == "darwin" else 1024))
        atomic_json(directory / "worker-result.json", result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--run", default="20261010")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.run != "20261010":
        parser.error("Only the authorized 20261010 benchmark is supported")
    directory = ROOT / "results/d1c" / f"cloud-canary-{args.run}"
    if args.worker:
        worker(directory)
        return
    def interrupted(signum, frame):
        raise InterruptedError(f"Supervisor received signal {signum}")
    signal.signal(signal.SIGTERM, interrupted)
    started = time.monotonic()
    if sys.version_info[:2] != (3, 14):
        raise RuntimeError("The benchmark requires Python 3.14")
    for line in (ROOT / "requirements-d1.txt").read_text().splitlines():
        name, expected = line.split("==")
        if version(name) != expected:
            raise RuntimeError(f"Package version differs from the frozen requirements: {name}")
    if git("rev-parse", "HEAD") != args.source or git("status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("Start from the exact clean published source commit")
    directory.mkdir(parents=True, exist_ok=False)  # no automatic retries
    runtime = dict(source_commit=args.source, branch=args.branch, command=sys.argv,
                   started_at=datetime.now(timezone.utc).isoformat(), state="running",
                   python=sys.version, platform=platform.platform(),
                   credit_before=dict(usd=216, basis="user report; not an account reading"),
                   credit_after=None, credit_note="No programmatic billing access; record an account reading separately if available.",
                   limit="One upstream preparation and downstream component 0; no wall-clock cutoff or retries.",
                   peak_sampled_process_group_rss_bytes=None,
                   memory_note="Two-second samples; summed process RSS may double-count shared pages.")
    for name in ("memory.max", "memory.peak"):
        path = Path("/sys/fs/cgroup") / name
        runtime["container_" + name.replace(".", "_")] = path.read_text().strip() if path.exists() else None
    def publish():
        runtime.update(elapsed_seconds=time.monotonic()-started,
                       updated_at=datetime.now(timezone.utc).isoformat())
        atomic_json(directory / "runtime.json", runtime)
    seen = set()
    export_failed = False
    def push(label):
        nonlocal export_failed
        try:
            export(directory, args.branch, label)
        except BaseException:
            export_failed = True
            raise
    def tick(pid):
        sample = memory_sample(pid)
        if sample is not None:
            runtime["peak_sampled_process_group_rss_bytes"] = max(sample, runtime["peak_sampled_process_group_rss_bytes"] or 0)
        completed = {p.name for p in (directory / "checkpoints").glob("component-*.json")}
        if completed != seen:
            publish()
            push(", ".join(sorted(completed)))
            seen.update(completed)
    try:
        publish()
        push("started")
        with (directory / "worker-stdout.txt").open("w") as output:
            code = supervise([sys.executable, str(Path(__file__).resolve()),
                              "--source", args.source, "--branch", args.branch, "--worker"], output, tick)
        runtime.update(state="complete" if code == 0 else "failed", worker_exit_code=code)
    except BaseException as exc:
        runtime.update(state="interrupted", error=repr(exc))
        raise
    finally:
        runtime["ended_at"] = datetime.now(timezone.utc).isoformat()
        peak = Path("/sys/fs/cgroup/memory.peak")
        runtime["container_memory_peak_at_end"] = peak.read_text().strip() if peak.exists() else None
        publish()
        if not export_failed:
            push(runtime["state"])
    if code:
        raise SystemExit(code)


if __name__ == "__main__":
    main()
