#!/usr/bin/env python3
"""Own the prepared Colab CPU timing fit, retrieve artifacts and release it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/d1c"))
from run_state import atomic_json, digest
from collect_parallel import verify_component

SESSION = "Brett-colab-timing1"
BASE = ROOT / "results/compute/colab-timing-20261011"
CACHE = ROOT / ".cache/compute/colab-timing-20261011"
REMOTE = "/content/marked-pole-compute/results/compute/20261011/colab-one"
CLI = ["uvx", "--from", "google-colab-cli==0.7.4", "python",
       str(ROOT / "scripts/compute/colab_access.py"), "--auth", "oauth2"]


def now():
    return datetime.now(timezone.utc).isoformat()


def call(*args, timeout=90):
    return subprocess.run(CLI+list(args), cwd=ROOT, capture_output=True, text=True, timeout=timeout)


def check_archive(path, source):
    destination = CACHE / "artifacts"
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            name = Path(member.filename)
            if name.is_absolute() or ".." in name.parts:
                raise ValueError("Archive contains a path outside its artifact directory")
        archive.extractall(destination)
    receipt = json.loads((destination / "receipt.json").read_text())
    spec = json.loads((destination / "specification.json").read_text())
    if receipt["source_commit"] != source or receipt["state"] != "complete" or receipt["completed"] != [0]:
        raise ValueError("Colab controller did not finish the assigned fit")
    if spec["profile"] != "colab-one" or spec["job"]["cell"] != 12 or spec["job"]["rep"] != 0:
        raise ValueError("Colab assignment differs")
    loaded = verify_component(destination / "component-000/checkpoints", "joint")
    if loaded is None:
        raise ValueError("No completed joint archive")
    manifest, record, arrays = loaded
    if manifest["signature"] != digest(dict(spec, component=0)):
        raise ValueError("Completed fit specification differs")
    runtime = json.loads((destination / "component-000/runtime.json").read_text())
    if runtime["archive_sha256"] != record["archive_sha256"]:
        raise ValueError("Runtime and archive disagree")
    atomic_json(BASE / "receipt.json", receipt)
    atomic_json(BASE / "runtime.json", runtime)
    atomic_json(BASE / "specification.json", spec)
    return dict(archive_verified=True, archive_sha256=record["archive_sha256"],
                diagnostic=record["metadata"]["diagnostic"],
                diagnostic_status=runtime.get("diagnostic_status"),
                elapsed_seconds=receipt["elapsed_seconds"],
                downloaded_zip_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    if not re.fullmatch("[0-9a-f]{40}", args.source):
        parser.error("Use the full published source commit")
    from run_component import verify_published_source
    verify_published_source(args.source, ["scripts/compute/run_colab_timing.py",
        "scripts/compute/colab_bootstrap.py", "scripts/compute/colab_access.py", "scripts/compute/README.md"])
    BASE.mkdir(parents=True, exist_ok=True)
    if (BASE / "status.json").exists():
        raise FileExistsError("Colab timing has already been attempted; inspect before any further action")
    CACHE.mkdir(parents=True, exist_ok=True)
    report = dict(state="preparing", source_commit=args.source, session=SESSION,
                  started_at=now(), initial_balance_units=400, observed_units_per_hour=.08,
                  available_pool_units=400, additional_credit_purchase_authorized=False,
                  calibration_replicate=False, automatic_model_retries=0)
    atomic_json(BASE / "status.json", report)
    process = None
    started = time.monotonic()

    def interrupted(signum, frame):
        raise InterruptedError(f"Signal {signum}")

    signal.signal(signal.SIGTERM, interrupted)
    try:
        with (ROOT / "logs/colab-timing-execution-20261011-stdout.txt").open("x") as stream:
            process = subprocess.Popen(CLI+["exec", "-s", SESSION, "--timeout", "24000", "--env",
                f"BENCHMARK_SOURCE={args.source}", "-f", str(ROOT / "scripts/compute/colab_bootstrap.py")],
                cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            report["state"] = "running"
            while process.poll() is None:
                if time.monotonic()-started >= 24000:
                    raise TimeoutError("Local Colab lifecycle limit reached")
                progress = CACHE / "latest-receipt.json"
                downloaded = call("download", "-s", SESSION, REMOTE+"/receipt.json", str(progress))
                if downloaded.returncode == 0:
                    report["progress"] = json.loads(progress.read_text())
                report.update(updated_at=now(), elapsed_seconds=time.monotonic()-started)
                atomic_json(BASE / "status.json", report)
                print(json.dumps({k: report[k] for k in ("state", "updated_at", "elapsed_seconds")}), flush=True)
                if process.poll() is None:
                    time.sleep(60)
            report["execution_returncode"] = process.returncode
        target = CACHE / "benchmark-artifacts.zip"
        download = call("download", "-s", SESSION, "/content/benchmark-artifacts.zip", str(target), timeout=180)
        if download.returncode:
            raise RuntimeError("Final archive download failed: "+download.stderr[-1000:])
        report["result"] = check_archive(target, args.source)
        report["state"] = "complete" if process.returncode == 0 else "execution_failed"
    except BaseException as error:
        report.update(state="failed", error=repr(error))
    finally:
        if process is not None and process.poll() is None:
            from cloud_benchmark import stop_group
            stop_group(process)
        # Release only the session this controller was assigned.
        try:
            stopped = call("stop", "-s", SESSION)
            report["runtime_release"] = dict(returncode=stopped.returncode,
                                            stdout=stopped.stdout, stderr=stopped.stderr)
        except Exception as error:
            report["runtime_release"] = dict(error=repr(error))
        report.update(ended_at=now(), elapsed_seconds=time.monotonic()-started)
        atomic_json(BASE / "status.json", report)
    return 0 if report["state"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
