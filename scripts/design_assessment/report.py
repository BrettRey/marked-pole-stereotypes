#!/usr/bin/env python3
"""Audit complete D1c run records and summarize design performance; never fit."""
import argparse
import csv
import hashlib
import itertools
import json
import platform
import sys
from collections import defaultdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from metrics import continuous, performance

ROOT = Path(__file__).resolve().parents[2]
FIELDS = ("design", "scenario", "target", "feedback", "reliability", "prior", "cell")
ESTIMANDS = ("h2_prevalence_bridge", "h1_fixed_usage", "b_z", "marking")


def read_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def signature(row):
    return tuple(float(row[k]) if k in {"target", "reliability", "prior", "cell"} else row[k]
                 for k in FIELDS)


def estimands(cell):
    return ESTIMANDS + (("h2_display",) if cell["scenario"] == "display" else ())


def load_run(fits_path, status_path, log_path):
    log = json.loads(log_path.read_text())
    if log.get("script") != "scripts/d1c/d1c.py" or log.get("args", {}).get("command") not in {"pilot", "run"}:
        raise ValueError("Require a complete D1c pilot/run log; component records are not replications")
    for path in (p for p in (fits_path, status_path) if p is not None):
        if str(path.resolve().relative_to(ROOT.resolve())) not in log["outputs"]:
            raise ValueError("Input CSV is not one of this run log's outputs")
    count = 2 if log["args"]["command"] == "pilot" else int(log["args"]["reps"])
    planned = {(signature(c), rep): c for c in log["cells"] for rep in range(count)}
    if not planned or len(planned) != count*len(log["cells"]):
        raise ValueError("Missing or duplicated planned cells")
    statuses = read_csv(status_path)
    status_map, logged = {}, {}
    for record in log["statuses"]:
        key = (signature(record), int(record["rep"]))
        if key in logged:
            raise ValueError("Duplicated run-log dataset")
        logged[key] = record
    for record in statuses:
        key = (signature(record), int(record["rep"]))
        if key in status_map or key not in planned or key not in logged:
            raise ValueError("Duplicated, unplanned or unlogged dataset")
        if record["status"] not in {"converged", "diagnostic_failure", "exception"}:
            raise ValueError("Unknown attempt status")
        if record["status"] != logged[key]["status"]:
            raise ValueError("CSV/log status mismatch")
        if record["status"] != "exception":
            diagnostic = logged[key]["diagnostics"]
            expected = 1 if record["feedback"] == "joint" else 1+int(log["sampler"]["cut_draws"])
            if len(diagnostic) != expected:
                raise ValueError("Incomplete fit: conditional cut components are not replications")
            modes = [d["mode"] for d in diagnostic]
            if modes != (["joint"] if expected == 1 else ["upstream"]+["downstream"]*(expected-1)):
                raise ValueError("Unexpected or missing fitted modules")
            good = all(d["good"] and d.get("contrast_good", True) for d in diagnostic)
            if good != (record["status"] == "converged"):
                raise ValueError("Diagnostics/status mismatch")
        status_map[key] = record
    if set(status_map) != set(planned) or set(logged) != set(planned):
        raise ValueError("Run is incomplete; every planned dataset needs a terminal attempt record")
    fits, seen, seeds = [], set(), defaultdict(set)
    for raw in (read_csv(fits_path) if fits_path else []):
        if "component" in raw or raw.get("estimand") is None:
            raise ValueError("Conditional components are not whole-fit replication records")
        key = (signature(raw), int(raw["rep"]))
        marker = (key, raw["estimand"])
        if key not in planned or marker in seen or raw["estimand"] not in estimands(planned[key]):
            raise ValueError("Duplicated or unexpected fit/estimand")
        seen.add(marker)
        status = status_map[key]
        if status["status"] == "exception" or raw["good"] not in {"True", "False"}:
            raise ValueError("Fit has no compatible completion status")
        row = {k: raw[k] for k in FIELDS}
        row.update(rep=int(raw["rep"]), estimand=raw["estimand"], good=raw["good"] == "True",
                   data_seed=int(raw["data_seed"]), fit_seed=int(raw["fit_seed"]))
        for field in ("truth", "mean", "lo50", "hi50", "lo90", "hi90"):
            row[field] = float(raw[field])
        import math
        if not all(math.isfinite(row[f]) for f in ("truth", "mean", "lo50", "hi50", "lo90", "hi90")):
            raise ValueError("Nonfinite completed result")
        if not row["lo90"] <= row["lo50"] <= row["hi50"] <= row["hi90"]:
            raise ValueError("Non-nested posterior intervals")
        if row["good"] != (status["status"] == "converged"):
            raise ValueError("Fit/status convergence mismatch")
        for name in ("data_seed", "fit_seed"):
            if row[name] != int(status[name]) or row[name] != int(logged[key][name]):
                raise ValueError("Fit/status/log seed mismatch")
        seed_key = (signature(row), row["estimand"])
        if row["data_seed"] in seeds[seed_key]:
            raise ValueError("A generated dataset was repeated as an independent replicate")
        seeds[seed_key].add(row["data_seed"])
        fits.append(row)
    expected_rows = {(key, e) for key, c in planned.items()
                     if status_map[key]["status"] != "exception" for e in estimands(c)}
    if seen != expected_rows:
        raise ValueError("Missing whole-fit estimand records")
    return fits, statuses, log


def summarize(fits, statuses):
    by_cell, by_fit = defaultdict(list), defaultdict(list)
    for status in statuses:
        by_cell[signature(status)].append(status)
    for row in fits:
        by_fit[(signature(row), row["estimand"])].append(row)
    summaries = []
    for sig, attempts in by_cell.items():
        cell = dict(zip(FIELDS, sig))
        for estimand in estimands(cell):
            summaries.append(dict(cell=cell, estimand=estimand,
                **performance(by_fit[(sig, estimand)], len(attempts))))
    # Paired comparisons never inflate independent-dataset counts by pooling fits.
    families = defaultdict(dict)
    for (sig, estimand), rows in by_fit.items():
        cell = dict(zip(FIELDS, sig))
        family = (cell["design"], cell["scenario"], cell["target"], estimand)
        families[family][sig] = {(r["rep"], r["data_seed"]): r for r in rows if r["good"]}
    paired = []
    for family, specifications in families.items():
        for a, b in itertools.combinations(sorted(specifications), 2):
            left, right = specifications[a], specifications[b]
            keys = sorted(set(left) & set(right))
            if any(abs(left[k]["truth"]-right[k]["truth"]) > 1e-8 for k in keys):
                raise ValueError("Paired specifications disagree on generating truth")
            paired.append(dict(family=family, left=dict(zip(FIELDS, a)), right=dict(zip(FIELDS, b)),
                n_paired=len(keys), n_left=len(left), n_right=len(right),
                direction="left minus right; jointly converged pairs",
                bias_difference=continuous([left[k]["mean"]-right[k]["mean"] for k in keys]),
                width90_difference=continuous([(left[k]["hi90"]-left[k]["lo90"])-
                    (right[k]["hi90"]-right[k]["lo90"]) for k in keys])))
    return summaries, paired


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fits", type=Path, help="Omit only when every attempt is an execution exception")
    parser.add_argument("--statuses", type=Path, required=True)
    parser.add_argument("--run-log", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, default=Path(__file__).with_name("inputs.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    fits, statuses, run = load_run(args.fits, args.statuses, args.run_log)
    inputs = json.loads(args.inputs.read_text())
    summaries, paired = summarize(fits, statuses)
    output = dict(schema=1, observed_at=datetime.now(timezone.utc).isoformat(),
        purpose="Engineering integration report; not empirical-design calibration or a power claim",
        detection_rule="Equal-tailed 90% interval wholly on the true nonzero side of zero",
        substantive_benchmarks=None, generating_design="Original provisional D1c design",
        bootstrap_seed=20261010, bootstrap_repetitions=2000, null_tolerance=1e-8,
        rate_interval="Exact Clopper–Pearson 95% intervals across independent datasets",
        limitations=["Two pilot datasets do not establish design performance." if run["args"]["command"] == "pilot" else
            "Assess replication uncertainty before interpreting performance.",
            f"Original per-component contrast budget: {run['sampler']['contrast_draws']}; historical summaries are not recomputed from full traces.",
            "Quantile and RMSE bootstrap SEs may be unstable with few independent datasets.",
            "Rate denominators can vary; selected metrics use only selected nonzero-truth fits.",
            "A failure counts as no usable detection in the per-attempt measure, not evidence of a null effect."],
        input_registry=inputs, summaries=summaries, paired_comparisons=paired,
        provenance={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (args.fits, args.statuses, args.run_log, args.inputs) if p is not None},
        run_identity={k: run[k] for k in ("timestamp", "git_sha", "git_dirty", "sampler")},
        environment=dict(python=sys.version, platform=platform.platform(),
            packages={p: version(p) for p in ("numpy", "scipy")}),
        source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in Path(__file__).parent.glob("*.py")})
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "assessment.json").write_text(json.dumps(output, indent=2, allow_nan=False)+"\n")
    lines = ["# Design-assessment integration check", "", output["purpose"]+".", "",
        "The input registry still has unresolved empirical-design inputs. Substantive benchmarks remain unset.", "",
        "| Cell | Estimand | Attempted | Converged | Mean 90% width | Width MCSE | 90% coverage | Exact 95% interval for coverage |",
        "|---|---|---:|---:|---:|---:|---|---|"]
    def fmt(x):
        return "undefined" if x is None else f"{x:.4f}"
    for row in summaries:
        width, cov = row["metrics"]["width90_mean"], row["metrics"]["coverage90"]
        lines.append(f"| {int(row['cell']['cell'])} | {row['estimand']} | {row['attempted_datasets']} | "
            f"{row['converged_fits']} | {fmt(width['estimate'])} | {fmt(width['mcse'])} | "
            f"{cov['events']}/{cov['n']} | {fmt(cov['lo95'])}–{fmt(cov['hi95'])} |")
    lines += ["", *output["limitations"], "", "All metrics, failure denominators, pairing and provenance: `assessment.json`."]
    (args.output / "REPORT.md").write_text("\n".join(lines)+"\n")
    print(json.dumps(dict(output=str(args.output), cells=len(run["cells"]),
                         fit_attempts=len(statuses), whole_fit_rows=len(fits), calibration=False)))


if __name__ == "__main__":
    main()
