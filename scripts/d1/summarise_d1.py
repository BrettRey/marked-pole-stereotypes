#!/usr/bin/env python3
"""Render results/d1/SUMMARY.md (and metrics CSVs) from the D1 fit files.

Metrics as specified in scripts/d1/README.md ("Reported per coefficient and
cell", "The table Brett decides from"). Every number comes from the CSVs.
Usage: .venv/bin/python scripts/d1/summarise_d1.py [fits.csv|pilot_fits.csv]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "results" / "d1"
CELL = ["scenario", "size", "indicator", "prior_scale", "model"]


def md(df: pd.DataFrame, index: bool = True) -> str:
    d = df.reset_index() if index else df
    cols = [" / ".join(map(str, c)) if isinstance(c, tuple) else str(c) for c in d.columns]
    fmt = lambda v: f"{v:.3f}" if isinstance(v, float) else str(v)  # noqa: E731
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(fmt(v) for v in row) + " |" for row in d.itertuples(index=False)]
    return "\n".join(lines)


def metrics(fits: pd.DataFrame) -> pd.DataFrame:
    f = fits.copy()
    f["indicator"] = f["indicator"].fillna("oracle")
    f["excl0"] = (f["q05"] > 0) | (f["q95"] < 0)
    f["width"] = f["q95"] - f["q05"]
    f["contraction"] = 1 - f["sd"] ** 2 / f["prior_sd"] ** 2
    # Two tiers (post-pilot 2, fixed before the grid): severe = R-hat > 1.05 or
    # more than 10 divergences (of 4,000 draws); mild = 1.01 < R-hat <= 1.05.
    f["severe"] = (f["rhat_max"] > 1.05) | (f["divergences"] > 10)
    f["flagged"] = f["severe"]
    f["mild"] = ~f["severe"] & ((f["rhat_max"] > 1.01) | (f["divergences"] > 0))
    has_t = f["truth"].notna()
    f["covered"] = np.where(has_t, (f["q05"] <= f["truth"]) & (f["truth"] <= f["q95"]), np.nan)
    f["err"] = f["mean"] - f["truth"]
    nz = has_t & (f["truth"] != 0)
    f["sign_err"] = np.where(nz & f["excl0"], np.sign(f["mean"]) != np.sign(f["truth"]), np.nan)
    f["exagg"] = np.where(nz & f["excl0"], (f["mean"] / f["truth"]).abs(), np.nan)
    f["false_excl"] = np.where(has_t & (f["truth"] == 0), f["excl0"], np.nan)
    g = f.groupby(CELL + ["coef"], dropna=False)
    out = g.agg(fits=("mean", "size"), truth=("truth", "first"), mean=("mean", "mean"),
                coverage=("covered", "mean"), bias=("err", "mean"), width=("width", "mean"),
                contraction=("contraction", "mean"), sign_error=("sign_err", "mean"),
                exaggeration=("exagg", "mean"), false_exclusion=("false_excl", "mean"),
                flagged=("flagged", "mean"), mild=("mild", "mean"), seconds=("seconds", "median")).reset_index()
    # prior sensitivity, f-only cells: paired by rep, shift in units of the prior-1 posterior SD
    fo = f[(f["indicator"] == "f_only")]
    p1 = fo[fo["prior_scale"] == 1.0].set_index(["scenario", "size", "rep", "coef"])
    p2 = fo[fo["prior_scale"] == 2.5].set_index(["scenario", "size", "rep", "coef"])
    shift = ((p2["mean"] - p1["mean"]).abs() / p1["sd"]).dropna()
    shift = shift.groupby(["scenario", "size", "coef"]).mean().rename("prior_shift").reset_index()
    shift["indicator"], shift["prior_scale"], shift["model"] = "f_only", 1.0, "joint"
    out = out.merge(shift, on=["scenario", "size", "coef", "indicator", "prior_scale", "model"], how="left")
    # scenario 3: agreement with the oracle (same dataset, true rho as data)
    s3 = f[f["scenario"] == "s3_mechanism"]
    orc = s3[s3["model"] == "oracle"].set_index(["size", "rep", "coef"])["mean"].rename("oracle_mean")
    j = s3[s3["model"] == "joint"].join(orc, on=["size", "rep", "coef"])
    j = j[j["oracle_mean"].notna()]
    j["oracle_sign_agree"] = np.sign(j["mean"]) == np.sign(j["oracle_mean"])
    j["oracle_in_interval"] = (j["q05"] <= j["oracle_mean"]) & (j["oracle_mean"] <= j["q95"])
    oa = j.groupby(CELL + ["coef"]).agg(oracle_mean=("oracle_mean", "mean"),
                                         oracle_sign_agree=("oracle_sign_agree", "mean"),
                                         oracle_in_interval=("oracle_in_interval", "mean")).reset_index()
    return out.merge(oa, on=CELL + ["coef"], how="left")


def identified(m: pd.DataFrame) -> pd.DataFrame:
    """README criteria: identified = contraction >= .5, coverage (or, for
    scenario-3 b_z, b_f and b_vt, oracle-in-interval) >= .8, and, for f-only, prior
    shift < .5 posterior SD. Not identified = contraction < .2. Otherwise weak."""
    j = m[(m["model"] == "joint") & (m["prior_scale"] == 1.0)].copy()

    def label(r):
        cov = r["coverage"] if pd.notna(r["coverage"]) else r.get("oracle_in_interval")
        if r["flagged"] > 0.5:  # post-pilot 2: most fits severely failed to converge
            return "not identified (no convergence)"
        if r["contraction"] < 0.2:
            return "not identified"
        ok = r["contraction"] >= 0.5 and pd.notna(cov) and cov >= 0.8
        if r["indicator"] == "f_only":
            ok = ok and pd.notna(r["prior_shift"]) and r["prior_shift"] < 0.5
        return "identified" if ok else "weak"

    j["status"] = j.apply(label, axis=1)
    return j.pivot_table(index=["scenario", "size", "indicator"], columns="coef", values="status", aggfunc="first")


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "fits.csv"
    fits = pd.read_csv(R / name)
    m = metrics(fits)
    stem = name.replace("_fits.csv", "").replace("fits.csv", "grid").rstrip("_")
    m.to_csv(R / f"metrics_{stem}.csv", index=False)
    ident = identified(m)
    ident.to_csv(R / f"identified_{stem}.csv")
    reps = fits.groupby(["scenario", "size", "model", "indicator", "prior_scale"], dropna=False)["rep"].nunique()
    out = [f"# D1 results ({stem})", "",
           "<!-- SUMMARY: Generated by scripts/d1/summarise_d1.py from results/d1 CSVs; do not edit by hand · status: generated -->", "",
           "Fake data only (scripts/d1/README.md). Never evidence about stereotypes.", "",
           f"Fits: {len(fits.drop_duplicates(['scenario', 'size', 'rep', 'model', 'indicator', 'prior_scale']))}; "
           f"reps per cell: {int(reps.min())}–{int(reps.max())}. "
           "With few reps, coverage and rates are coarse; the pilot exists to time fits and catch failures.", "",
           "## What each design can identify (prior scale 1)", "", md(ident), ""]
    s2 = m[(m["scenario"] == "s2_register") & (m["model"] == "joint") & (m["prior_scale"] == 1.0)
           & m["coef"].isin(["b_z", "b_m"])]
    out += ["## Scenario 2: false exclusion of zero for βz and βm (register confound)", "",
            md(s2.pivot_table(index=["size", "indicator"], columns="coef", values="false_exclusion")), "",
            "Posterior means:", "", md(s2.pivot_table(index=["size", "indicator"], columns="coef", values="mean")), ""]
    s3 = m[(m["scenario"] == "s3_mechanism") & (m["coef"].isin(["b_z", "b_m", "b_vt"]))]
    out += ["## Scenario 3: joint model against the oracle (true z as data)", "",
            md(s3.pivot_table(index=["size", "model", "indicator", "prior_scale"], columns="coef", values="mean")), "",
            "Oracle in the joint model's 90% interval (βz):", "",
            md(s3[s3["coef"] == "b_z"].pivot_table(index=["size", "indicator", "prior_scale"], values="oracle_in_interval")), ""]
    cols = ["fits", "truth", "mean", "coverage", "bias", "width", "contraction", "sign_error", "exaggeration",
            "false_exclusion", "prior_shift", "flagged", "mild", "seconds"]
    out += ["## All metrics", "", md(m.set_index(CELL + ["coef"])[cols]), ""]
    diag = fits.drop_duplicates(["scenario", "size", "rep", "model", "indicator", "prior_scale"])
    out += ["## Sampler diagnostics per fit", "",
            md(diag[["scenario", "size", "rep", "model", "indicator", "prior_scale", "rhat_max", "ess_min",
                     "divergences", "seconds"]], index=False), ""]
    (R / f"SUMMARY_{stem}.md").write_text("\n".join(out))
    print("wrote", (R / f"SUMMARY_{stem}.md").relative_to(ROOT))


if __name__ == "__main__":
    main()
