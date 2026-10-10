#!/usr/bin/env python3
"""Collect the baseline extension and reuse earlier fits; never sample or submit."""
import argparse
import json
import math
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import baseline_batch as batch
import grid
import paired_batch as paired
from collect_parallel import TERMINAL_HF, command
from launch_baseline_batch import RECEIPT
from run_component import verify_published_source
from run_state import atomic_json

CACHE = batch.ROOT / ".cache/d1c/baseline-batch"
REMOTE = "hf://buckets/BrettRey/marked-pole-d1c-compute/20261010/baseline-batch"
COMBINED = batch.BATCH / "collected"


def refresh(item):
    host, entry = item
    info = dict(host=host, submission_state=entry["state"], stage="PENDING")
    if entry["state"] != "accepted":
        return info
    info["id"] = entry["id"]
    try:
        job = json.loads(command("hf", "jobs", "inspect", "BrettRey/"+entry["id"], "--json"))[0]
        info.update(stage=job["status"]["stage"], durations=job.get("durations", {}))
        command("hf", "buckets", "sync", f"{REMOTE}/{host}", str(CACHE / host))
        path = CACHE / host / "progress.json"
        if path.exists():
            info["progress"] = json.loads(path.read_text())
    except Exception as exc:
        info["error"] = repr(exc)
    return info


def import_module(source, spec, name):
    record, _ = batch.check_module(source, spec, name)
    destination = COMBINED / "modules" / name
    if destination.exists():
        existing, _ = batch.check_module(destination, spec, name)
        if existing["archive_sha256"] != record["archive_sha256"]:
            raise ValueError(f"Changed collected module {name}")
        return
    temporary = destination.with_name("."+name+".collecting")
    if temporary.exists():
        shutil.rmtree(temporary)
    (temporary / "checkpoints").mkdir(parents=True)
    for path in (source / "checkpoints").iterdir():
        if path.name == "manifest.json" or path.name.startswith("component-"):
            shutil.copyfile(path, temporary / "checkpoints" / path.name)
    for filename in ("runtime.json", "result.json"):
        if (source / filename).exists():
            shutil.copyfile(source / filename, temporary / filename)
    batch.check_module(temporary, spec, name)
    temporary.rename(destination)


def reused_results():
    prior = json.loads((batch.ROOT / "results/d1c/complete-cut-20261010/assembly.json").read_text())
    results = {10:dict(rows=prior["summaries"], status=dict(prior["job"], status=prior["status"],
                                                        diagnostics=prior["diagnostics"]))}
    for location in ("local", "hf-joint", "hf-complete"):
        path = paired.BATCH / location / "results.json"
        if path.exists():
            for result in json.loads(path.read_text())["results"]:
                cell = result["status"]["cell"]
                if cell not in {4, 124, 130}:
                    raise ValueError("Unexpected reused cell")
                results[cell] = result
    return results


def comparison_rows(results):
    comparisons = []
    for cell, result in sorted(results.items()):
        s = result["status"]
        if s["feedback"] != "joint":
            continue
        paired_results = [r for r in results.values() if r["status"]["feedback"] == "cut" and
            all(r["status"][k] == s[k] for k in ("design", "scenario", "target", "reliability", "prior", "rep"))]
        if not paired_results:
            continue
        if len(paired_results) != 1:
            raise ValueError("Ambiguous joint/cut pairing")
        cut = {r["estimand"]:r for r in paired_results[0]["rows"]}
        for row in result["rows"]:
            other = cut[row["estimand"]]
            if row["data_seed"] != other["data_seed"] or abs(row["truth"]-other["truth"]) > 1e-12:
                raise ValueError("Joint/cut datasets differ")
            comparisons.append(dict(joint_cell=cell, cut_cell=paired_results[0]["status"]["cell"],
                design=s["design"], target=s["target"], reliability=s["reliability"], estimand=row["estimand"],
                mean_difference=row["mean"]-other["mean"], width90_ratio=row["width90"]/other["width90"]))
    return comparisons


def report(state, results):
    lines = ["# Parallel baseline engineering batch", "",
        f"Updated {state['updated_at']}. State: **{state['state']}**. "
        f"Completed configurations: **{len(results)}/16**.", "",
        "Fixed scope: both designs, targets 0/−.1, joint/cut and register reliability 0/.8, "
        "prior scale 1, replicate 0. Completed and running fits from the earlier batch are reused.", "",
        "| Host | Provider state | Active modules | Completed modules |", "|---|---|---:|---:|"]
    for host in state["hosts"]:
        p = host.get("progress") or {}
        lines.append(f"| {host['host']} | {host['stage']} | {len(p.get('active',{}))} | {len(p.get('completed',[]))} |")
    lines += ["", "| Cell | Design | Target | Register reliability | Fit | Diagnostic status |", "|---|---|---:|---:|---|---|"]
    for cell, job in batch.jobs().items():
        status = results[cell]["status"]["status"] if cell in results else "pending"
        lines.append(f"| {cell} | {job['design']} | {job['target']} | {job['reliability']} | {job['feedback']} | {status} |")
    lines += ["", "| Cell | Contrast | Generated truth | Mean | 50% interval | 90% interval |", "|---|---|---:|---:|---|---|"]
    for cell, result in sorted(results.items()):
        for r in result["rows"]:
            lines.append(f"| {cell} | {r['estimand']} | {r['truth']:.5f} | {r['mean']:.5f} | "
                         f"[{r['lo50']:.5f}, {r['hi50']:.5f}] | [{r['lo90']:.5f}, {r['hi90']:.5f}] |")
    lines += ["", "| Joint / cut cells | Contrast | Joint mean minus cut mean | Joint/cut 90% width |",
              "|---|---|---:|---:|"]
    for r in state["paired_comparisons"]:
        lines.append(f"| {r['joint_cell']} / {r['cut_cell']} | {r['estimand']} | {r['mean_difference']:.5f} | {r['width90_ratio']:.4f} |")
    lines += ["", "One artificial dataset per design/target, with paired specifications; this is not "
        "replicated calibration. Eight outer draws do not establish cut-integration accuracy. "
        "Inner-chain diagnostic failures remain visible. The provisional empirical-design inputs "
        "remain unresolved. Summary differences are not posterior intervals for differences.", "",
        f"New extension compute ceiling: USD {state['maximum_new_compute_usd']:.2f}. "
        f"Conservative total reservation: USD {state['total_reserved_usd']:.2f} of USD 15. "
        f"Observed extension compute estimate: USD {state['estimated_compute_usd']:.4f}, not an invoice."]
    if state["errors"]:
        lines += ["", "Collection issues: " + "; ".join(state["errors"])]
    (batch.BATCH / "REPORT.md").write_text("\n".join(lines)+"\n")


def collect(source):
    verify_published_source(source, batch.PATHS)
    grid.configure_sampler(4000, 2000, 8000)
    receipt = json.loads(RECEIPT.read_text())
    if receipt["source_commit"] != source:
        raise ValueError("Launch source differs")
    COMBINED.mkdir(parents=True, exist_ok=True)
    expected = batch.specification(source)
    state = dict(state="running", updated_at=datetime.now(timezone.utc).isoformat(), source_commit=source,
        hosts=[], errors=[], verified_modules=[], completed_cells=[], estimated_compute_usd=0.,
        maximum_new_compute_usd=receipt["maximum_new_compute_usd"],
        total_reserved_usd=receipt["total_conservative_reserved_usd"])
    with ThreadPoolExecutor(max_workers=8) as pool:
        state["hosts"] = list(pool.map(refresh, receipt["hosts"].items()))
    for host in state["hosts"]:
        durations = host.get("durations",{})
        seconds = sum(durations.get(k,0) for k in ("starting_secs","running_secs"))
        state["estimated_compute_usd"] += math.ceil(seconds/60)*.03/60
        if host.get("error"):
            state["errors"].append(host["host"]+": "+host["error"])
            continue
        folder = CACHE / host["host"]
        if not (folder / "specification.json").exists():
            continue
        try:
            spec = json.loads((folder / "specification.json").read_text())
            if paired.scientific_identity(spec) != paired.scientific_identity(expected):
                raise ValueError("Host source, package, or assignment identity differs")
            for name in expected["hosts"][host["host"]]:
                directory = folder / "modules" / name
                p = directory / "runtime.json"
                if not p.exists() or json.loads(p.read_text())["state"] != "complete":
                    continue
                import_module(directory, spec, name)
                state["verified_modules"].append(name)
        except Exception as exc:
            state["errors"].append(host["host"]+": "+repr(exc))
    results = reused_results()
    for cell in (*batch.JOINT_CELLS, *batch.CUT_CELLS):
        required = {name for name,info in expected["modules"].items() if info["job"]["cell"] == cell}
        if required <= set(state["verified_modules"]):
            results[cell] = batch.assemble_cell(COMBINED, expected, cell)
    state["completed_cells"] = sorted(results)
    state["paired_comparisons"] = comparison_rows(results)
    terminal = all(h["stage"] in TERMINAL_HF for h in state["hosts"])
    if len(results) == 16 and terminal and not state["errors"]:
        state["state"] = "complete"
    elif terminal and (paired.BATCH / "status.json").exists():
        earlier = json.loads((paired.BATCH / "status.json").read_text())
        if earlier["state"] != "running":
            state["state"] = "incomplete_terminal"
    atomic_json(batch.BATCH / "status.json", state)
    atomic_json(batch.BATCH / "results.json", dict(results=results, source_commit=source))
    report(state, results)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    while True:
        state = collect(args.source)
        print(json.dumps(dict(state=state["state"], updated_at=state["updated_at"],
            completed_cells=state["completed_cells"], verified_modules=len(state["verified_modules"]),
            stages={h["host"]:h["stage"] for h in state["hosts"]}, errors=state["errors"])), flush=True)
        if not args.watch or state["state"] != "running":
            break
        time.sleep(60)


if __name__ == "__main__":
    main()
