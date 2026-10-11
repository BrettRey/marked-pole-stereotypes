#!/usr/bin/env python3
"""Launch exactly two capped packing benchmarks, defaulting to preview."""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/d1c"))
from launch_hf_batch import BUCKET, IMAGE
from run_state import atomic_json

PROFILES = ("hf-two", "hf-three")
RECEIPT = ROOT / "logs/compute-packing-launch-20261011.json"
MAXIMUM_NEW_USD = 2 * 12 * .03
TOTAL_RESERVED_USD = 13.80 + MAXIMUM_NEW_USD
BOOTSTRAP = '''set -eu
git clone --quiet https://github.com/BrettRey/marked-pole-stereotypes.git /work
cd /work
git checkout --quiet "$1"
python -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -r requirements-d1.txt
exec .venv/bin/python -u scripts/compute/benchmark.py --source "$1" --profile "$2" --export "/outputs/20261011/packing/$2"
'''


def command(source, profile, execute=False):
    if profile not in PROFILES or not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("Invalid fixed assignment")
    cmd = ["hf", "jobs", "run", "--format", "json", "--detach", "--flavor", "cpu-upgrade",
           "--timeout", "12h", "--attempts", "1", "--name", f"packing-{profile}-20261011",
           "--volume", f"{BUCKET}:/outputs:rw"]
    if not execute:
        cmd.append("--dry-run")
    return cmd + ["--", IMAGE, "bash", "-lc", BOOTSTRAP, "packing", source, profile]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    assert TOTAL_RESERVED_USD <= 15
    commands = [command(args.source, p, args.execute) for p in PROFILES]
    if not args.execute:
        print(json.dumps(dict(maximum_new_usd=MAXIMUM_NEW_USD,
            total_conservative_reserved_usd=TOTAL_RESERVED_USD, commands=commands), indent=2))
        return
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from benchmark import PATHS
    from run_component import verify_published_source
    verify_published_source(args.source, PATHS)
    if RECEIPT.exists():
        raise FileExistsError("Launch receipt already exists; never blindly repeat submission")
    env = {k: v for k, v in os.environ.items() if k != "HF_TOKEN"}
    listed = json.loads(subprocess.run(["hf", "jobs", "list", "--all", "--format", "json"],
                       check=True, capture_output=True, text=True, env=env).stdout)
    if any(j.get("labels", {}).get("name") in {f"packing-{p}-20261011" for p in PROFILES} for j in listed):
        raise RuntimeError("Provider already has a benchmark submission; reconcile first")
    report = dict(state="submitting", source_commit=args.source, calibration_replicate=False,
                  maximum_new_compute_usd=MAXIMUM_NEW_USD, total_conservative_reserved_usd=TOTAL_RESERVED_USD,
                  authorized_usd=15, image=IMAGE, hourly_compute_usd=.03, timeout_seconds=43200,
                  automatic_retries=0, jobs={})
    atomic_json(RECEIPT, report)
    for profile, cmd in zip(PROFILES, commands):
        report["jobs"][profile] = dict(state="submitting")
        atomic_json(RECEIPT, report)
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=90)
        report["jobs"][profile].update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
        if result.returncode:
            report["state"] = "submission_requires_inspection"
            atomic_json(RECEIPT, report)
            raise RuntimeError("Submission failed or ambiguous; no automatic retry")
        job = json.loads(result.stdout)
        report["jobs"][profile].update(state="accepted", id=job["id"])
        atomic_json(RECEIPT, report)
        print(f"Accepted {profile}: {job['id']}", flush=True)
    report["state"] = "launched"
    atomic_json(RECEIPT, report)


if __name__ == "__main__":
    main()
