#!/usr/bin/env python3
"""Notify locally about compute events without model calls or new cloud jobs."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "results/compute/event-watch-20261011"
SOURCES = {
    "HF": ROOT / "results/compute/packing-20261011/status.json",
    "Colab": ROOT / "results/compute/colab-timing-20261011/status.json",
}
TERMINAL = {"COMPLETED", "ERROR", "CANCELED", "CANCELLED", "FAILED", "DELETED"}


def utcnow():
    return datetime.now(timezone.utc)


def fingerprint(value):
    return hashlib.sha256(str(value).encode()).hexdigest()[:16]


def facts(label, data, now):
    """Stable event IDs let restarts and repeated snapshots avoid duplicate alerts."""
    out = {}
    state = data.get("state", "unknown")
    stamp = data.get("updated_at") or data.get("ended_at") or data.get("started_at")
    if stamp and state in {"running", "preparing", "unknown"}:
        age = (now-datetime.fromisoformat(stamp)).total_seconds()
        if age > 300:
            out[f"{label}:stale:{stamp}"] = f"{label}: monitor has not updated for over five minutes."
    if data.get("error"):
        out[f"{label}:error:{fingerprint(data['error'])}"] = f"{label}: monitor reports an error; inspect the event log."
    if label == "HF":
        for arm in data.get("arms", []):
            name = arm["profile"]
            for module in arm.get("modules", []):
                if module.get("archive_verified"):
                    good = module.get("diagnostics_pass", False)
                    out[f"{name}:component:{module['component']}"] = (
                        f"{name}: fit {module['component']} completed and archive verified; "
                        + ("diagnostics passed." if good else "diagnostics FAILED."))
            for failed in arm.get("receipt", {}).get("failed", []):
                out[f"{name}:failed:{fingerprint(failed)}"] = f"{name}: a fit failed; inspect the event log."
            if arm.get("error"):
                out[f"{name}:error:{fingerprint(arm['error'])}"] = f"{name}: collection or verification error."
            stage = arm.get("stage")
            if stage in TERMINAL:
                out[f"{name}:terminal:{stage}"] = f"{name}: provider job ended ({stage}); {arm.get('verified_completed', 0)}/6 fits verified."
    else:
        diagnostic = data.get("result", {}).get("diagnostic", {})
        if diagnostic and not (diagnostic.get("good") and diagnostic.get("contrast_good")):
            out["Colab:diagnostics-failed"] = "Colab: fit finished, but diagnostics FAILED."
        for failed in data.get("progress", {}).get("failed", []):
            out[f"Colab:failed:{fingerprint(failed)}"] = "Colab: fit failed; controller is collecting artifacts and releasing the runtime."
        release = data.get("runtime_release", {})
        if release and (release.get("error") or release.get("returncode") != 0):
            out["Colab:release-failed"] = "Colab runtime release failed. Manual attention is required."
    if state == "complete":
        out[f"{label}:complete"] = f"{label}: run complete; results collected and verified."
    elif state in {"failed", "execution_failed", "incomplete_terminal"}:
        out[f"{label}:{state}"] = f"{label}: run ended with state {state}; inspect the saved report."
    return out


def notify(message):
    return subprocess.Popen([
        "/usr/bin/osascript", "-e", "on run argv", "-e",
        "beep 1", "-e",
        'display dialog (item 1 of argv) with title "Compute monitor" buttons {"Acknowledge"} default button 1',
        "-e", "end run", message,
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hf-pid", type=int, required=True)
    parser.add_argument("--colab-pid", type=int, required=True)
    args = parser.parse_args()
    BASE.mkdir(parents=True, exist_ok=True)
    lock = (BASE / "writer.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    logfile = BASE / "events.jsonl"
    prior = [json.loads(line) for line in logfile.read_text().splitlines()] if logfile.exists() else []
    seen = {e["id"] for e in prior}
    acknowledgements = BASE / "acknowledgements.jsonl"
    acked = set()
    if acknowledgements.exists():
        for line in acknowledgements.read_text().splitlines():
            acked.update(json.loads(line)["ids"])
    pending = {event["id"]: event for event in prior if event["id"] not in acked}
    dialog = None
    retry_at = 0
    pids = {"HF": args.hf_pid, "Colab": args.colab_pid}
    awake = subprocess.Popen(["/usr/bin/caffeinate", "-i", "-w", str(os.getpid())])

    def emit(event_id, message, detail=None):
        if event_id in seen:
            return
        event = dict(id=event_id, at=utcnow().isoformat(), message=message, detail=detail)
        # Preserve the event even if Notification Center or osascript fails.
        with logfile.open("a") as stream:
            stream.write(json.dumps(event, sort_keys=True)+"\n")
            stream.flush()
            os.fsync(stream.fileno())
        seen.add(event_id)
        pending[event_id] = event
        print(json.dumps(dict(event=event)), flush=True)

    def deliver():
        nonlocal dialog, retry_at
        if dialog is not None and dialog[0].poll() is not None:
            process, ids = dialog
            stdout, stderr = process.communicate()
            if process.returncode == 0:
                with acknowledgements.open("a") as stream:
                    stream.write(json.dumps(dict(at=utcnow().isoformat(), ids=ids))+"\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                for event_id in ids:
                    pending.pop(event_id, None)
                print(json.dumps(dict(acknowledged=ids, at=utcnow().isoformat())), flush=True)
            else:
                print(json.dumps(dict(alert_error=stderr, returncode=process.returncode)), flush=True)
                retry_at = time.monotonic()+300
            dialog = None
        if dialog is None and pending and time.monotonic() >= retry_at:
            ids = list(pending)
            message = "\n\n".join(pending[event_id]["message"] for event_id in ids)
            message += "\n\nEvents are saved in results/compute/event-watch-20261011/events.jsonl."
            dialog = (notify(message), ids)

    try:
        print(json.dumps(dict(watching=pids, started_at=utcnow().isoformat())), flush=True)
        while True:
            statuses = {}
            for label, path in SOURCES.items():
                try:
                    data = json.loads(path.read_text())
                    statuses[label] = data.get("state")
                    for event_id, message in facts(label, data, utcnow()).items():
                        emit(event_id, message, data if "error" in event_id or "failed" in event_id else None)
                    if not alive(pids[label]) and data.get("state") not in {"complete", "failed", "execution_failed", "incomplete_terminal"}:
                        emit(f"{label}:monitor-stopped", f"{label}: monitor stopped before recording a final result.")
                except (OSError, ValueError) as error:
                    emit(f"{label}:unreadable:{fingerprint(error)}", f"{label}: cannot read monitor status.", repr(error))
            if not any(alive(pid) for pid in pids.values()):
                emit("watch-finished", "Both compute monitors have stopped. Final results and any failures are saved.", statuses)
                if awake is not None:
                    awake.terminate()
                    awake.wait(timeout=5)
                    awake = None
            deliver()
            if "watch-finished" in seen and not pending and dialog is None:
                return
            time.sleep(10)
    finally:
        if awake is not None:
            awake.terminate()
            awake.wait(timeout=5)


if __name__ == "__main__":
    main()
