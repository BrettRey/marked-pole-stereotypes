#!/usr/bin/env python3
"""Submit the one authorized HF component; default is a non-submitting preview."""
import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "python@sha256:7ee7e4d4fb42c3ad45b8fdc473b64ec69c3cf6e80ae5d52f6fa55f77fac29027"
BUCKET = "hf://buckets/BrettRey/marked-pole-d1c-compute"
BOOTSTRAP = '''set -eu
git clone --quiet https://github.com/BrettRey/marked-pole-stereotypes.git /work
cd /work
git checkout --quiet "$1"
git fetch --quiet origin 942dfd8109232beaf7e5bf35c023409b09a18525
exec bash scripts/d1c/hf_job.sh "$1"
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch("[0-9a-f]{40}", args.source):
        parser.error("Use the full published source commit")
    receipt = ROOT / "logs/d1c-hf-job-20261010.json"
    if args.execute and receipt.exists():
        raise RuntimeError("An HF submission record already exists; inspect it, do not duplicate the job")
    command = ["hf", "jobs", "run", "--json", "--detach", "--flavor", "cpu-upgrade",
               "--timeout", "24h", "--attempts", "1", "--name", "d1c-component-002-20261010",
               "--volume", f"{BUCKET}:/outputs:rw"]
    if not args.execute:
        command.append("--dry-run")
    command.extend([IMAGE, "bash", "-lc", BOOTSTRAP, "d1c-job", args.source])
    environment = os.environ.copy()
    # Use Brett's newly authorized cached OAuth login, not the old read-only
    # environment token. No credential enters the job or this public receipt.
    environment.pop("HF_TOKEN", None)
    result = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True)
    record = dict(submitted_at=datetime.now(timezone.utc).isoformat(), source_commit=args.source,
                  image=IMAGE, bucket=BUCKET, flavor="cpu-upgrade", timeout_seconds=86400,
                  maximum_attempts=1, hourly_compute_usd=.03, maximum_compute_usd=.72,
                  total_authorized_hf_usd=10, returncode=result.returncode,
                  stdout=result.stdout, stderr=result.stderr)
    if args.execute:
        receipt.write_text(json.dumps(record, indent=2) + "\n")
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
