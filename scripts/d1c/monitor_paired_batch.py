#!/usr/bin/env python3
"""Collect this fixed batch and assemble cached fits; never submit or sample."""
import argparse
import hashlib
import json
import math
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import grid
from collect_parallel import TERMINAL_HF, command
from launch_paired_batch import RECEIPT
from paired_batch import (BATCH, ROOT, PATHS, check_module, final_results,
                          scientific_identity, shard_modules, specification)
from run_component import verify_published_source
from run_state import atomic_json

CACHE = ROOT / ".cache/d1c/paired-batch"
REMOTE = "hf://buckets/BrettRey/marked-pole-d1c-compute/20261010/paired-batch"


def import_module(source, destination, spec, name):
    record, _ = check_module(source, spec, name)
    if destination.exists():
        existing, _ = check_module(destination, spec, name)
        if existing["archive_sha256"] != record["archive_sha256"]:
            raise ValueError("A collected module changed")
        return
    temporary = destination.with_name("." + destination.name + ".collecting")
    if temporary.exists():
        shutil.rmtree(temporary)
    (temporary / "checkpoints").mkdir(parents=True)
    for path in (source / "checkpoints").iterdir():
        if path.name == "manifest.json" or path.name.startswith("component-"):
            shutil.copyfile(path, temporary / "checkpoints" / path.name)
    for name_ in ("runtime.json", "result.json"):
        if (source / name_).exists():
            shutil.copyfile(source / name_, temporary / name_)
    check_module(temporary, spec, name)
    temporary.rename(destination)


def write_report(state):
    lines = ["# Registered baseline joint/cut comparison", "",
        f"Updated {state['updated_at']}. Batch state: **{state['state']}**.", "",
        "One artificial dataset per production design. Paired fits are not independent "
        "replications; this is a computational comparison, not calibration or an empirical verdict.", "",
        "| Location | Provider/controller state | Completed modules |", "|---|---|---|"]
    for host in state["hosts"]:
        p = host.get("progress") or {}
        lines.append(f"| {host['name']} | {host['stage']} / {p.get('state', 'pending')} | "
                     f"{', '.join(p.get('completed', [])) or 'none'} |")
    if state.get("errors"):
        lines.extend(["", "Collection issues: " + "; ".join(state["errors"])])
    results = []
    previous = json.loads((ROOT / "results/d1c/complete-cut-20261010/assembly.json").read_text())
    results.append(dict(rows=previous["summaries"], status=dict(previous["job"], status=previous["status"])))
    for location in ("local", "hf-joint", "hf-complete"):
        path = BATCH / location / "results.json"
        if path.exists():
            results.extend(json.loads(path.read_text())["results"])
    lines += ["", "| Design / fit | Contrast | Mean | 50% interval | 90% interval | Diagnostic status |",
              "|---|---|---:|---|---|---|"]
    for result in results:
        s = result["status"]
        for row in result["rows"]:
            lines.append(f"| {s['design']} / {s['feedback']} | {row['estimand']} | {row['mean']:.5f} | "
                f"[{row['lo50']:.5f}, {row['hi50']:.5f}] | [{row['lo90']:.5f}, {row['hi90']:.5f}] | {s['status']} |")
    if len(results) == 4:
        lines += ["", "| Design | Contrast | Joint mean minus cut mean | Joint/cut 90% interval width |",
                  "|---|---|---:|---:|"]
        for design in ("uwa", "nicolas"):
            pair = {r["status"]["feedback"]: r for r in results if r["status"]["design"] == design}
            cut = {r["estimand"]: r for r in pair["cut"]["rows"]}
            for row in pair["joint"]["rows"]:
                other = cut[row["estimand"]]
                if row["data_seed"] != other["data_seed"] or abs(row["truth"] - other["truth"]) > 1e-12:
                    raise ValueError("Joint/cut datasets are not paired")
                lines.append(f"| {design} | {row['estimand']} | {row['mean']-other['mean']:.5f} | "
                             f"{row['width90']/other['width90']:.4f} |")
    lines += ["", "Cuts retain eight equally weighted upstream draws; inner-chain diagnostics do not "
        "establish the accuracy of that outer approximation. Failed diagnostics remain visible. "
        "Mean differences and width ratios describe the two posterior summaries; no posterior interval "
        "for their difference is implied. The 240-cell sweep remains stopped.", "",
        f"HF compute estimate from provider durations: USD {state['estimated_compute_usd']:.4f}; not an invoice."]
    (BATCH / "REPORT.md").write_text("\n".join(lines) + "\n")


def collect(source):
    verify_published_source(source, PATHS)
    grid.configure_sampler(4000, 2000, 8000)
    receipt = json.loads(RECEIPT.read_text())
    if receipt["source_commit"] != source:
        raise ValueError("Launch source differs")
    state = dict(state="running", updated_at=datetime.now(timezone.utc).isoformat(),
        source_commit=source, hosts=[], errors=[], verified_modules=[], estimated_compute_usd=0.)
    canonical = None
    combined = BATCH / "hf-complete"
    combined.mkdir(parents=True, exist_ok=True)
    for job in receipt["hf_jobs"]:
        if "id" not in job:
            state["errors"].append(f"HF shard {job['shard']} was not accepted")
            continue
        shard = job["shard"]
        name = "hf-joint" if job["location"] == "hf-joint" else f"hf-shard-{shard}"
        host = dict(name=name, id=job["id"], stage="UNKNOWN")
        state["hosts"].append(host)
        try:
            info = json.loads(command("hf", "jobs", "inspect", "BrettRey/"+job["id"], "--json"))[0]
            host["stage"] = info["status"]["stage"]
            host["durations"] = info.get("durations", {})
            seconds = sum(host["durations"].get(k, 0) for k in ("starting_secs", "running_secs"))
            state["estimated_compute_usd"] += math.ceil(seconds / 60)*.03/60
            command("hf", "buckets", "sync", f"{REMOTE}/{name}", str(CACHE / name))
            folder = CACHE / name
            if (folder / "progress.json").exists():
                host["progress"] = json.loads((folder / "progress.json").read_text())
            if not (folder / "specification.json").exists():
                continue
            spec = json.loads((folder / "specification.json").read_text())
            if spec["source_commit"] != source:
                raise ValueError("Provider source differs")
            if scientific_identity(spec) != scientific_identity(specification(source, job["location"])):
                raise ValueError("Provider scientific source or package versions differ")
            if job["location"] == "hf-joint":
                directory = folder / "modules/joint-124"
                runtime_path = directory / "runtime.json"
                if runtime_path.exists() and json.loads(runtime_path.read_text())["state"] == "complete":
                    joint_base = BATCH / "hf-joint"
                    import_module(directory, joint_base / "modules/joint-124", spec, "joint-124")
                    atomic_json(joint_base / "specification.json", spec)
                    if not (joint_base / "results.json").exists():
                        final_results(joint_base, spec)
                continue
            if canonical is None:
                canonical = spec
                atomic_json(combined / "specification.json", spec)
            if scientific_identity(spec) != scientific_identity(canonical):
                raise ValueError("Host scientific specifications differ")
            for name_ in (["upstream"] if shard == 0 else []) + shard_modules(shard):
                directory = folder / "modules" / name_
                # Wait for worker validation/runtime, not just a checkpoint marker.
                if not (directory / "runtime.json").exists():
                    continue
                runtime = json.loads((directory / "runtime.json").read_text())
                if runtime["state"] != "complete":
                    continue
                import_module(directory, combined / "modules" / name_, spec, name_)
                state["verified_modules"].append(name_)
        except Exception as exc:
            state["errors"].append(f"{name}: {exc!r}")
    if len(state["verified_modules"]) == 9 and not (combined / "results.json").exists():
        final_results(combined, canonical)
    local = BATCH / "local/progress.json"
    progress = json.loads(local.read_text()) if local.exists() else None
    state["hosts"].append(dict(name="local", stage=progress["state"] if progress else "pending", progress=progress))
    hf_terminal = len(state["hosts"]) == 6 and all(h["stage"] in TERMINAL_HF for h in state["hosts"][:-1])
    if (hf_terminal and (BATCH / "local/results.json").exists() and
            (BATCH / "hf-joint/results.json").exists() and
            (combined / "results.json").exists() and not state["errors"]):
        state["state"] = "complete"
    elif hf_terminal and progress and progress["state"] in {"complete", "failed"}:
        state["state"] = "incomplete_terminal"
    atomic_json(BATCH / "status.json", state)
    write_report(state)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    while True:
        result = collect(args.source)
        print(json.dumps(result), flush=True)
        if not args.watch or result["state"] != "running":
            break
        time.sleep(60)


if __name__ == "__main__":
    main()
