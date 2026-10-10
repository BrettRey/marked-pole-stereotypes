#!/usr/bin/env python3
"""Submit the authorized baseline extension, filling available HF capacity."""
import argparse
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone

from baseline_batch import BATCH, PATHS, ROOT, hosts
from collect_parallel import command
from launch_hf_batch import BUCKET, IMAGE
from run_component import verify_published_source
from run_state import atomic_json

RECEIPT = ROOT / "logs/d1c-baseline-batch-launch-20261010.json"
MAXIMUM_NEW_USD = 27 * 12 * .03
TOTAL_RESERVED_USD = 2.16 + 1.20 + MAXIMUM_NEW_USD
AUTHORIZED_USD = 15
BOOTSTRAP = '''set -eu
git clone --quiet https://github.com/BrettRey/marked-pole-stereotypes.git /work
cd /work
git checkout --quiet "$1"
exec bash scripts/d1c/baseline_batch.sh "$1" "$2"
'''


def label(host):
    return f"d1c-baseline-{host}-20261010"


def hf_command(source, host, execute):
    cmd = ["hf", "jobs", "run", "--format", "json", "--detach", "--flavor", "cpu-upgrade",
        "--timeout", "12h", "--attempts", "1", "--name", label(host),
        "--volume", f"{BUCKET}:/outputs:rw"]
    if not execute:
        cmd.append("--dry-run")
    return cmd + ["--", IMAGE, "bash", "-lc", BOOTSTRAP, "d1c-job", source, host]


def quota_rejection(message):
    return bool(re.search(r"(?i)(HTTP[^\n]*429|429 Too Many|too many (concurrent|running|active) jobs|"
        r"concurren[^\n]{0,100}(limit|quota)|(limit|quota)[^\n]{0,100}(concurren|running jobs))", message))


def reconcile(record, listed):
    """An interrupted submission is never blindly repeated."""
    for host, item in record["hosts"].items():
        if item["state"] != "submitting":
            continue
        matches = [j for j in listed if j.get("labels", {}).get("name") == label(host)]
        if len(matches) != 1 or record["source_commit"] not in matches[0].get("command", ""):
            raise RuntimeError(f"Ambiguous submission for {host}; inspect provider before another attempt")
        item.update(state="accepted", id=matches[0]["id"], reconciled=True)


def launch(source, watch):
    verify_published_source(source, PATHS)
    assert len(hosts()) == 27 and TOTAL_RESERVED_USD <= AUTHORIZED_USD
    if RECEIPT.exists():
        record = json.loads(RECEIPT.read_text())
        if (record["source_commit"] != source or
                {h:v["modules"] for h,v in record["hosts"].items()} != hosts()):
            raise RuntimeError("Launch record differs")
        if any(v["state"] == "submitting" for v in record["hosts"].values()):
            reconcile(record, json.loads(command("hf", "jobs", "list", "--all", "--format", "json")))
    else:
        existing = json.loads(command("hf", "jobs", "list", "--all", "--format", "json"))
        if any(j.get("labels", {}).get("name") in {label(h) for h in hosts()} for j in existing):
            raise RuntimeError("Provider has baseline jobs without this local receipt; reconcile before launch")
        record = dict(state="submitting", source_commit=source, image=IMAGE, bucket=BUCKET,
            started_at=datetime.now(timezone.utc).isoformat(), maximum_attempts_per_job=1,
            timeout_seconds_per_job=43200, hourly_compute_usd=.03, maximum_new_compute_usd=MAXIMUM_NEW_USD,
            total_conservative_reserved_usd=TOTAL_RESERVED_USD, total_authorized_hf_usd=AUTHORIZED_USD,
            hosts={h:dict(state="pending", modules=names, submission_requests=0) for h,names in hosts().items()})
    atomic_json(RECEIPT, record)
    environment = os.environ.copy()
    environment.pop("HF_TOKEN", None)
    while True:
        pending = [h for h in hosts() if record["hosts"][h]["state"] in {"pending", "capacity_wait"}]
        if not pending:
            record["state"] = "launched" if all(v["state"] == "accepted" for v in record["hosts"].values()) else "launch_failed"
            atomic_json(RECEIPT, record)
            return record
        for host in pending:
            item = record["hosts"][host]
            item.update(state="submitting", submission_requests=item["submission_requests"]+1,
                        submitted_at=datetime.now(timezone.utc).isoformat())
            atomic_json(RECEIPT, record)
            try:
                result = subprocess.run(hf_command(source, host, True), cwd=ROOT, env=environment,
                    capture_output=True, text=True, timeout=90)
            except BaseException as exc:
                record.update(state="submission_ambiguous", error=repr(exc))
                atomic_json(RECEIPT, record)
                raise
            item.update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
            if result.returncode == 0:
                item.update(state="accepted", id=json.loads(result.stdout)["id"])
                print(f"Accepted {host}: {item['id']}", flush=True)
            else:
                # A creation response can be lost. Look up the unique label
                # before deciding that rejection permits another request.
                if not quota_rejection(result.stderr):
                    try:
                        reconcile(record, json.loads(command("hf", "jobs", "list", "--all", "--format", "json")))
                    except Exception as exc:
                        record.update(state="submission_ambiguous", error=repr(exc))
                        atomic_json(RECEIPT, record)
                        raise
                if item["state"] == "accepted":
                    pass
                elif quota_rejection(result.stderr):
                    # Explicit service rejection means no model attempt ran.
                    item["state"] = "capacity_wait"
                    record["state"] = "waiting_for_capacity"
                    print(f"Capacity wait: {host}", flush=True)
                    atomic_json(RECEIPT, record)
                    break
                else:
                    item["state"] = "failed"
                    record["state"] = "launch_failed"
                    atomic_json(RECEIPT, record)
                    raise RuntimeError(f"Submission failed for {host}; no automatic model retry")
            atomic_json(RECEIPT, record)
        if not watch and any(v["state"] == "capacity_wait" for v in record["hosts"].values()):
            return record
        if any(v["state"] == "capacity_wait" for v in record["hosts"].values()):
            time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch("[0-9a-f]{40}", args.source):
        parser.error("Use full published source commit")
    if not args.execute:
        print(json.dumps(dict(hosts=hosts(), new_compute_ceiling=MAXIMUM_NEW_USD,
            total_reserved=TOTAL_RESERVED_USD, authorized=AUTHORIZED_USD), indent=2))
        return
    result = launch(args.source, args.watch)
    print(json.dumps(dict(state=result["state"], accepted=sum(v["state"] == "accepted" for v in result["hosts"].values()))))


if __name__ == "__main__":
    main()
