"""Uncertainty across independent simulated datasets, not posterior draws."""
import math

import numpy as np
from scipy.stats import beta

NULL_TOLERANCE = 1e-8  # D1c's numerical root solve can leave near-zero truths.


def rate(events):
    events = np.asarray(events, dtype=bool)
    n, k = len(events), int(events.sum())
    if not n:
        return dict(n=0, events=0, estimate=None, mcse=None, lo95=None, hi95=None)
    p = k / n
    return dict(n=n, events=k, estimate=p,
                mcse=math.sqrt(p*(1-p)/n) if n > 1 and 0 < k < n else None,
                lo95=0. if k == 0 else float(beta.ppf(.025, k, n-k+1)),
                hi95=1. if k == n else float(beta.ppf(.975, k+1, n-k)),
                interval="Clopper–Pearson 95%; plug-in MCSE suppressed at observed boundaries")


def continuous(values, *, statistic="mean", bootstrap=2000, seed=20261010):
    values = np.asarray(values, dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Nonfinite performance value")
    functions = {"mean": np.mean, "median": np.median,
                 "q10": lambda x, axis=None: np.quantile(x, .1, axis=axis),
                 "q90": lambda x, axis=None: np.quantile(x, .9, axis=axis),
                 "rmse": lambda x, axis=None: np.sqrt(np.mean(x*x, axis=axis))}
    function = functions[statistic]
    n = len(values)
    if not n:
        return dict(n=0, estimate=None, mcse=None)
    estimate, mcse = float(function(values)), None
    if n > 1:
        if statistic == "mean":
            mcse = float(values.std(ddof=1)/math.sqrt(n))
        else:
            rng = np.random.default_rng(seed)
            # Bound temporary memory when there are many independent datasets.
            resampled = []
            for start in range(0, bootstrap, 100):
                sample = rng.choice(values, size=(min(100, bootstrap-start), n))
                resampled.extend(function(sample, axis=1))
            mcse = float(np.std(resampled, ddof=1))
    return dict(n=n, estimate=estimate, mcse=mcse,
                uncertainty="Across datasets; analytic mean SE or fixed-seed bootstrap SE",
                bootstrap_repetitions=0 if statistic == "mean" or n < 2 else bootstrap)


def performance(rows, attempts):
    """Rows contain one whole-fit result per generated dataset and estimand."""
    usable = [r for r in rows if r["good"]]
    nonnull = [r for r in usable if abs(r["truth"]) > NULL_TOLERANCE]
    null = [r for r in usable if abs(r["truth"]) <= NULL_TOLERANCE]
    selected = [r for r in nonnull if excludes_zero(r)]
    correct = [correct_direction(r) for r in nonnull]
    result = dict(attempted_datasets=attempts, completed_fits=len(rows),
                  converged_fits=len(usable), diagnostic_failures=len(rows)-len(usable),
                  execution_failures=attempts-len(rows),
                  truth_range=[min(r["truth"] for r in rows), max(r["truth"] for r in rows)] if rows else None,
                  metrics_population="Converged fits unless explicitly per_attempted_dataset",
                  successful_fit_rate=rate([True]*len(usable)+[False]*(attempts-len(usable))))
    if attempts < len(rows):
        raise ValueError("More completed rows than attempted datasets")
    metrics = dict(bias=continuous([r["mean"]-r["truth"] for r in usable]),
        rmse=continuous([r["mean"]-r["truth"] for r in usable], statistic="rmse"),
        wrong_sign=rate([r["mean"]*r["truth"] < 0 for r in nonnull]),
        selected_wrong_sign=rate([r["mean"]*r["truth"] < 0 for r in selected]),
        selected_exaggeration=continuous([abs(r["mean"]/r["truth"]) for r in selected]),
        correct_direction_detection=rate(correct),
        false_exclusion_at_null=rate([excludes_zero(r) for r in null]),
        usable_correct_detection_per_attempted_dataset=rate(
            [True]*sum(correct)+[False]*(attempts-sum(correct))))
    for level in (50, 90):
        lo, hi = f"lo{level}", f"hi{level}"
        metrics[f"coverage{level}"] = rate([r[lo] <= r["truth"] <= r[hi] for r in usable])
        widths = [r[hi]-r[lo] for r in usable]
        for name in ("mean", "median", "q10", "q90"):
            metrics[f"width{level}_{name}"] = continuous(widths, statistic=name)
    result["metrics"] = metrics
    return result


def excludes_zero(row):
    return row["lo90"] > 0 or row["hi90"] < 0


def correct_direction(row):
    if abs(row["truth"]) <= NULL_TOLERANCE:
        return False
    return row["lo90"] > 0 if row["truth"] > 0 else row["hi90"] < 0
