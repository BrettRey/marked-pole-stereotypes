#!/usr/bin/env python3
"""Summarize the assigned cut from all eight saved components; never fit."""
from __future__ import annotations

import argparse
import copy
import csv
import fcntl
import hashlib
import json
import os
import platform
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np

import collect_parallel as collection
from run_state import atomic_json, plain

ROOT = collection.ROOT
OUTPUT = ROOT / "results/d1c/complete-cut-20261010"
LOCATIONS = ("cloud", "local", "hf", "local-003", "hf-004", "hf-005", "hf-006", "local-007")
SOURCE_PATHS = ("scripts/d1c/assemble_cut.py", "scripts/d1c/ASSEMBLY.md",
                "scripts/d1c/collect_parallel.py", "scripts/d1c/component_state.py",
                "scripts/d1c/run_state.py", "scripts/d1c/d1c.py")
FIELDS = ("estimand", "truth", "mean", "median", "lo50", "hi50", "lo90", "hi90",
          "width50", "width90", "error", "good", "data_seed", "fit_seed")


class IncompleteCut(ValueError):
    pass


class ReadOnlyComponents:
    """A missing cached result raises before the fit function can sample."""
    def __init__(self, records):
        expected = {"upstream"} | {f"downstream-{i:03d}" for i in range(8)}
        if set(records) != expected or any(value is None for value in records.values()):
            raise IncompleteCut("Require upstream and exactly eight downstream components")
        self.records = records

    def load(self, key):
        if key not in self.records:
            raise IncompleteCut(f"Missing completed component: {key}")
        metadata, arrays = self.records[key]
        return copy.deepcopy(metadata), arrays

    def save(self, *args, **kwargs):
        raise RuntimeError("Assembly cannot write or fit a component")


def canonical_manifest():
    return json.loads(collection.command("git", "show",
        f"{collection.UPSTREAM_COMMIT}:{collection.CLOUD_PATH}/checkpoints/manifest.json"))


def read_complete(folder, canonical):
    records, provenance = {}, []
    missing = [i for i, location in enumerate(LOCATIONS)
               if not (folder / "collected" / location / "checkpoints" /
                       f"component-downstream-{i:03d}.json").exists()]
    if missing:
        raise IncompleteCut(f"Waiting for collected components {missing}")
    for component, location in enumerate(LOCATIONS):
        directory = folder / "collected" / location
        result = collection.validate_assignment(directory, location, component, canonical)
        if result is None:
            raise IncompleteCut(f"Missing completed component {component}")
        record, arrays = result
        if any(not np.isfinite(values).all() for values in arrays.values()):
            raise ValueError(f"Nonfinite contrasts in component {component}")
        spec = collection.json_file(directory / "checkpoints/manifest.json")["specification"]
        for name in ("scripts/d1c/d1c.py", "scripts/d1c/component_state.py"):
            if spec.get("sources", {}).get(name) != canonical["specification"]["sources"][name]:
                raise ValueError(f"Missing or changed scientific source in component {component}")
        records[f"downstream-{component:03d}"] = (record["metadata"], arrays)
        provenance.append(dict(component=component, location=location,
            archive_sha256=record["archive_sha256"], signature=record["signature"],
            marker_sha256=hashlib.sha256((directory / "checkpoints" /
                f"component-downstream-{component:03d}.json").read_bytes()).hexdigest()))
    upstream = collection.verify_component(folder / "collected/cloud/checkpoints", "upstream")
    if upstream is None:
        raise IncompleteCut("Missing upstream checkpoint")
    _, record, arrays = upstream
    shapes = {"z": (8, 400), "v": (8, 400), "s": (8, 400), "h": (8, 400, 3)}
    if set(arrays) != set(shapes):
        raise ValueError("Unexpected upstream variables for the assigned cell")
    if any(values.shape != shapes[name] or not np.isfinite(values).all()
           for name, values in arrays.items()):
        raise ValueError("Invalid selected upstream draws")
    records["upstream"] = (record["metadata"], arrays)
    return ReadOnlyComponents(records), provenance


def verify_runtime(canonical, source):
    if len(source) != 40 or any(c not in "0123456789abcdef" for c in source):
        raise ValueError("Require the full published assembly commit")
    collection.command("git", "merge-base", "--is-ancestor", source, "origin/master")
    for name in SOURCE_PATHS:
        frozen = collection.command("git", "show", f"{source}:{name}")
        if (ROOT / name).read_bytes() != frozen:
            raise ValueError(f"Assembly source differs from published commit: {name}")
    spec = canonical["specification"]
    for name, expected in spec["sources"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Scientific source differs from original run: {name}")
    for name, expected in spec["packages"].items():
        if version(name) != expected:
            raise ValueError(f"Package differs from original run: {name}")
    return {name: version(name) for name in spec["packages"]}


def replay(cache, job):
    import d1c
    if d1c.CUT_DRAWS != 8:
        raise ValueError("Unexpected outer cut budget")
    # Every lookup is present; ReadOnlyComponents raises rather than returning
    # None on a cache miss, so d1c.fit cannot enter its sampling branches.
    historical, status = d1c.fit(job, components=cache)
    stacked = {name: np.stack([cache.records[f"downstream-{i:03d}"][1][name]
                               for i in range(8)]) for name in collection.NAMES}
    rows = []
    for item in historical:
        name = "h2" if item["estimand"].startswith("h2_") else item["estimand"]
        row = {key: item[key] for key in FIELDS if key != "median"}
        row["median"] = float(np.median(stacked[name]))
        rows.append(plain(row))
    return rows, status, stacked


def render(result):
    job = result["job"]
    lines = ["# Completed D1c cut: one artificial dataset", "",
        f"Cell {job['cell']}, replicate {job['rep']}: {job['design']}, {job['scenario']}, "
        f"target {job['target']}, register reliability {job['reliability']}, prior scale {job['prior']}.", "",
        f"Status: **{result['status']}**. All eight assigned components are present, "
        "with equal weight. Each supplies 16,000 draws; each contrast has 128,000 draws.", "",
        "| Contrast | Generated truth | Mean | Median | 50% interval | 90% interval | Mean error |",
        "|---|---:|---:|---:|---|---|---:|"]
    for row in result["summaries"]:
        lines.append(f"| {row['estimand']} | {row['truth']:.5f} | {row['mean']:.5f} | "
            f"{row['median']:.5f} | [{row['lo50']:.5f}, {row['hi50']:.5f}] | "
            f"[{row['lo90']:.5f}, {row['hi90']:.5f}] | {row['error']:.5f} |")
    lines += ["", "H2 and H1 are mean log production-probability contrasts. Marking is a "
        "probability difference; b_z is the direct production coefficient.", "",
        "| Module | Parameter R-hat | Parameter ESS | Divergences | Contrast R-hat | Contrast ESS | Pass |",
        "|---|---:|---:|---:|---:|---:|---|"]
    for i, diagnostic in enumerate(result["diagnostics"]):
        values = [diagnostic.get(key) for key in ("rhat", "ess", "divergences", "contrast_rhat", "contrast_ess")]
        cells = ["n/a" if value is None else f"{value:.4g}" for value in values]
        good = diagnostic["good"] and diagnostic.get("contrast_good", True)
        lines.append("| " + ("upstream" if i == 0 else f"component {i-1}") + " | " +
                     " | ".join(cells) + f" | {'yes' if good else 'no'} |")
    lines += ["", *result["limitations"], "",
        "`assembly.json` records provenance and diagnostics; `summaries.csv` holds the "
        "numeric table. `contrasts.npz` preserves arrays as [component, draw]."]
    return "\n".join(lines) + "\n"


def assemble(folder, output, source, canonical, packages):
    cache, provenance = read_complete(folder, canonical)
    rows, status, stacked = replay(cache, canonical["specification"]["job"])
    if status["data_seed"] != canonical["specification"]["seeds"]["data"]:
        raise ValueError("Regenerated artificial dataset seed differs")
    result = dict(schema=1, observed_at=datetime.now(timezone.utc).isoformat(),
        job=canonical["specification"]["job"], status=status["status"],
        complete_assigned_cut=True, empirical_design_calibration=False,
        independent_datasets=1, component_weights=[1/8]*8,
        draws_per_component=16000, total_draws_per_contrast=128000,
        summaries=rows, diagnostics=status["diagnostics"],
        sampler=canonical["specification"]["sampler"],
        upstream_archive_sha256=collection.UPSTREAM_SHA,
        upstream_signature=canonical["signature"], components=provenance,
        assembly_source_commit=source,
        environment=dict(python=sys.version, platform=platform.platform(), packages=packages),
        source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCE_PATHS},
        limitations=[
            "This is the finite eight-component approximation to one cut posterior. Inner-chain "
            "diagnostics do not establish the accuracy of the eight-draw outer approximation.",
            "One artificial dataset cannot establish coverage, power or empirical-design calibration. "
            "Conditional components and posterior draws are not study replications.",
            "The original provisional vocabulary and response structure remain in this engineering run. "
            "No substantive support threshold or D1 verdict is assigned. The full grid remains stopped.",
            "Diagnostic failures, if any, are retained. R-hat and ESS are assessed within each "
            "module, not across different conditional distributions."])
    if output.exists():
        raise FileExistsError(f"Assembly output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".cut-assembly-", dir=output.parent))
    try:
        np.savez_compressed(temporary / "contrasts.npz", **stacked)
        result["contrast_archive_sha256"] = hashlib.sha256((temporary / "contrasts.npz").read_bytes()).hexdigest()
        with (temporary / "summaries.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        (temporary / "REPORT.md").write_text(render(result))
        atomic_json(temporary / "assembly.json", result)
        os.rename(temporary, output)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    lock_path = ROOT / ".cache/d1c/cut-assembly.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        canonical = canonical_manifest()
        packages = verify_runtime(canonical, args.source)
        while True:
            try:
                # A watch may outlive edits in another session. Recheck the
                # pinned sources before importing/replaying the scientific code.
                packages = verify_runtime(canonical, args.source)
                result = assemble(collection.OUTPUT, OUTPUT, args.source, canonical, packages)
                print(json.dumps(dict(state="complete", status=result["status"], output=str(OUTPUT))), flush=True)
                return
            except IncompleteCut as exc:
                print(json.dumps(dict(state="pending", message=str(exc),
                    observed_at=datetime.now(timezone.utc).isoformat())), flush=True)
                status_path = collection.OUTPUT / "status.json"
                terminal = status_path.exists() and collection.json_file(status_path).get("all_assigned_jobs_terminal")
                if terminal or not args.watch:
                    raise SystemExit(2)
                time.sleep(60)


if __name__ == "__main__":
    main()
