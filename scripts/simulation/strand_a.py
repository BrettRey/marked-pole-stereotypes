#!/usr/bin/env python3
"""Strand A: the UWA (2026) stereotype-negativity simulation, rebuilt from the
published design, with the extensions specified in scripts/simulation/README.md.

The spec in README.md was written before this code ran; read it first.

Usage: python3 scripts/simulation/strand_a.py <replicate|replicate_seeds|ties|fresh|diversity|groupsize|consensus|consensus_check|consensus_equal_shift|all>
"""
from __future__ import annotations

import argparse
import itertools
import json
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import hypergeom

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "strandA"
LOGS = ROOT / "logs"
ROOT_SEED = 20261007

BASE_RATE_PAIRS = [(0.5, 0.5), (0.6, 0.4), (0.7, 0.3), (0.8, 0.2), (0.9, 0.1)]
EXPERIMENT_IDS = {"replicate": 1, "ties": 2, "fresh": 3, "diversity": 4,
                  "groupsize": 5, "consensus": 6, "consensus_check": 7,
                  "replicate_seeds": 8, "consensus_equal_shift": 9}


# ---------------------------------------------------------------- helpers

def rng_for(experiment: str, *cond: int) -> np.random.Generator:
    """A generator whose seed depends only on the experiment and condition
    index, so results don't change when experiments run in another order."""
    ss = np.random.SeedSequence(ROOT_SEED, spawn_key=(EXPERIMENT_IDS[experiment], *cond))
    return np.random.default_rng(ss)


def seed_record(experiment: str, *cond: int) -> dict:
    return {"root": ROOT_SEED, "spawn_key": [EXPERIMENT_IDS[experiment], *cond]}


def group_sizes(n_target: int, total: int = 1000, k: int = 10) -> np.ndarray:
    """Target first; the rest split as evenly as integers allow."""
    rest = total - n_target
    base, extra = divmod(rest, k - 1)
    others = [base + (1 if i < extra else 0) for i in range(k - 1)]
    return np.array([n_target, *others])


def attribute_rates(n_pos: int, n_neg: int, pi_pos: float, pi_neg: float):
    """Positives first, then negatives. Returns (pi per attribute, is_neg)."""
    pis = np.concatenate([np.full(n_pos, pi_pos), np.full(n_neg, pi_neg)])
    is_neg = np.concatenate([np.zeros(n_pos, bool), np.ones(n_neg, bool)])
    return pis, is_neg


def draw_counts(rng, sizes: np.ndarray, theta: np.ndarray, reps: int) -> np.ndarray:
    """Counts of members with each attribute, shape (reps, K, A).
    theta is (A,) for no group differences or (K, A) otherwise.
    Equivalent to drawing individuals because attributes are independent
    of group and of each other (README, 'Counts, not individuals')."""
    th = np.broadcast_to(theta, (len(sizes), theta.shape[-1]))
    return rng.binomial(sizes[None, :, None], th[None, :, :], size=(reps, len(sizes), th.shape[-1]))


def target_stats(counts: np.ndarray, sizes: np.ndarray):
    """a, b, PPV, p(A|G1), LR1, LR2 for the target group (index 0)."""
    n1 = sizes[0]
    n0 = sizes.sum() - n1
    a = counts[:, 0, :].astype(float)
    b = counts[:, 1:, :].sum(axis=1).astype(float)
    tot = a + b
    with np.errstate(invalid="ignore", divide="ignore"):
        ppv = np.where(tot > 0, a / tot, np.nan)
    p_a_g1 = a / n1
    lr1 = ((a + 0.5) / (n1 + 1)) / ((b + 0.5) / (n0 + 1))
    lr2 = ((a + 0.5) / (tot + 1)) / (n1 / (n1 + n0))
    return a, b, ppv, p_a_g1, lr1, lr2


def rank_order(ppv: np.ndarray, rng, ties: str = "random") -> np.ndarray:
    """Attribute indices by descending PPV, per row. NaN PPVs go last.
    ties: 'random', 'pos_first' (lower index wins) or 'neg_first'."""
    key = np.where(np.isnan(ppv), -np.inf, ppv)
    reps, n_attr = key.shape
    if ties == "random":
        tiebreak = rng.random((reps, n_attr))
    elif ties == "pos_first":
        tiebreak = np.broadcast_to(np.arange(n_attr), (reps, n_attr))
    elif ties == "neg_first":
        tiebreak = np.broadcast_to(-np.arange(n_attr), (reps, n_attr))
    else:
        raise ValueError(ties)
    # lexsort: last key is primary
    return np.lexsort((tiebreak, -key), axis=1)


def take(x: np.ndarray, idx: np.ndarray) -> np.ndarray:
    return np.take_along_axis(x, idx, axis=1)


def summarise(rows: list[dict], name: str, values: np.ndarray, **cond):
    """Append mean and Monte Carlo SE of per-run values."""
    v = np.asarray(values, float)
    v = v[~np.isnan(v)]
    rows.append({**cond, "metric": name, "mean": v.mean(),
                 "mc_se": v.std(ddof=1) / np.sqrt(len(v)), "runs": len(v)})


def run_core(rng, sizes, pis, is_neg, reps, ties="random", fresh=False):
    """UWA's three outcomes (plus both LR definitions) for one condition.
    Returns a dict of per-run arrays."""
    counts = draw_counts(rng, sizes, pis, reps)
    a, b, ppv, p_a_g1, lr1, lr2 = target_stats(counts, sizes)
    order = rank_order(ppv, rng, ties)
    top5 = order[:, :5]
    out = {
        "share_negative_top5": is_neg[top5].mean(axis=1),
        "mean_p_A_given_G1_top5": take(p_a_g1, top5).mean(axis=1),
        "mean_pi_top5": pis[top5].mean(axis=1),
    }
    # within-valence ranks for the LR panel
    for label, mask in (("pos", ~is_neg), ("neg", is_neg)):
        idx = np.flatnonzero(mask)
        sub_order = rank_order(ppv[:, idx], rng, ties)[:, :5]
        chosen = idx[sub_order]
        for r in range(5):
            out[f"LR1_{label}_rank{r + 1}"] = take(lr1, chosen[:, [r]])[:, 0]
            out[f"LR2_{label}_rank{r + 1}"] = take(lr2, chosen[:, [r]])[:, 0]
    if fresh:
        counts2 = draw_counts(rng, sizes, pis, reps)
        _, _, ppv2, pag2, lr1_2, _ = target_stats(counts2, sizes)
        out["fresh_ppv_top5"] = np.nanmean(take(ppv2, top5), axis=1)
        out["fresh_p_A_given_G1_top5"] = take(pag2, top5).mean(axis=1)
        out["fresh_LR1_top5"] = take(lr1_2, top5).mean(axis=1)
        out["original_ppv_top5"] = take(ppv, top5).mean(axis=1)
    return out


def write(df: pd.DataFrame, name: str) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / name
    df.to_csv(path, index=False)
    return path


# ---------------------------------------------------------------- experiments

def exp_replicate(reps=1000, ties="random", experiment="replicate"):
    rows, seeds = [], []
    sizes = np.full(10, 100)
    for i, (pp, pn) in enumerate(BASE_RATE_PAIRS):
        pis, is_neg = attribute_rates(50, 50, pp, pn)
        out = run_core(rng_for(experiment, i), sizes, pis, is_neg, reps, ties=ties)
        seeds.append(seed_record(experiment, i))
        for k, v in out.items():
            summarise(rows, k, v, pi_pos=pp, pi_neg=pn, ties=ties)
    return pd.DataFrame(rows), seeds


def exp_ties(reps=1000):
    """Same seeds as 'replicate', so only the tie rule differs. (The first
    version gave the variants their own seeds, which confounded tie-breaking
    with Monte Carlo variation; fixed after the first run.)"""
    frames, seeds = [], []
    for j, mode in enumerate(("pos_first", "neg_first")):
        df, s = exp_replicate(reps, ties=mode, experiment="replicate")
        frames.append(df)
        seeds += s
    return pd.concat(frames), seeds


def exp_replicate_seeds(reps=1000, n_seeds=50):
    """Across-seed spread of the replication's outcomes, so the pre-committed
    seed's values can be read against Monte Carlo variation between seeds."""
    rows, seeds = [], []
    sizes = np.full(10, 100)
    for i, (pp, pn) in enumerate(BASE_RATE_PAIRS):
        pis, is_neg = attribute_rates(50, 50, pp, pn)
        per_seed = []
        for k in range(n_seeds):
            out = run_core(rng_for("replicate_seeds", i, k), sizes, pis, is_neg, reps)
            per_seed.append({m: v.mean() for m, v in out.items()})
            seeds.append(seed_record("replicate_seeds", i, k))
        ps = pd.DataFrame(per_seed)
        for m in ps.columns:
            rows.append({"pi_pos": pp, "pi_neg": pn, "metric": m, "mean_across_seeds": ps[m].mean(),
                         "sd_across_seeds": ps[m].std(ddof=1), "min": ps[m].min(), "max": ps[m].max(),
                         "n_seeds": n_seeds, "runs_per_seed": reps})
    return pd.DataFrame(rows), seeds


def exp_fresh(reps=1000):
    rows, seeds = [], []
    sizes = np.full(10, 100)
    for i, (pp, pn) in enumerate(BASE_RATE_PAIRS):
        pis, is_neg = attribute_rates(50, 50, pp, pn)
        out = run_core(rng_for("fresh", i), sizes, pis, is_neg, reps, fresh=True)
        seeds.append(seed_record("fresh", i))
        for k in ("original_ppv_top5", "fresh_ppv_top5", "mean_p_A_given_G1_top5",
                  "fresh_p_A_given_G1_top5", "mean_pi_top5", "fresh_LR1_top5"):
            summarise(rows, k, out[k], pi_pos=pp, pi_neg=pn, p_G1=0.1)
    return pd.DataFrame(rows), seeds


def exp_diversity(reps=1000):
    rows, seeds = [], []
    sizes = np.full(10, 100)
    for i, (pp, pn) in enumerate(BASE_RATE_PAIRS):
        pis, is_neg = attribute_rates(50, 100, pp, pn)
        out = run_core(rng_for("diversity", i), sizes, pis, is_neg, reps, fresh=True)
        seeds.append(seed_record("diversity", i))
        for k, v in out.items():
            summarise(rows, k, v, pi_pos=pp, pi_neg=pn, n_pos=50, n_neg=100)
    return pd.DataFrame(rows), seeds


def exp_groupsize(reps=1000):
    rows, seeds = [], []
    for j, n1 in enumerate((20, 50, 100, 200, 300, 500)):
        sizes = group_sizes(n1)
        for i, (pp, pn) in enumerate(BASE_RATE_PAIRS):
            pis, is_neg = attribute_rates(50, 50, pp, pn)
            out = run_core(rng_for("groupsize", j, i), sizes, pis, is_neg, reps, fresh=True)
            seeds.append(seed_record("groupsize", j, i))
            for k, v in out.items():
                summarise(rows, k, v, n_target=n1, p_G1=n1 / sizes.sum(),
                          pi_pos=pp, pi_neg=pn)
    return pd.DataFrame(rows), seeds


def chance_jaccard(n_attr=100, top=5) -> float:
    """Expected Jaccard of two independent random top-k sets."""
    rv = hypergeom(n_attr, top, top)
    x = np.arange(0, top + 1)
    return float(np.sum(rv.pmf(x) * x / (2 * top - x)))


def ppv_from_counts(counts: np.ndarray) -> np.ndarray:
    """PPV for the target group from counts shaped (..., K, A)."""
    a = counts[..., 0, :].astype(float)
    b = counts[..., 1:, :].sum(axis=-2).astype(float)
    tot = a + b
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(tot > 0, a / tot, np.nan)


def top5_sets(ppv: np.ndarray, rng) -> np.ndarray:
    """Top-5 attribute indices for PPVs shaped (..., A)."""
    lead, n_attr = ppv.shape[:-1], ppv.shape[-1]
    flat = ppv.reshape(-1, n_attr)
    return rank_order(flat, rng)[:, :5].reshape(*lead, 5)


def indicator(sets: np.ndarray, n_attr: int) -> np.ndarray:
    ind = np.zeros((*sets.shape[:-1], n_attr), np.int16)
    np.put_along_axis(ind, sets, 1, axis=-1)
    return ind


def consensus_world_rates(rng, pis, is_neg, worlds, delta, val, k_diff):
    """theta (worlds, K, A) and the differing attributes (worlds, k_diff)."""
    n_attr = len(pis)
    pool = {"negative": np.flatnonzero(is_neg), "positive": np.flatnonzero(~is_neg)}.get(
        val, np.arange(n_attr))
    diff = np.stack([rng.choice(pool, k_diff, replace=False) for _ in range(worlds)])
    theta = np.broadcast_to(pis, (worlds, 10, n_attr)).copy()
    if delta > 0:
        logit = np.log(pis / (1 - pis))
        shifted = 1 / (1 + np.exp(-(logit + delta)))
        theta[np.repeat(np.arange(worlds), k_diff), 0, diff.ravel()] = shifted[diff.ravel()]
    return theta, diff


def exp_consensus(worlds=300, perceivers=20, k_diff=5):
    """Two versions (README): 'independent' perceivers sample straight from
    the world's rates; 'shared' perceivers sample from one finite society of
    M members per group, without replacement."""
    rows, seeds = [], []
    deltas = (0.0, 0.25, 0.5, 1.0, 2.0)
    diff_valences = ("negative", "positive", "mixed")
    n_per_group = (10, 30, 100)
    versions = [("independent", None), ("shared", 100), ("shared", 1000)]
    iu = np.triu_indices(perceivers, 1)
    cond_list = []
    for (s, (version, m_soc)), (i, (pp, pn)), (j, n) in itertools.product(
            enumerate(versions), enumerate(BASE_RATE_PAIRS), enumerate(n_per_group)):
        if m_soc is not None and n > m_soc:
            continue
        cond_list.append((s, version, m_soc, i, pp, pn, j, n, 0, 0.0, "none"))
        for (d, delta), (v, val) in itertools.product(enumerate(deltas[1:], 1), enumerate(diff_valences)):
            cond_list.append((s, version, m_soc, i, pp, pn, j, n, d * 10 + v, delta, val))
    for s, version, m_soc, i, pp, pn, j, n, c, delta, val in cond_list:
        rng = rng_for("consensus", s, i, j, c)
        seeds.append(seed_record("consensus", s, i, j, c))
        pis, is_neg = attribute_rates(50, 50, pp, pn)
        n_attr = len(pis)
        theta, diff = consensus_world_rates(rng, pis, is_neg, worlds, delta, val, k_diff)
        shape = (worlds, perceivers, 10, n_attr)
        if version == "independent":
            counts = rng.binomial(n, theta[:, None, :, :], size=shape)
        else:
            society = rng.binomial(m_soc, theta)  # (worlds, K, A) realized counts
            counts = rng.hypergeometric(society[:, None, :, :], m_soc - society[:, None, :, :],
                                        n, size=shape)
            soc_top5 = top5_sets(ppv_from_counts(society), rng)  # (worlds, 5)
        top5 = top5_sets(ppv_from_counts(counts), rng)  # (worlds, P, 5)
        ind = indicator(top5, n_attr)
        inter = np.einsum("wpa,wqa->wpq", ind, ind)
        jac = (inter / (10 - inter))[:, iu[0], iu[1]].mean(axis=1)
        share_neg = is_neg[top5].mean(axis=2)
        is_diff = indicator(diff, n_attr).astype(bool)
        hit = np.take_along_axis(np.repeat(is_diff[:, None, :], perceivers, 1), top5, axis=2).mean(axis=2)
        cond = dict(version=version, society_M=m_soc if m_soc else np.nan, pi_pos=pp, pi_neg=pn,
                    n_per_group=n, delta=delta, diff_valence=val, k_diff=k_diff if delta > 0 else 0)
        summarise(rows, "jaccard_mean_pairwise", jac, **cond)
        summarise(rows, "share_negative_mean", share_neg.mean(axis=1), **cond)
        summarise(rows, "share_negative_sd_across_perceivers", share_neg.std(axis=1, ddof=1), **cond)
        summarise(rows, "prop_perceivers_majority_negative", (share_neg >= 0.6).mean(axis=1), **cond)
        if delta > 0:
            summarise(rows, "hit_rate_true_differences", hit.mean(axis=1), **cond)
        if version == "shared":
            soc_ind = indicator(soc_top5, n_attr)
            inter_soc = np.einsum("wpa,wa->wp", ind, soc_ind)
            summarise(rows, "jaccard_with_society_top5", (inter_soc / (10 - inter_soc)).mean(axis=1), **cond)
            summarise(rows, "society_share_negative_top5", is_neg[soc_top5].mean(axis=1), **cond)
    df = pd.DataFrame(rows)
    df["chance_jaccard"] = chance_jaccard()
    return df, seeds


def exp_consensus_equal_shift(worlds=300, perceivers=20, n=100, k_diff=5, pp=0.7, pn=0.3):
    """POST HOC, exploratory (added after the consensus run): the main design
    shifts the target group on the logit scale, which moves rates near .3 more
    on the probability scale than rates near .7. Here the shift is an equal
    absolute amount for both valences, to check that the valence asymmetry
    in content agreement isn't a scale artefact. Independent version only."""
    rows, seeds = [], []
    pis, is_neg = attribute_rates(50, 50, pp, pn)
    n_attr = len(pis)
    iu = np.triu_indices(perceivers, 1)
    for (d, dp), (v, val) in itertools.product(enumerate((0.05, 0.10, 0.15, 0.20)),
                                             enumerate(("negative", "positive"))):
        rng = rng_for("consensus_equal_shift", d, v)
        seeds.append(seed_record("consensus_equal_shift", d, v))
        pool = np.flatnonzero(is_neg) if val == "negative" else np.flatnonzero(~is_neg)
        diff = np.stack([rng.choice(pool, k_diff, replace=False) for _ in range(worlds)])
        theta = np.broadcast_to(pis, (worlds, 10, n_attr)).copy()
        theta[np.repeat(np.arange(worlds), k_diff), 0, diff.ravel()] += dp
        counts = rng.binomial(n, theta[:, None], size=(worlds, perceivers, 10, n_attr))
        top5 = top5_sets(ppv_from_counts(counts), rng)
        ind = indicator(top5, n_attr)
        inter = np.einsum("wpa,wqa->wpq", ind, ind)
        jac = (inter / (10 - inter))[:, iu[0], iu[1]].mean(axis=1)
        is_diff = indicator(diff, n_attr).astype(bool)
        hit = np.take_along_axis(np.repeat(is_diff[:, None, :], perceivers, 1), top5, axis=2).mean(axis=2)
        cond = dict(version="independent", pi_pos=pp, pi_neg=pn, n_per_group=n,
                    abs_shift=dp, diff_valence=val, k_diff=k_diff, post_hoc=True)
        summarise(rows, "jaccard_mean_pairwise", jac, **cond)
        summarise(rows, "hit_rate_true_differences", hit.mean(axis=1), **cond)
    return pd.DataFrame(rows), seeds


def exp_consensus_exact_check(worlds=100, perceivers=20, m_soc=1000, n=30, pp=0.7, pn=0.3):
    """Exact individual-level shared society for one cell (delta = 0), to check
    the per-attribute hypergeometric approximation used in exp_consensus."""
    rng = rng_for("consensus_check", 0)
    pis, is_neg = attribute_rates(50, 50, pp, pn)
    n_attr = len(pis)
    iu = np.triu_indices(perceivers, 1)
    jac_exact, jac_approx = [], []
    for _ in range(worlds):
        society = rng.random((10, m_soc, n_attr)) < pis  # individuals
        soc_counts = society.sum(axis=1)
        exact = np.stack([
            np.stack([society[g, rng.choice(m_soc, n, replace=False)].sum(axis=0) for g in range(10)])
            for _ in range(perceivers)])  # (P, K, A)
        approx = rng.hypergeometric(soc_counts[None], m_soc - soc_counts[None], n,
                                    size=(perceivers, 10, n_attr))
        for counts, store in ((exact, jac_exact), (approx, jac_approx)):
            ind = indicator(top5_sets(ppv_from_counts(counts), rng), n_attr)
            inter = ind @ ind.T
            store.append((inter / (10 - inter))[iu].mean())
    rows = []
    for name, v in (("exact_individual_level", jac_exact), ("hypergeometric_approx", jac_approx)):
        summarise(rows, "jaccard_mean_pairwise", np.array(v), method=name, society_M=m_soc,
                  n_per_group=n, pi_pos=pp, pi_neg=pn, delta=0.0)
    return pd.DataFrame(rows), [seed_record("consensus_check", 0)]


# ---------------------------------------------------------------- checks

def check_against_paper(rep: pd.DataFrame) -> pd.DataFrame:
    """Text anchors T1-T5 (primary) and Figure 6 by-eye values (secondary)."""
    m = rep.set_index(["pi_neg", "metric"])["mean"]
    se = rep.set_index(["pi_neg", "metric"])["mc_se"]
    pn = sorted(rep["pi_neg"].unique())
    sh = [m[(p, "share_negative_top5")] for p in pn]
    pa = {p: m[(p, "mean_p_A_given_G1_top5")] for p in pn}
    pos_lr = [np.mean([m[(p, f"LR1_pos_rank{r}")] for r in range(1, 6)]) for p in pn]
    rows = [
        # Weak monotonicity: amended after the first run, where the share was
        # 1.000 at both .10 and .20 (a ceiling) and a strict check failed.
        {"check": "T1 share negative never falls as pi_neg falls; >= .95 at .10",
         "value": "; ".join(f"{p}: {v:.3f}" for p, v in zip(pn, sh)),
         "pass": bool(all(np.diff(sh) <= 1e-9) and m[(0.1, "share_negative_top5")] >= 0.95)},
        {"check": "T2 share negative ~ .50 at .50/.50",
         "value": f"{m[(0.5, 'share_negative_top5')]:.3f} (MC SE {se[(0.5, 'share_negative_top5')]:.3f})",
         "pass": bool(abs(m[(0.5, "share_negative_top5")] - 0.5) < 3 * se[(0.5, "share_negative_top5")] + 0.01)},
        {"check": "T3 mean LR1 of top-5 positives close to 1, changes modestly",
         "value": "; ".join(f"{p}: {v:.3f}" for p, v in zip(pn, pos_lr)),
         "pass": bool(max(pos_lr) < 1.3)},
        {"check": "T4 mean p(A|G1) about .60 at .50/.50",
         "value": f"{pa[0.5]:.3f}", "pass": bool(abs(pa[0.5] - 0.60) < 0.03)},
        {"check": "T5 mean p(A|G1) < .50 at pi_neg .30, > .50 at .40",
         "value": f".30: {pa[0.3]:.3f}; .40: {pa[0.4]:.3f}",
         "pass": bool(pa[0.3] < 0.5 < pa[0.4])},
    ]
    fig = pd.read_csv(RESULTS / "figure6_read_by_eye.csv", comment="#")
    for _, r in fig.iterrows():
        series = r["series"]
        tol = 0.08 if series.startswith("LR") else 0.05
        for lrdef in (("LR1", "LR2") if series.startswith("LR") else ("",)):
            metric = series.replace("LR", lrdef, 1) if lrdef else series
            sim = m[(r["pi_neg"], metric)]
            rows.append({"check": f"Fig6 {metric} at pi_neg {r['pi_neg']}",
                         "value": f"sim {sim:.3f} vs read {r['value']:.2f}",
                         "pass": bool(abs(sim - r["value"]) <= tol)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- logging

def run_log(experiments, seeds, outputs, elapsed):
    LOGS.mkdir(exist_ok=True)
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                    capture_output=True, text=True).stdout.strip())
    except Exception:  # noqa: BLE001
        sha, dirty = None, None
    import scipy
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "script": "scripts/simulation/strand_a.py",
        "experiments": experiments,
        "argv": sys.argv,
        "git_sha": sha, "git_dirty": dirty,
        "python": sys.version, "platform": platform.platform(),
        "packages": {"numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__},
        "seeds": seeds,
        "outputs": [str(p.relative_to(ROOT)) for p in outputs],
        "elapsed_seconds": round(elapsed, 1),
    }
    path = LOGS / f"strandA-{stamp}.json"
    path.write_text(json.dumps(log, indent=2))
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("experiment", choices=[*EXPERIMENT_IDS, "all"])
    args = ap.parse_args()
    todo = list(EXPERIMENT_IDS) if args.experiment == "all" else [args.experiment]
    t0, seeds, outputs = time.time(), {}, []
    for e in todo:
        df, s = {"replicate": exp_replicate, "ties": exp_ties, "fresh": exp_fresh,
                 "diversity": exp_diversity, "groupsize": exp_groupsize,
                 "consensus": exp_consensus,
                 "consensus_check": exp_consensus_exact_check,
                 "replicate_seeds": exp_replicate_seeds,
                 "consensus_equal_shift": exp_consensus_equal_shift}[e]()
        seeds[e] = s
        outputs.append(write(df, f"{e}.csv"))
        if e == "replicate":
            chk = check_against_paper(df)
            outputs.append(write(chk, "check_against_paper.csv"))
            print(chk.to_string(index=False))
        print(f"{e}: done ({time.time() - t0:.1f}s)")
    print("log:", run_log(todo, seeds, outputs, time.time() - t0).relative_to(ROOT))


if __name__ == "__main__":
    main()
