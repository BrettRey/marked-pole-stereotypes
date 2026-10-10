#!/usr/bin/env python3
"""Analytical illustrations for the threshold note, not fitted posteriors.

No research data, pilot estimates, or grid results are read. Every numerical
distribution, comparison magnitude and baseline probability is illustrative.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/d1c/mpl"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm, truncnorm

PREFIX = Path(__file__).with_suffix("")
CASES = [("A: lower centre", .4, .3, "#9a5100"),
         ("B: broad uncertainty", 1., .8, "#4d5aaa"),
         ("C: higher centre", 1.8, .4, "#007a69")]


def illustration(scale, probability_difference=False):
    records = []
    distributions = []
    for label, mean_multiple, sd_multiple, colour in CASES:
        mean, sd = mean_multiple*scale, sd_multiple*scale
        distribution = (truncnorm((-1-mean)/sd, (1-mean)/sd, loc=mean, scale=sd)
                        if probability_difference else norm(mean, sd))
        lower, upper = distribution.ppf([.05, .95])
        records.append(dict(label=label, location=mean, scale=sd,
                            interval90=[lower, upper],
                            comparison_magnitudes=[.5*scale, scale, 2*scale],
                            probabilities=distribution.sf([.5*scale, scale, 2*scale]).tolist()))
        assert abs(distribution.cdf(lower)-.05) < 1e-10
        assert abs(distribution.sf(upper)-.05) < 1e-10
        distributions.append((label, distribution, colour))
    return records, distributions


def plot(name, title, scale, probability_difference=False):
    records, distributions = illustration(scale, probability_difference)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), layout="constrained")
    x = np.linspace(-1.5*scale, 3.5*scale, 600)
    thresholds = np.linspace(0, 3*scale, 400)
    for label, distribution, colour in distributions:
        axes[0].plot(x, distribution.pdf(x), color=colour, label=label[0], lw=2)
        axes[1].plot(thresholds, distribution.sf(thresholds), color=colour, label=label[0], lw=2)
    for axis in axes:
        for threshold in [.5*scale, scale, 2*scale]:
            axis.axvline(threshold, color="#888888", ls=":", lw=.8)
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", color="#eeeeee")
    axes[0].set(xlabel="Signed effect (positive = predicted direction)", ylabel="Density",
                title="Constructed posterior shapes")
    axes[0].legend(frameon=False, title="Illustration")
    axes[1].set(xlabel="Effect size T", ylabel="P(signed effect > T)",
                ylim=(-.02, 1.02), title="Exceedance curves")
    fig.suptitle(title + "\nIllustrative distributions only; no fitted data", fontsize=13)
    path = PREFIX.with_name(PREFIX.name + f"-{name}.png")
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return dict(figure=str(path.relative_to(ROOT)), records=records,
                distribution="normal truncated to [-1,1]" if probability_difference else "normal")


def main():
    figures = {
        "log_probability_ratio": plot("log", "Log probability ratios: H2 and proposed H1 display", .1),
        "l1_probability_difference": plot("l1", "L1 protocol contrast: probability difference", .1, True),
        "word_probability_difference": plot("word", "Word-level negation contrast: probability difference", .02, True),
    }
    probability_examples = [dict(
        effect_size=threshold, baseline=baseline,
        h2_probability=baseline*np.exp(-threshold),
        h1_probability=baseline*np.exp(threshold),
        baseline_selections_per_10000=10000*baseline,
        h2_selections_per_10000=10000*baseline*np.exp(-threshold),
        baseline_at_least_once_in_six_independent_draws=1-(1-baseline)**6,
        conditional_coefficient_probability=(baseline*np.exp(-threshold)
                                             / (1-baseline+baseline*np.exp(-threshold))))
        for threshold in [.05, .10, .20] for baseline in [.001, .005, .01]]
    log = dict(
        label="ILLUSTRATIVE: analyst-chosen distributions, comparison magnitudes and baselines; no fitted posteriors",
        created_at=datetime.now(timezone.utc).isoformat(),
        method="Analytical normal CDF/quantiles; bounded probability differences use truncation to [-1,1]",
        seed=None, seed_note="No random sampling",
        python=sys.version,
        packages={name: version(name) for name in ("numpy", "scipy", "matplotlib")},
        source_hashes={path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in
                       ("analysis_plan.md", "DECISIONS.md", "scripts/d1c/README.md",
                        "scripts/d2/README.md", "reviews/codex-thresholds-2026-10-09/output.md")},
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        figures=figures, probability_examples=probability_examples)
    PREFIX.with_suffix(".json").write_text(json.dumps(log, indent=2))
    (ROOT / "logs/d1c-threshold-illustrations-20261010.json").write_text(json.dumps(log, indent=2))
    print(json.dumps({key: value["records"] for key, value in figures.items()}, indent=2))


if __name__ == "__main__":
    main()
