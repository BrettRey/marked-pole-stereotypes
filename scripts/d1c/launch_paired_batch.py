#!/usr/bin/env python3
"""Launch five HF machines and the independent Mac joint fit."""
import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone

from launch_hf_batch import BUCKET, IMAGE
from paired_batch import BATCH, PATHS, ROOT, shard_modules
from run_component import verify_published_source
from run_state import atomic_json

RECEIPT = ROOT / "logs/d1c-paired-batch-launch-20261010.json"
BOOTSTRAP = '''set -eu
git clone --quiet https://github.com/BrettRey/marked-pole-stereotypes.git /work
cd /work
git checkout --quiet "$1"
exec bash scripts/d1c/paired_batch.sh "$1" "$2" "$3"
'''


def hf_command(source, shard, execute):
    location = "hf-joint" if shard == 4 else "hf"
    command = ["hf", "jobs", "run", "--format", "json", "--detach", "--flavor", "cpu-upgrade",
        "--timeout", "8h", "--attempts", "1", "--name", f"d1c-nicolas-pair-{shard}-20261010",
        "--volume", f"{BUCKET}:/outputs:rw"]
    if not execute:
        command.append("--dry-run")
    return command + ["--", IMAGE, "bash", "-lc", BOOTSTRAP, "d1c-job", source,
                      str(0 if shard == 4 else shard), location]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch("[0-9a-f]{40}", args.source):
        parser.error("Require full published source commit")
    if not args.execute:
        print(json.dumps(dict(hf_commands=[hf_command(args.source, i, False) for i in range(5)],
            local_cells=[4], maximum_new_compute_usd=1.20,
            conservative_total_reserved_usd=3.36, authorized_total_usd=10), indent=2))
        return
    if RECEIPT.exists() or (BATCH / "local/progress.json").exists():
        raise RuntimeError("This batch was already attempted; inspect it, do not duplicate it")
    verify_published_source(args.source, PATHS)
    environment = os.environ.copy()
    environment.pop("HF_TOKEN", None)
    environment.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    record = dict(state="submitting", source_commit=args.source, image=IMAGE, bucket=BUCKET,
        started_at=datetime.now(timezone.utc).isoformat(), hourly_compute_usd_per_machine=.03,
        timeout_seconds_per_machine=28800, maximum_attempts=1, machines=5, workers_per_machine=[2,2,2,2,1],
        maximum_new_compute_usd=1.20, conservative_total_reserved_usd=3.36,
        total_authorized_hf_usd=10, hf_jobs=[])
    atomic_json(RECEIPT, record)
    try:
        for shard in range(5):
            result = subprocess.run(hf_command(args.source, shard, True), cwd=ROOT,
                env=environment, capture_output=True, text=True, timeout=90)
            item = dict(shard=shard, location="hf-joint" if shard == 4 else "hf",
                modules=(["joint-124"] if shard == 4 else (["upstream"] if shard == 0 else []) + shard_modules(shard)),
                returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
            record["hf_jobs"].append(item)
            atomic_json(RECEIPT, record)
            if result.returncode:
                raise RuntimeError(f"HF submission {shard} failed; earlier accepted jobs are retained")
            job = json.loads(result.stdout)
            item["id"] = job["id"]
            atomic_json(RECEIPT, record)
            print(f"HF shard {shard}: {job['id']}", flush=True)
        with (ROOT / "logs/d1c-paired-local-20261010-stdout.txt").open("x") as stream:
            process = subprocess.Popen(["nice", "-n", "10", str(ROOT / ".venv/bin/python"), "-u",
                "scripts/d1c/paired_batch.py", "--source", args.source, "--location", "local"],
                cwd=ROOT, env=environment, stdin=subprocess.DEVNULL, stdout=stream,
                stderr=subprocess.STDOUT, start_new_session=True)
        record.update(state="launched", local_controller_pid=process.pid,
                      submitted_at=datetime.now(timezone.utc).isoformat())
    except BaseException as exc:
        record.update(state="launch_failed", error=repr(exc))
        raise
    finally:
        atomic_json(RECEIPT, record)
    print(json.dumps(dict(state=record["state"], local_controller_pid=record["local_controller_pid"])))


if __name__ == "__main__":
    main()
