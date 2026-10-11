#!/usr/bin/env python3
"""Read-only cloud collector: no fitting, submission, cancellation or retries."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/d1c"))
from collect_parallel import command, verify_component, TERMINAL_HF
from run_state import atomic_json, digest

BASE = ROOT / "results/compute/packing-20261011"
CACHE = ROOT / ".cache/compute/packing-20261011"
REMOTE = "hf://buckets/BrettRey/marked-pole-d1c-compute/20261011/packing"


def refresh(item):
    profile, entry = item
    state = dict(profile=profile, job_id=entry["id"], stage="UNKNOWN", modules=[])
    try:
        job = json.loads(command("hf", "jobs", "inspect", "BrettRey/"+entry["id"], "--json"))[0]
        state.update(stage=job["status"]["stage"], durations=job.get("durations", {}),
                     compute_estimate_usd=job.get("durations", {}).get("running_secs", 0)*.03/3600)
        command("hf", "buckets", "sync", f"{REMOTE}/{profile}", str(CACHE / profile))
        base = CACHE / profile
        if (base / "receipt.json").exists():
            state["receipt"] = json.loads((base / "receipt.json").read_text())
        if not (base / "specification.json").exists():
            return state
        spec = json.loads((base / "specification.json").read_text())
        state["specification"] = spec
        for component in spec["settings"]["components"]:
            directory = base / f"component-{component:03d}"
            path = directory / "runtime.json"
            if not path.exists():
                continue
            runtime = json.loads(path.read_text())
            if runtime["state"] == "complete":
                key = f"downstream-{component:03d}"
                verified = verify_component(directory / "checkpoints", key)
                if verified is None:
                    raise ValueError("Completed worker has no valid checkpoint")
                manifest, record, arrays = verified
                if manifest["signature"] != digest(dict(spec, component=component)):
                    raise ValueError("Checkpoint specification differs")
                if record["archive_sha256"] != runtime["archive_sha256"]:
                    raise ValueError("Runtime/archive hash differs")
                runtime["archive_verified"] = True
                diag = record["metadata"]["diagnostic"]
                runtime["diagnostics_pass"] = bool(diag["good"] and diag["contrast_good"])
            state["modules"].append(runtime)
        completed = [r for r in state["modules"] if r.get("archive_verified")]
        state["verified_completed"] = len(completed)
        state["usable"] = (state.get("receipt", {}).get("state") == "complete"
                            and len(completed) == 6 and all(r["diagnostics_pass"] for r in completed))
        if completed and state["durations"].get("running_secs", 0):
            state["completed_per_machine_hour"] = len(completed)*3600/state["durations"]["running_secs"]
            state["compute_usd_per_completed"] = state["compute_estimate_usd"]/len(completed)
    except Exception as error:
        state["error"] = repr(error)
    return state


def report(state):
    lines = ["# Compute packing check", "", f"Updated {state['updated_at']}. **{state['state']}**.", "",
             "Hardware repeats only; excluded from calibration. Same six archived conditional fits in each arm.", "",
             "| Arm | Provider | Active | Verified completed | Peak sampled RSS | Compute estimate |",
             "|---|---|---:|---:|---:|---:|"]
    for arm in state["arms"]:
        receipt = arm.get("receipt", {})
        lines.append(f"| {arm['profile']} | {arm['stage']} | {len(receipt.get('active', {}))} | "
                     f"{arm.get('verified_completed', 0)}/6 | "
                     f"{receipt.get('peak_sampled_group_rss_bytes', 0)/2**30:.2f} GiB | "
                     f"USD {arm.get('compute_estimate_usd', 0):.4f} |")
    lines.extend(["", "Duration-based compute estimates are not invoices. Maximum new compute USD .72. "
                  "No throughput conclusion before both jobs end and their artifacts are verified.", ""])
    if state["state"] == "complete":
        for arm in state["arms"]:
            lines.append(f"- {arm['profile']}: usable={arm.get('usable', False)}; "
                         f"{arm.get('completed_per_machine_hour', 0):.3f} completed fits/machine-hour; "
                         f"USD {arm.get('compute_usd_per_completed', 0):.4f}/completed fit.")
        lines.append("\nA single pair of machines does not estimate provider-wide variability.")
    (BASE / "REPORT.md").write_text("\n".join(lines)+"\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    launch = json.loads((ROOT / "logs/compute-packing-launch-20261011.json").read_text())
    BASE.mkdir(parents=True, exist_ok=True)
    deadline, terminal_incomplete = time.monotonic()+13*3600, 0
    while True:
        with ThreadPoolExecutor(max_workers=2) as pool:
            arms = list(pool.map(refresh, launch["jobs"].items()))
        terminal = all(a["stage"] in TERMINAL_HF for a in arms)
        verified = all(a.get("verified_completed") == 6 and not a.get("error") for a in arms)
        terminal_incomplete = terminal_incomplete+1 if terminal and not verified else 0
        state = dict(state="complete" if terminal and verified else
                     "incomplete_terminal" if terminal else "running",
                     updated_at=datetime.now(timezone.utc).isoformat(), arms=arms,
                     maximum_new_usd=.72, calibration_replicates_added=0)
        atomic_json(BASE / "status.json", state)
        report(state)
        print(json.dumps({"at": state["updated_at"], "state": state["state"],
            "arms": [{k: a.get(k) for k in ("profile", "stage", "verified_completed", "error")} for a in arms]}), flush=True)
        if not args.watch or (terminal and verified) or terminal_incomplete >= 3 or time.monotonic() >= deadline:
            return
        time.sleep(60)


if __name__ == "__main__":
    main()
