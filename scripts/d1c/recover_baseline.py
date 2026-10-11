#!/usr/bin/env python3
"""One diagnosed infrastructure recovery, with storage failures isolated from fits."""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import baseline_batch as batch
import grid
import monitor_baseline_batch as original_monitor
import paired_batch as paired
from collect_parallel import TERMINAL_HF, command
from launch_hf_batch import BUCKET, IMAGE
from run_component import verify_published_source
from run_state import atomic_json

ORIGINAL = "94eb4e41ec22a4e00de7ef243e6da6985af7756a"
CELLS = (0, 12)
ROOT = batch.ROOT
BATCH = ROOT / "results/d1c/baseline-recovery-20261011"
CACHE = ROOT / ".cache/d1c/baseline-recovery-20261011"
RECEIPT = ROOT / "logs/d1c-baseline-recovery-launch-20261011.json"
PATHS = ("scripts/d1c/recover_baseline.py", "scripts/d1c/BASELINE-RECOVERY.md")
REMOTE = BUCKET + "/20261011/baseline-recovery"
MAXIMUM_NEW_USD = 2 * 12 * .03
TOTAL_RESERVED_USD = 13.08 + MAXIMUM_NEW_USD
BOOTSTRAP = '''set -eu
git clone --quiet https://github.com/BrettRey/marked-pole-stereotypes.git /work
cd /work
git checkout --quiet "$1"
python -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -r requirements-d1.txt
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
exec .venv/bin/python -u scripts/d1c/recover_baseline.py --source "$1" --cell "$2"
'''


def now():
    return datetime.now(timezone.utc).isoformat()


def verify(source):
    verify_published_source(source, PATHS)
    verify_published_source(ORIGINAL, batch.PATHS)


def export_attempt(base, destination, copied, export=paired.export_snapshot):
    """A storage outage must not propagate into a live sampler's controller."""
    try:
        export(base, destination, copied)
        return True
    except OSError as exc:
        event = dict(at=now(), error=repr(exc), action="retry_export_without_restarting_worker")
        with (base / "export-errors.jsonl").open("a") as stream:
            stream.write(json.dumps(event) + "\n")
        print(json.dumps(event), flush=True)
        return False


def finish_export(base, destination, copied, validate, timeout=1800, pause=time.sleep,
                  clock=time.monotonic, attempt=export_attempt):
    deadline = clock() + timeout
    while True:
        if attempt(base, destination, copied):
            try:
                validate()
                return
            except OSError:
                pass
        if clock() >= deadline:
            raise TimeoutError("Completed worker export did not validate within 30 minutes")
        pause(30)


def controller(source, cell):
    if cell not in CELLS:
        raise ValueError("Recovery is restricted to cells 0 and 12")
    verify(source)
    grid.configure_sampler(4000, 2000, 8000)
    name = batch.module_name(cell, "joint")
    base = batch.BATCH / "joint-0"
    base.mkdir(parents=True, exist_ok=False)
    spec = batch.specification(ORIGINAL)
    atomic_json(base / "specification.json", spec)
    destination = Path("/outputs/20261011/baseline-recovery") / name
    progress = dict(state="running", cell=cell, module=name, original_source=ORIGINAL,
                    recovery_source=source, started_at=now(), pid=os.getpid())
    atomic_json(base / "recovery.json", progress)
    copied = {}
    stream = (base / f"{name}-stdout.txt").open("x")
    worker = subprocess.Popen([sys.executable, "-u", str(ROOT / "scripts/d1c/baseline_batch.py"),
        "--source", ORIGINAL, "--host", "joint-0", "--worker", name], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        while worker.poll() is None:
            progress.update(worker_pid=worker.pid, updated_at=now())
            atomic_json(base / "recovery.json", progress)
            export_attempt(base, destination, copied)
            time.sleep(30)
        progress.update(worker_returncode=worker.returncode, ended_at=now())
        if worker.returncode:
            progress["state"] = "worker_failed"
            atomic_json(base / "recovery.json", progress)
            finish_export(base, destination, copied, lambda: None)
            raise RuntimeError(f"Worker exited {worker.returncode}; no model retry")
        record, _ = batch.check_module(base / "modules" / name, spec, name)
        progress.update(state="complete", archive_sha256=record["archive_sha256"])
        atomic_json(base / "recovery.json", progress)
        finish_export(base, destination, copied,
                      lambda: batch.check_module(destination / "modules" / name, spec, name))
        print(json.dumps(progress), flush=True)
    finally:
        if worker.poll() is None:
            paired.stop_group(worker)
        stream.close()


def hf_command(source, cell):
    if cell not in CELLS:
        raise ValueError("Unexpected recovery cell")
    return ["hf", "jobs", "run", "--format", "json", "--detach", "--flavor", "cpu-upgrade",
        "--timeout", "12h", "--attempts", "1", "--name", f"d1c-recover-c{cell:03d}-20261011",
        "--volume", f"{BUCKET}:/outputs:rw", "--", IMAGE, "bash", "-lc", BOOTSTRAP,
        "d1c-recovery", source, str(cell)]


def launch(source):
    verify(source)
    if RECEIPT.exists():
        raise RuntimeError("Recovery receipt exists; inspect it, never blindly resubmit")
    old = json.loads((batch.BATCH / "status.json").read_text())
    if old["state"] != "incomplete_terminal" or set(batch.jobs()) - set(old["completed_cells"]) != set(CELLS):
        raise ValueError("Original missing-cell set differs")
    existing = json.loads(command("hf", "jobs", "list", "--all", "--format", "json"))
    names = {f"d1c-recover-c{c:03d}-20261011" for c in CELLS}
    if any(j.get("labels", {}).get("name") in names for j in existing):
        raise RuntimeError("Unreconciled provider recovery submission")
    assert TOTAL_RESERVED_USD <= 15
    record = dict(state="submitting", source_commit=source, original_source=ORIGINAL,
        started_at=now(), cells=list(CELLS), maximum_new_compute_usd=MAXIMUM_NEW_USD,
        total_reserved_usd=TOTAL_RESERVED_USD, authorized_usd=15, timeout_seconds=43200,
        maximum_attempts=1, jobs={})
    atomic_json(RECEIPT, record)
    env = os.environ.copy()
    env.pop("HF_TOKEN", None)
    for cell in CELLS:
        record["jobs"][str(cell)] = dict(state="submitting")
        atomic_json(RECEIPT, record)
        result = subprocess.run(hf_command(source, cell), cwd=ROOT, env=env,
                                capture_output=True, text=True, timeout=90)
        item = dict(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
        if result.returncode == 0:
            item.update(state="accepted", id=json.loads(result.stdout)["id"])
        else:
            item["state"] = "submission_failed_or_ambiguous"
        record["jobs"][str(cell)] = item
        atomic_json(RECEIPT, record)
        if result.returncode:
            raise RuntimeError("Submission failed; reconcile receipt before another action")
    record["state"] = "launched"
    atomic_json(RECEIPT, record)
    return record


def refresh(item):
    cell, entry = item
    cell = int(cell)
    info = dict(cell=cell, id=entry.get("id"), stage="UNKNOWN")
    try:
        if entry["state"] != "accepted":
            raise ValueError("Recovery submission not accepted")
        job = json.loads(command("hf", "jobs", "inspect", "BrettRey/" + entry["id"], "--json"))[0]
        info.update(stage=job["status"]["stage"], durations=job.get("durations", {}))
        name = batch.module_name(cell, "joint")
        command("hf", "buckets", "sync", f"{REMOTE}/{name}", str(CACHE / name))
    except Exception as exc:
        info["error"] = repr(exc)
    return info


def collect(source):
    verify(source)
    grid.configure_sampler(4000, 2000, 8000)
    receipt = json.loads(RECEIPT.read_text())
    if receipt["source_commit"] != source or set(map(int, receipt["jobs"])) != set(CELLS):
        raise ValueError("Recovery receipt differs")
    state = dict(state="running", updated_at=now(), recovery_source=source, original_source=ORIGINAL,
        errors=[], jobs=[], estimated_recovery_compute_usd=0., total_reserved_usd=TOTAL_RESERVED_USD)
    with ThreadPoolExecutor(max_workers=2) as pool:
        state["jobs"] = list(pool.map(refresh, receipt["jobs"].items()))
    results = {int(k):v for k,v in json.loads((batch.BATCH / "results.json").read_text())["results"].items()}
    if set(results) != set(batch.jobs()) - set(CELLS):
        raise ValueError("Original 14-result snapshot differs")
    expected = batch.specification(ORIGINAL)
    for host in state["jobs"]:
        seconds = sum(host.get("durations", {}).get(k, 0) for k in ("starting_secs", "running_secs"))
        state["estimated_recovery_compute_usd"] += math.ceil(seconds / 60) * .03 / 60
        if host.get("error"):
            state["errors"].append(host["error"])
            continue
        cell = host["cell"]
        name = batch.module_name(cell, "joint")
        folder = CACHE / name
        runtime = folder / "modules" / name / "runtime.json"
        if not runtime.exists() or json.loads(runtime.read_text())["state"] != "complete":
            continue
        try:
            spec = json.loads((folder / "specification.json").read_text())
            if paired.scientific_identity(spec) != paired.scientific_identity(expected):
                raise ValueError("Recovered original scientific identity differs")
            record, _ = batch.check_module(folder / "modules" / name, expected, name)
            recovery = json.loads((folder / "recovery.json").read_text())
            if (recovery["cell"], recovery["original_source"], recovery["recovery_source"]) != (cell, ORIGINAL, source):
                raise ValueError("Recovery provenance differs")
            destination = BATCH / "collected/modules" / name
            shutil.copytree(folder / "modules" / name, destination, dirs_exist_ok=True)
            batch.check_module(destination, expected, name)
            result = batch.assemble_cell(BATCH / "collected", expected, cell)
            if result["archive_sha256"] != {"joint":record["archive_sha256"]}:
                raise ValueError("Recovery summary archive differs")
            results[cell] = result
        except Exception as exc:
            state["errors"].append(f"cell {cell}: {exc!r}")
    terminal = all(j["stage"] in TERMINAL_HF for j in state["jobs"])
    state["completed_cells"] = sorted(results)
    state["paired_comparisons"] = original_monitor.comparison_rows(results)
    if terminal:
        state["state"] = "complete" if len(results) == 16 and not state["errors"] else "incomplete_terminal"
    atomic_json(BATCH / "status.json", state)
    atomic_json(BATCH / "results.json", dict(results=results, recovery_source=source, original_source=ORIGINAL))
    lines = ["# Baseline recovery and combined results", "", f"Updated {state['updated_at']}. "
        f"State: **{state['state']}**. Completed configurations: **{len(results)}/16**.", "",
        "Original 14 results are preserved in ../baseline-batch-20261010/. Only interrupted cells 0 and 12 "
        "are recovered; original data, seeds and model code are unchanged.", "",
        "| Cell | Diagnostic status |", "|---|---|"]
    lines += [f"| {c} | {results[c]['status']['status'] if c in results else 'pending recovery'} |" for c in batch.jobs()]
    lines += ["", "| Cell | Contrast | Generated truth | Mean | 50% interval | 90% interval |",
              "|---|---|---:|---:|---|---|"]
    for cell, result in sorted(results.items()):
        for r in result["rows"]:
            lines.append(f"| {cell} | {r['estimand']} | {r['truth']:.5f} | {r['mean']:.5f} | "
                f"[{r['lo50']:.5f}, {r['hi50']:.5f}] | [{r['lo90']:.5f}, {r['hi90']:.5f}] |")
    lines += ["", "One artificial dataset per design/target; this is not replicated calibration. "
        "Eight outer draws do not establish cut-integration accuracy. Diagnostic failures remain visible. "
        "Paired mean differences and width ratios are retained in status.json; they are not posterior "
        "intervals for differences.", "", f"Recovery compute estimate USD {state['estimated_recovery_compute_usd']:.4f}, "
        "not an invoice. Conservative reservation for all work: USD 13.80 of USD 15."]
    if state["errors"]:
        lines += ["", "Collection issues: " + "; ".join(state["errors"])]
    (BATCH / "REPORT.md").write_text("\n".join(lines) + "\n")
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--launch", action="store_true")
    mode.add_argument("--watch", action="store_true")
    mode.add_argument("--cell", type=int, choices=CELLS)
    args = parser.parse_args()
    if args.launch:
        print(json.dumps(launch(args.source)))
    elif args.cell is not None:
        controller(args.source, args.cell)
    else:
        while True:
            state = collect(args.source)
            print(json.dumps(state), flush=True)
            if state["state"] != "running":
                break
            time.sleep(60)


if __name__ == "__main__":
    main()
