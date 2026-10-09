#!/usr/bin/env python3
"""D2: fake-data check of the lexical models L1 and L2 (fake data only; never evidence).

Spec: scripts/d2/README.md (v2), committed before this ran.

Run in the project venv, e.g.
    .venv/bin/python scripts/d2/d2.py truths
    .venv/bin/python scripts/d2/d2.py pilot
    .venv/bin/python scripts/d2/d2.py run --part l1 --reps 60 --reps-a 100 --workers 3
    .venv/bin/python scripts/d2/d2.py run --part l2 --reps 40 --workers 3
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# pytensor appends "-ld64" on macOS >= 15; D1's wrapper drops it (scripts/d1/README.md).
if sys.platform == "darwin":
    os.environ.setdefault("PYTENSOR_FLAGS", f"cxx={ROOT / 'scripts' / 'd1' / 'bin' / 'clang++'}")

import argparse  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402
from concurrent.futures import ProcessPoolExecutor, as_completed  # noqa: E402
from datetime import datetime  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.optimize import brentq  # noqa: E402
from scipy.special import expit, softmax  # noqa: E402

RESULTS = ROOT / "results" / "d2"
LOGS = ROOT / "logs"
ROOT_SEED = 20261009
BIG = 400_000  # population size for truths (README: "Truth")

# ------------------------------------------------------------------ cells (README, "Grid")

L1_BASE = dict(N=80, s_off=0.2, beta=0.0, delta=0.0, confound=False, selection=False, rootavail=False,
               orient_mu=1.5, shared=False, cs_mnar=False, floor=False, coder_s=0.6, avail=0.0, delta_m=None)
L1_DESIGNS_ALL = ("a", "b10", "b30", "c")


def l1_cells() -> list[dict]:
    cells = []
    for N in (40, 80, 160):
        for s_off in (0.1, 0.2, 0.3):
            for beta in (0.0, 1.0):
                cells.append(dict(L1_BASE, N=N, s_off=s_off, beta=beta, kind="core", designs=L1_DESIGNS_ALL))
    for s_off in (0.1, 0.2, 0.3):
        cells.append(dict(L1_BASE, N=80, s_off=s_off, beta=0.5, kind="core", designs=L1_DESIGNS_ALL))
    stress = [("delta+", dict(delta=0.4)), ("delta-", dict(delta=-0.4)), ("selection", dict(selection=True)),
              ("rootavail", dict(rootavail=True)), ("orient", dict(orient_mu=0.8)), ("shared", dict(shared=True)),
              ("cs_mnar", dict(cs_mnar=True)), ("floor", dict(floor=True)), ("coder.4", dict(coder_s=0.4)),
              ("coder.9", dict(coder_s=0.9))]
    for name, kw in stress:
        for beta in (0.0, 1.0):
            designs = ("a", "b10", "b30") if name in ("coder.4", "coder.9", "cs_mnar") else L1_DESIGNS_ALL
            cells.append(dict(L1_BASE, beta=beta, kind=name, designs=designs, **kw))
    cells.append(dict(L1_BASE, beta=0.0, kind="confound", confound=True, designs=L1_DESIGNS_ALL))
    for beta in (0.0, 1.0):
        cells.append(dict(L1_BASE, beta=beta, kind="avail", avail=0.3, designs=("c",)))
    for dm in (-0.4, 0.0, 0.4):
        for beta in (0.0, 1.0):
            cells.append(dict(L1_BASE, beta=beta, kind=f"word{dm:+.1f}", delta_m=dm, designs=("word",)))
    for i, c in enumerate(cells):
        c["cell"] = f"L1-{i:02d}"
    return cells


L2_BASE = dict(K=300, rho_zs=-0.5, beta_z=0.0, story="A", indicator="desc", delta=0.0, wordcoded=False,
               register=False, floor=False, R_assumed=0.36, naive=False, non_share=0.02)


def l2_cells() -> list[dict]:
    cells = []
    for rho in (0.0, -0.5, -0.8):
        for bz in (0.0, -0.4):
            for story in ("A", "B"):
                cells.append(dict(L2_BASE, rho_zs=rho, beta_z=bz, story=story, kind="core", fits=("adj", "unadj")))
    for bz in (0.0, -0.4):
        for story in ("A", "B"):
            cells.append(dict(L2_BASE, K=150, beta_z=bz, story=story, kind="core150", fits=("adj", "unadj")))
    stress = [("desc+.3", dict(delta=0.3)), ("desc-.3", dict(delta=-0.3)),
              ("word+.4", dict(indicator="word", delta=0.4)), ("word-.4", dict(indicator="word", delta=-0.4)),
              ("wordcoded", dict(wordcoded=True)), ("floor", dict(floor=True)),
              ("R.25", dict(R_assumed=0.25)), ("R.6", dict(R_assumed=0.6)), ("naive", dict(naive=True)),
              ("sep150", dict(K=150, non_share=0.01))]
    for name, kw in stress:
        for bz in (0.0, -0.4):
            cells.append(dict(L2_BASE, beta_z=bz, kind=name, fits=("adj",), **kw))
    cells.append(dict(L2_BASE, beta_z=0.0, kind="register", register=True, fits=("adj",)))
    for i, c in enumerate(cells):
        c["cell"] = f"L2-{i:02d}"
    return cells


def seed_seq(*key: int) -> np.random.SeedSequence:
    return np.random.SeedSequence(ROOT_SEED, spawn_key=key)


def cell_index(cell: dict) -> int:
    return int(cell["cell"].split("-")[1])

# ------------------------------------------------------------------ L1 generator (README, "D2-L1")

R_MU, R_SD, RHO_Q_MU, RHO_Q_SD = 1.0, 1.2, -1.5, 1.0
OMEGA_POLE_SD = 0.35          # per pole and wording set; the set effect has SD about .5
BAND, FLOOR_BAND, FLOOR_LOGIT = 0.4, 1.2, -2.0
CODER_B, J2_B, J2_S = 0.3, 0.1, 0.7
M_ETA, M_PHI, M_B, M_S, N_FAM = 0.4, 0.25, 0.5, 0.3, 3
CS_P = 0.05


def _l1_pool(rng, cell: dict, n: int, alpha: float) -> dict:
    rho_q = rng.normal(RHO_Q_MU, RHO_Q_SD, n)
    r = rng.normal(R_MU, R_SD, n)
    rho_p = rho_q + r
    rs = (r - R_MU) / R_SD
    x = -0.5 * rs + np.sqrt(0.75) * rng.normal(size=n)
    lin = alpha - cell["beta"] * rs + (1.0 * x if cell["confound"] else 0.0)
    Y = rng.random(n) < expit(lin)
    keep = np.ones(n, bool)
    rho_neg = np.where(Y, rho_p, rho_q)
    rho_root = np.where(Y, rho_q, rho_p)
    if cell["selection"]:
        z = (rho_neg - rho_neg.mean()) / rho_neg.std()
        keep &= rng.random(n) < expit(-0.5 + 0.8 * z - 0.5 * Y)
    if cell["rootavail"]:
        z = (rho_root - rho_root.mean()) / rho_root.std()
        keep &= rng.random(n) < expit(0.5 + 0.8 * z)
    return dict(rho_p=rho_p, rho_q=rho_q, r=r, Y=Y, keep=keep)


def l1_alpha(cell: dict) -> float:
    """alpha such that the frame's share of Y = 1 pairs is s_off (after any selection)."""
    def share(a):
        rng = np.random.default_rng(seed_seq(90, cell_index(cell)))
        d = _l1_pool(rng, cell, 200_000, a)
        return d["Y"][d["keep"]].mean() - cell["s_off"]
    return brentq(share, -20, 20, xtol=1e-6)


def _judge(rng, r, wdiff, Y, b, s, delta, rho_p, rho_q, floor):
    d = r + wdiff + b - delta * (2 * Y - 1) + rng.logistic(0, s, r.shape)
    band = np.where(floor & (np.maximum(rho_p, rho_q) < FLOOR_LOGIT), FLOOR_BAND, BAND)
    return np.where(d < -band, 0, np.where(d > band, 2, 1)).astype(int)


def l1_dataset(cell: dict, rep: int, alpha: float) -> dict:
    rng = np.random.default_rng(seed_seq(1, cell_index(cell), rep))
    N = cell["N"]
    pool = _l1_pool(rng, cell, 6 * N, alpha)
    idx = np.flatnonzero(pool["keep"])[:N]
    rho_p, rho_q, Y = pool["rho_p"][idx].copy(), pool["rho_q"][idx].copy(), pool["Y"][idx].copy()
    n = len(idx)
    wP = rng.normal(0, OMEGA_POLE_SD, (n, 2))
    wQ = rng.normal(0, OMEGA_POLE_SD, (n, 2))
    if cell["shared"]:  # 15% of pairs take their root pole (prevalence, descriptions) from a same-type partner
        for i in np.flatnonzero(rng.random(n) < 0.15):
            partners = np.flatnonzero((Y == Y[i]) & (np.arange(n) != i))
            if len(partners) == 0:
                continue
            j = rng.choice(partners)
            if Y[i]:
                rho_q[i], wQ[i] = rho_q[j], wQ[j]
            else:
                rho_p[i], wP[i] = rho_p[j], wP[j]
    r = rho_p - rho_q
    wdiff = wP - wQ                                       # (n, 2) wording-set effects
    # orientation: true valence difference, observed with error; a wrong sign swaps P and Q
    dv = rng.normal(cell["orient_mu"], 0.6, n)
    while (bad := dv < 0.05).any():
        dv[bad] = rng.normal(cell["orient_mu"], 0.6, bad.sum())
    dv_obs = dv + rng.normal(0, 0.3, n)
    flip = dv_obs < 0
    floor = cell["floor"]
    # coder: every pair once, wording set at random
    set_c = rng.integers(0, 2, n)
    resp_c = _judge(rng, r, wdiff[np.arange(n), set_c], Y, CODER_B, cell["coder_s"], cell["delta"], rho_p, rho_q, floor)
    # second judge: half the pairs on the coder's set, half on the other (subset chosen at analysis)
    same = rng.random(n) < 0.5
    set_2 = np.where(same, set_c, 1 - set_c)
    resp_2 = _judge(rng, r, wdiff[np.arange(n), set_2], Y, J2_B, J2_S, cell["delta"], rho_p, rho_q, floor)
    p_cs = np.where(Y, 0.20, 0.05) if cell["cs_mnar"] else np.full(n, CS_P)
    cs_c = rng.random(n) < p_cs
    cs_2 = rng.random(n) < p_cs
    # model judges: three families x both wording sets
    eta = rng.normal(0, M_ETA, n)
    phi = rng.normal(0, M_PHI, (n, N_FAM))
    resp_m = np.empty((n, N_FAM, 2), int)
    for f in range(N_FAM):
        for s in range(2):
            resp_m[:, f, s] = _judge(rng, r, wdiff[:, s] + eta + phi[:, f], Y, M_B, M_S,
                                     cell["delta"] + cell["avail"], rho_p, rho_q, floor)
    # word ratings (secondary specification): negated pole rated rarer by delta_m; floored
    dm = cell["delta_m"] or 0.0
    e_p = np.maximum(rho_p - dm * Y + rng.normal(0, 0.5, n), -2.5)
    e_q = np.maximum(rho_q - dm * (~Y) + rng.normal(0, 0.5, n), -2.5)
    # the analyst's view: orientation swaps flip Y, the response scale and the poles
    Y_obs = np.where(flip, ~Y, Y)
    fl = lambda k: np.where(flip, 2 - k, k)  # noqa: E731
    e_posval, e_negval = np.where(flip, e_q, e_p), np.where(flip, e_p, e_q)  # by the analyst's valence labels
    sub_order = rng.permutation(n)   # random order for filling the second judge's Y_obs = 0 slots
    # finite-population truths for this frame (delta = 0, availability 0), by the true labels
    band = np.where(floor & (np.maximum(rho_p, rho_q) < FLOOR_LOGIT), FLOOR_BAND, BAND)
    p0c = expit((-band[:, None] - r[:, None] - wdiff - CODER_B) / cell["coder_s"]).mean(1)
    p0m = expit((-band[:, None, None] - r[:, None, None] - wdiff[:, None, :] - eta[:, None, None]
                 - phi[:, :, None] - M_B) / M_S).mean((1, 2))
    th_fp = p0c[Y].mean() - p0c[~Y].mean() if Y.any() and (~Y).any() else np.nan
    thm_fp = p0m[Y].mean() - p0m[~Y].mean() if Y.any() and (~Y).any() else np.nan
    return dict(n=n, Y=Y, Y_obs=Y_obs.astype(int), resp_c=fl(resp_c), set_c=set_c, cs_c=cs_c,
                resp_2=fl(resp_2), set_2=set_2, cs_2=cs_2, resp_m=np.where(flip[:, None, None], 2 - resp_m, resp_m),
                R_word=e_negval - e_posval, dv_obs=np.abs(dv_obs), sub_order=sub_order, flip=flip,
                theta_fp=th_fp, theta_m_fp=thm_fp)


def l1_truths(cell: dict, alpha: float) -> dict:
    """Protocol truths from a large population: coder and model-judge contrasts (no delta, no
    availability bias), the two judges' latent correlation, and the word-based slope (delta_m = 0)."""
    rng = np.random.default_rng(seed_seq(91, cell_index(cell)))
    pool = _l1_pool(rng, cell, BIG, alpha)
    out = {}
    for label, keep in (("frame", pool["keep"]), ("pool", np.ones(BIG, bool))):
        rho_p, rho_q, Y, r = (pool[k][keep] for k in ("rho_p", "rho_q", "Y", "r"))
        n = len(r)
        w = rng.normal(0, OMEGA_POLE_SD, (n, 4))
        w1, w2 = w[:, 0] - w[:, 1], w[:, 2] - w[:, 3]
        rc = _judge(rng, r, w1, Y, CODER_B, cell["coder_s"], 0.0, rho_p, rho_q, cell["floor"])
        out[f"theta_{label}"] = (rc[Y] == 0).mean() - (rc[~Y] == 0).mean()
        if label == "pool":
            continue
        eta = rng.normal(0, M_ETA, n)
        th_m = []
        for f in range(N_FAM):
            rm = _judge(rng, r, w1 + eta + rng.normal(0, M_PHI, n), Y, M_B, M_S, 0.0, rho_p, rho_q, cell["floor"])
            th_m.append((rm[Y] == 0).mean() - (rm[~Y] == 0).mean())
        out["theta_m"] = float(np.mean(th_m))
        # latent correlation, coder vs second judge, different wording sets, within pair type (pooled)
        d1 = r + w1 + rng.logistic(0, cell["coder_s"], n)
        d2 = r + w2 + rng.logistic(0, J2_S, n)
        c = [np.corrcoef(d1[m], d2[m])[0, 1] * m.sum() for m in (Y, ~Y)]
        out["rho12"] = float(sum(c) / n)
        # word-based slope with delta_m = 0 (ratings floored), MLE on the population
        e_p = np.maximum(rho_p + rng.normal(0, 0.5, n), -2.5)
        e_q = np.maximum(rho_q + rng.normal(0, 0.5, n), -2.5)
        rel = e_q - e_p  # the positive pole's relative rarity
        dv = np.abs(rng.normal(cell["orient_mu"], 0.6, n))
        b, _ = _logit_mle(np.column_stack([np.ones(n), rel, dv]), Y.astype(float))
        out["kappa"] = float(b[1])
    return out

# ------------------------------------------------------------------ L1 analyses


def _logit_mle(X: np.ndarray, y: np.ndarray, iters: int = 50):
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = expit(X @ b)
        W = p * (1 - p)
        H = X.T @ (X * W[:, None]) + 1e-8 * np.eye(X.shape[1])
        step = np.linalg.solve(H, X.T @ (y - p))
        b += step
        if np.abs(step).max() < 1e-8:
            break
    p = expit(X @ b)
    cov = np.linalg.inv(X.T @ (X * (p * (1 - p))[:, None]) + 1e-8 * np.eye(X.shape[1]))
    return b, cov


def l1_word(d: dict) -> dict:
    """Secondary specification: logistic slope of Y_obs on the positive pole's relative rarity,
    refitted over an assumed-bias grid; tipping point = assumed bias where the 90% interval reaches 0."""
    Y = d["Y_obs"].astype(float)
    grid = np.round(np.arange(-0.6, 0.6001, 0.05), 2)
    res = {}
    for a in grid:
        # R_word = negative-valence pole's rating minus positive pole's: the positive pole's relative
        # rarity. Undo an assumed bias a (negated pole rated rarer by a): raise the negated pole's rating.
        rel = d["R_word"] - a * (2 * d["Y_obs"] - 1)
        b, cov = _logit_mle(np.column_stack([np.ones(d["n"]), rel, d["dv_obs"]]), Y)
        se = np.sqrt(cov[1, 1])
        res[a] = (b[1], b[1] - 1.645 * se, b[1] + 1.645 * se)
    k0, lo0, hi0 = res[0.0]
    tip = np.nan
    if lo0 > 0:  # smallest assumed bias at which the lower bound reaches 0
        for a in grid[grid > 0]:
            if res[a][1] <= 0:
                tip = float(a)
                break
        else:
            tip = np.inf
    return dict(mean=k0, q05=lo0, q95=hi0, tip=tip)


def l1_dirichlet(d: dict, rng) -> np.ndarray:
    ok = ~d["cs_c"]
    draws = []
    for y in (1, 0):
        m = ok & (d["Y_obs"] == y)
        cnt = np.bincount(d["resp_c"][m], minlength=3)
        draws.append(rng.dirichlet(1 + cnt, 4000)[:, 0])
    return draws[0] - draws[1]


def _ordinal_logp(pm, pt, resp, eta, cut):
    return pm.logp(pm.OrderedLogistic.dist(eta=eta, cutpoints=cut), resp)


def build_l1b(N: int):
    import pymc as pm
    import pytensor.tensor as pt
    with pm.Model() as m:
        Y = pm.Data("Y", np.zeros(N, dtype="float64"))
        rc = pm.Data("rc", np.ones(N, dtype="int64"))
        sc = pm.Data("sc", np.zeros(N, dtype="int64"))
        mc = pm.Data("mc", np.ones(N, dtype="float64"))
        r2 = pm.Data("r2", np.ones(N, dtype="int64"))
        s2 = pm.Data("s2", np.zeros(N, dtype="int64"))
        m2 = pm.Data("m2", np.ones(N, dtype="float64"))
        gamma = pm.Normal("gamma", 0, 1.5)
        sig_u = pm.HalfNormal("sig_u", 1.0)
        sig_w = pm.HalfNormal("sig_w", 1.0)
        u = sig_u * pm.Normal("u_raw", 0, 1, shape=N)
        w = sig_w * pm.Normal("w_raw", 0, 1, shape=(N, 2))
        cut_c = pm.Normal("cut_c", 0, 2, shape=2, transform=pm.distributions.transforms.ordered,
                          initval=np.array([-0.5, 0.5]))
        cut_2 = pm.Normal("cut_2", 0, 2, shape=2, transform=pm.distributions.transforms.ordered,
                          initval=np.array([-0.5, 0.5]))
        tau2 = pm.LogNormal("tau2", 0, 0.5)
        mu = gamma * Y + u
        ar = pt.arange(N)
        lp_c = _ordinal_logp(pm, pt, rc, mu + w[ar, sc], cut_c)
        lp_2 = _ordinal_logp(pm, pt, r2, (mu + w[ar, s2]) / tau2, cut_2 / tau2)
        pm.Potential("lik", (lp_c * mc).sum() + (lp_2 * m2).sum())
    return m


def build_l1c(N: int):
    import pymc as pm
    import pytensor.tensor as pt
    with pm.Model() as m:
        Y = pm.Data("Y", np.zeros(N, dtype="float64"))
        R = pm.Data("R", np.ones((N, N_FAM, 2), dtype="int64"))
        gamma = pm.Normal("gamma", 0, 1.5)
        sig_u = pm.HalfNormal("sig_u", 1.0)
        sig_w = pm.HalfNormal("sig_w", 1.0)
        sig_f = pm.HalfNormal("sig_f", 1.0)
        u = sig_u * pm.Normal("u_raw", 0, 1, shape=N)
        w = sig_w * pm.Normal("w_raw", 0, 1, shape=(N, 2))
        f = sig_f * pm.Normal("f_raw", 0, 1, shape=(N, N_FAM))
        cut = pm.Normal("cut", 0, 2, shape=(N_FAM, 2), transform=pm.distributions.transforms.ordered,
                        initval=np.tile([-0.5, 0.5], (N_FAM, 1)))
        tau_rest = pm.LogNormal("tau_rest", 0, 0.5, shape=N_FAM - 1)
        tau = pt.concatenate([pt.ones(1), tau_rest])
        lp = 0.0
        for fam in range(N_FAM):
            for s in range(2):
                eta = (gamma * Y + u + w[:, s] + f[:, fam]) / tau[fam]
                lp = lp + _ordinal_logp(pm, pt, R[:, fam, s], eta, cut[fam] / tau[fam]).sum()
        pm.Potential("lik", lp)
    return m


_COMPILED: dict = {}


def _compiled(key, builder, *args):
    import nutpie
    if key not in _COMPILED:
        _COMPILED[key] = nutpie.compile_pymc_model(builder(*args), freeze_model=False)
    return _COMPILED[key]


def _sample(compiled, data: dict, seed: int, tune=2000, draws=1000, target_accept=0.95):
    import nutpie
    t0 = time.time()
    tr = nutpie.sample(compiled.with_data(**data), draws=draws, tune=tune, chains=4, cores=4, seed=seed,
                       progress_bar=False, target_accept=target_accept)
    return tr, time.time() - t0


def _post(tr, name) -> np.ndarray:
    """Posterior array with chains and draws stacked first: (S, ...)."""
    x = np.asarray(tr.posterior[name])
    return x.reshape((-1,) + x.shape[2:])


def _diag(tr, names) -> tuple[float, float, int]:
    import arviz as az
    rh, es = [], []
    for nm in names:
        x = np.asarray(tr.posterior[nm])  # (chain, draw, ...)
        x = x.reshape(x.shape[0], x.shape[1], -1)
        for j in range(x.shape[2]):
            rh.append(float(az.rhat(x[:, :, j])))
            es.append(float(az.ess(x[:, :, j])))
    div = int(np.asarray(tr.sample_stats["diverging"]).sum())
    return max(rh), min(es), div


def _summ(x: np.ndarray) -> dict:
    q = np.quantile(x, [0.05, 0.25, 0.5, 0.75, 0.95])
    return dict(mean=float(x.mean()), sd=float(x.std(ddof=1)), q05=q[0], q25=q[1], q50=q[2], q75=q[3], q95=q[4])


GH_X, GH_W = np.polynomial.hermite_e.hermegauss(30)
GH_W = GH_W / GH_W.sum()


def _p_rarer_new(g, sd, cut1, tau, y):
    """P(a judge says the positive pole is rarer) for a new pair of type y: integrate the pair's
    total random effect, N(0, sd), by Gauss-Hermite. Arrays are per posterior draw."""
    x = sd[:, None] * GH_X[None, :]
    return ((1 - expit((g[:, None] * y + x - cut1[:, None]) / tau[:, None])) * GH_W[None, :]).sum(1)


def l1_subset(d: dict, extra: int) -> np.ndarray:
    """Second judge's subset: every Y_obs = 1 pair plus `extra` random Y_obs = 0 pairs."""
    sub = d["Y_obs"] == 1
    zeros = [i for i in d["sub_order"] if d["Y_obs"][i] == 0][:extra]
    sub[zeros] = True
    return sub


def fit_l1(job: dict) -> list[dict]:
    cell, rep, design = job["cell"], job["rep"], job["design"]
    alpha, tr_ = job["alpha"], job["truth"]
    d = l1_dataset(cell, rep, alpha)
    base = dict(part="L1", cell=cell["cell"], kind=cell["kind"], N=cell["N"], s_off=cell["s_off"],
                beta=cell["beta"], design=design, rep=rep, n_pairs=d["n"], n_off_obs=int(d["Y_obs"].sum()),
                n_flip=int(d["flip"].sum()))
    fseed = int(seed_seq(3, cell_index(cell), rep, L1_DESIGNS_ALL.index(design) if design in L1_DESIGNS_ALL else 9
                         ).generate_state(1)[0])
    rows = []
    if design == "word":
        t0 = time.time()
        w = l1_word(d)
        rows.append(dict(base, estimand="kappa", truth=tr_["kappa"], mean=w["mean"], q05=w["q05"], q95=w["q95"],
                         tip=w["tip"], seconds=round(time.time() - t0, 2)))
        return rows
    if design == "a":
        t0 = time.time()
        th = l1_dirichlet(d, np.random.default_rng(fseed))
        rows.append(dict(base, estimand="theta", truth=tr_["theta_frame"], truth_pool=tr_["theta_pool"],
                         **_summ(th), seconds=round(time.time() - t0, 2)))
        return rows
    N = d["n"]
    if design in ("b10", "b30"):
        sub = l1_subset(d, 10 if design == "b10" else 30)
        data = dict(Y=d["Y_obs"].astype("float64"), rc=d["resp_c"], sc=d["set_c"],
                    mc=(~d["cs_c"]).astype("float64"), r2=d["resp_2"], s2=d["set_2"],
                    m2=(sub & ~d["cs_2"]).astype("float64"))
        tr, sec = _sample(_compiled(("b", N), build_l1b, N), data, fseed)
        g, su, sw = _post(tr, "gamma"), _post(tr, "sig_u"), _post(tr, "sig_w")
        u = _post(tr, "u_raw") * su[:, None]
        w = _post(tr, "w_raw") * sw[:, None, None]
        cut = _post(tr, "cut_c")
        tau2 = _post(tr, "tau2")
        eta = g[:, None, None] * d["Y_obs"][None, :, None] + u[:, :, None] + w      # (S, N, 2)
        p0 = (1 - expit(eta - cut[:, 0][:, None, None])).mean(axis=2)                # P(coder says P rarer)
        on = d["Y_obs"] == 1
        th_fp = p0[:, on].mean(axis=1) - p0[:, ~on].mean(axis=1)                    # this frame's pairs
        sd_new = np.sqrt(su ** 2 + sw ** 2)
        one = np.ones_like(g)
        th = _p_rarer_new(g, sd_new, cut[:, 0], one, 1.0) - _p_rarer_new(g, sd_new, cut[:, 0], one, 0.0)
        k = np.pi ** 2 / 3
        rho12 = su ** 2 / np.sqrt((su ** 2 + sw ** 2 + k) * (su ** 2 + sw ** 2 + k * tau2 ** 2))
        rh, es, dv = _diag(tr, ["gamma", "sig_u", "sig_w", "cut_c", "cut_2", "tau2"])
        common = dict(rhat_max=rh, ess_min=es, divergences=dv, seconds=round(sec, 1), n_sub=int(sub.sum()))
        rows.append(dict(base, estimand="theta", truth=tr_["theta_frame"], truth_pool=tr_["theta_pool"],
                         **_summ(th), **common))
        rows.append(dict(base, estimand="theta_fp", truth=d["theta_fp"], **_summ(th_fp), **common))
        rows.append(dict(base, estimand="rho12", truth=tr_["rho12"], **_summ(rho12), **common))
        rows.append(dict(base, estimand="gamma", truth=np.nan, **_summ(g), **common))
        return rows
    if design == "c":
        data = dict(Y=d["Y_obs"].astype("float64"), R=d["resp_m"])
        tr, sec = _sample(_compiled(("c", N), build_l1c, N), data, fseed)
        g, su, sw, sf = (_post(tr, k) for k in ("gamma", "sig_u", "sig_w", "sig_f"))
        u = _post(tr, "u_raw") * su[:, None]
        w = _post(tr, "w_raw") * sw[:, None, None]
        f = _post(tr, "f_raw") * sf[:, None, None]
        cut = _post(tr, "cut")                                    # (S, F, 2)
        tau = np.concatenate([np.ones((len(g), 1)), _post(tr, "tau_rest")], axis=1)
        on = d["Y_obs"] == 1
        ths, ths_fp = [], []
        sd_new = np.sqrt(su ** 2 + sw ** 2 + sf ** 2)
        for fam in range(N_FAM):
            eta = g[:, None, None] * d["Y_obs"][None, :, None] + u[:, :, None] + w + f[:, :, fam][:, :, None]
            p0 = (1 - expit((eta - cut[:, fam, 0][:, None, None]) / tau[:, fam][:, None, None])).mean(axis=2)
            ths_fp.append(p0[:, on].mean(axis=1) - p0[:, ~on].mean(axis=1))
            ths.append(_p_rarer_new(g, sd_new, cut[:, fam, 0], tau[:, fam], 1.0)
                       - _p_rarer_new(g, sd_new, cut[:, fam, 0], tau[:, fam], 0.0))
        th, th_fp = np.mean(ths, axis=0), np.mean(ths_fp, axis=0)
        rh, es, dv = _diag(tr, ["gamma", "sig_u", "sig_w", "sig_f", "cut", "tau_rest"])
        common = dict(rhat_max=rh, ess_min=es, divergences=dv, seconds=round(sec, 1))
        rows.append(dict(base, estimand="theta_m", truth=tr_["theta_m"], truth_coder=tr_["theta_frame"],
                         **_summ(th), **common))
        rows.append(dict(base, estimand="theta_m_fp", truth=d["theta_m_fp"], **_summ(th_fp), **common))
        rows.append(dict(base, estimand="gamma", truth=np.nan, **_summ(g), **common))
        return rows
    raise ValueError(design)

# ------------------------------------------------------------------ L2 generator (README, "D2-L2")

CATS = ("simple", "un", "in", "dis", "non", "less")
CONTRARY = (1, 2, 3)


def l2_shares(cell: dict) -> np.ndarray:
    non = cell["non_share"]
    return np.array([0.68 + (0.02 - non), 0.14, 0.08, 0.03, non, 0.05])


def l2_coefs(cell: dict) -> dict:
    bz = cell["beta_z"]
    dev = np.array([-0.2, 0.0, 0.2]) if bz != 0 else np.zeros(3)
    bzc = np.concatenate([bz + dev, [bz, 0.5 * bz]])     # un, in, dis, non, less
    return dict(bz=bzc, bs=-0.5, bv=-0.3, ba=0.8 if cell["story"] == "A" else 0.0, bh=0.6 if cell["register"] else 0.0)


def _l2_latents(rng, cell: dict, K: int) -> dict:
    z = rng.normal(size=K)
    rho = cell["rho_zs"]
    s = rho * z + np.sqrt(1 - rho ** 2) * rng.normal(size=K)
    v = -0.4 * s + np.sqrt(0.84) * rng.normal(size=K)
    h = -0.4 * z + np.sqrt(0.84) * rng.normal(size=K)
    a = (rng.random(K) < 0.4).astype(float)
    return dict(z=z, s=s, v=v, h=h, a=a)


def _l2_eta(L: dict, alpha: np.ndarray, co: dict, a_in_outcome: bool) -> np.ndarray:
    K = len(L["z"])
    eta = np.zeros((K, 6))
    for j in range(5):
        eta[:, j + 1] = (alpha[j] + co["bz"][j] * L["z"] + co["bs"] * L["s"] + co["bv"] * L["v"]
                         + (co["ba"] * L["a"] if a_in_outcome else 0.0)
                         + (co["bh"] * L["h"] if j + 1 in CONTRARY else 0.0))
    return eta


def l2_alpha(cell: dict) -> np.ndarray:
    rng = np.random.default_rng(seed_seq(92, cell_index(cell)))
    L = _l2_latents(rng, cell, 200_000)
    co, target = l2_coefs(cell), l2_shares(cell)
    alpha = np.log(target[1:] / target[0])
    for _ in range(200):
        p = softmax(_l2_eta(L, alpha, co, cell["story"] == "A"), axis=1).mean(0)
        step = np.log(target[1:] / p[1:]) - np.log(target[0] / p[0])
        alpha += step
        if np.abs(step).max() < 1e-6:
            break
    return alpha


def l2_dataset(cell: dict, rep: int, alpha: np.ndarray) -> dict:
    rng = np.random.default_rng(seed_seq(4, cell_index(cell), rep))
    K = cell["K"]
    L = _l2_latents(rng, cell, K)
    co = l2_coefs(cell)
    P = softmax(_l2_eta(L, alpha, co, cell["story"] == "A"), axis=1)
    y = (P.cumsum(1) > rng.random(K)[:, None]).argmax(1)
    neg = (y > 0).astype(float)
    if cell["story"] == "B":  # negation produces omission meaning
        L["a"] = (rng.random(K) < expit(-1.2 + 1.8 * neg)).astype(float)
    a = L["a"]
    p1 = np.where(a == 1, 0.85, 0.15)
    if cell["wordcoded"]:
        p1 = np.minimum(p1 + 0.15 * neg, 1.0)
    a_obs = (rng.random(K) < p1).astype(float)
    se = 0.6 if cell["indicator"] == "desc" else 0.5
    e = L["z"] - cell["delta"] * neg + rng.normal(0, se, K)
    if cell["floor"]:
        e = np.maximum(e, -2.0)
    arousal = 0.6 * L["s"] + rng.normal(0, 0.8, K)
    return dict(K=K, y=y, e=e, se=se, arousal=arousal, v=(L["v"] - L["v"].mean()) / L["v"].std(), a_obs=a_obs,
                L=L)


def l2_truths(cell: dict, alpha: np.ndarray) -> dict:
    """Causal average predictive comparisons (README, "Estimands"), from a large population."""
    rng = np.random.default_rng(seed_seq(93, cell_index(cell)))
    L = _l2_latents(rng, cell, BIG)
    co = l2_coefs(cell)
    a_in = cell["story"] == "A"
    out = {}
    for var in ("z", "s"):
        hi, lo = dict(L), dict(L)
        hi[var], lo[var] = L[var] + 0.5, L[var] - 0.5
        ph = softmax(_l2_eta(hi, alpha, co, a_in), axis=1)[:, list(CONTRARY)].sum(1)
        pl = softmax(_l2_eta(lo, alpha, co, a_in), axis=1)[:, list(CONTRARY)].sum(1)
        out[f"apc_{var}"] = float((ph - pl).mean())
    out["bzC"] = float(cell["beta_z"])
    return out


def build_l2(K: int, adjusted: bool, naive: bool):
    import pymc as pm
    import pytensor.tensor as pt
    with pm.Model() as m:
        y = pm.Data("y", np.zeros(K, dtype="int64"))
        e = pm.Data("e", np.zeros(K))
        se = pm.Data("se", 0.6)
        ar = pm.Data("ar", np.zeros(K))
        v = pm.Data("v", np.zeros(K))
        a = pm.Data("a", np.zeros(K))
        Rel = pm.Data("Rel", 0.36)
        z = pm.Normal("z", 0, 1, shape=K)
        c_e = pm.Normal("c_e", 0, 1)
        lam_e = pm.HalfNormal("lam_e", 1)
        pm.Normal("e_obs", c_e + lam_e * z, se, observed=e)
        if naive:
            s = (ar - ar.mean()) / ar.std()
        else:
            rho = pm.Uniform("rho", -1, 1)
            xi = pm.Normal("xi", 0, 1, shape=K)
            s = rho * z + pt.sqrt(1 - rho ** 2) * xi
            sd_ar = pm.HalfNormal("sd_ar", 2)
            c_a = pm.Normal("c_a", 0, 1)
            pm.Normal("ar_obs", c_a + pt.sqrt(Rel) * sd_ar * s, pt.sqrt(1 - Rel) * sd_ar, observed=ar)
        alpha = pm.Normal("alpha", -1.5, 2, shape=5)
        bzC = pm.Normal("bzC", 0, 1.5)
        tau_z = pm.HalfNormal("tau_z", 0.5)
        bz_con = bzC + tau_z * pm.Normal("bz_raw", 0, 1, shape=3)
        bz_non = pm.Normal("bz_non", 0, 1.5)
        bz_less = pm.Normal("bz_less", 0, 1.5)
        bz = pt.concatenate([bz_con, pt.stack([bz_non, bz_less])])
        bs = pm.Normal("bs", 0, 1.5)
        bv = pm.Normal("bv", 0, 1.5)
        lin = alpha[None, :] + bz[None, :] * z[:, None] + bs * s[:, None] + bv * v[:, None]
        if adjusted:
            ba = pm.Normal("ba", 0, 1.5)
            lin = lin + ba * a[:, None]
        eta = pt.concatenate([pt.zeros((K, 1)), lin], axis=1)
        pm.Categorical("y_obs", p=pm.math.softmax(eta, axis=1), observed=y)
    return m


def fit_l2(job: dict) -> list[dict]:
    cell, rep, fit = job["cell"], job["rep"], job["fit"]
    alpha, tr_ = np.asarray(job["alpha"]), job["truth"]
    d = l2_dataset(cell, rep, alpha)
    K = d["K"]
    adjusted = fit == "adj"
    data = dict(y=d["y"], e=d["e"], se=float(d["se"]), ar=d["arousal"], v=d["v"])
    if adjusted:
        data["a"] = d["a_obs"]
    if not cell["naive"]:
        data["Rel"] = float(cell["R_assumed"])
    fseed = int(seed_seq(5, cell_index(cell), rep, int(adjusted)).generate_state(1)[0])
    tr, sec = _sample(_compiled(("l2", K, adjusted, cell["naive"]), build_l2, K, adjusted, cell["naive"]), data, fseed)
    S = 1000  # thin for the predictive comparisons
    pick = np.linspace(0, 3999, S).astype(int)
    z = _post(tr, "z")[pick]
    if cell["naive"]:
        s = np.broadcast_to((d["arousal"] - d["arousal"].mean()) / d["arousal"].std(), z.shape)
    else:
        rho = _post(tr, "rho")[pick]
        s = rho[:, None] * z + np.sqrt(1 - rho ** 2)[:, None] * _post(tr, "xi")[pick]
    al = _post(tr, "alpha")[pick]
    bzc = _post(tr, "bzC")[pick][:, None] + _post(tr, "tau_z")[pick][:, None] * _post(tr, "bz_raw")[pick]
    bz = np.concatenate([bzc, _post(tr, "bz_non")[pick][:, None], _post(tr, "bz_less")[pick][:, None]], axis=1)
    bs, bv = _post(tr, "bs")[pick], _post(tr, "bv")[pick]
    ba = _post(tr, "ba")[pick] if adjusted else np.zeros(S)

    def p_con(zz, ss):
        lin = (al[:, None, :] + bz[:, None, :] * zz[:, :, None] + bs[:, None, None] * ss[:, :, None]
               + bv[:, None, None] * d["v"][None, :, None] + ba[:, None, None] * d["a_obs"][None, :, None])
        eta = np.concatenate([np.zeros(lin.shape[:2] + (1,)), lin], axis=2)
        return softmax(eta, axis=2)[:, :, list(CONTRARY)].sum(2)

    apc_z = (p_con(z + 0.5, s) - p_con(z - 0.5, s)).mean(1)
    apc_s = (p_con(z, s + 0.5) - p_con(z, s - 0.5)).mean(1)
    names = ["bzC", "tau_z", "bz_non", "bz_less", "bs", "bv", "alpha", "lam_e"] + (["ba"] if adjusted else []) \
        + ([] if cell["naive"] else ["rho", "sd_ar"])
    rh, es, dv = _diag(tr, names)
    base = dict(part="L2", cell=cell["cell"], kind=cell["kind"], K=K, rho_zs=cell["rho_zs"], beta_z=cell["beta_z"],
                story=cell["story"], fit=fit, rep=rep, rhat_max=rh, ess_min=es, divergences=dv, seconds=round(sec, 1),
                n_neg=int((d["y"] > 0).sum()), n_non=int((d["y"] == 4).sum()), n_less=int((d["y"] == 5).sum()))
    return [dict(base, estimand="apc_z", truth=tr_["apc_z"], **_summ(apc_z)),
            dict(base, estimand="apc_s", truth=tr_["apc_s"], **_summ(apc_s)),
            dict(base, estimand="bzC", truth=tr_["bzC"], **_summ(_post(tr, "bzC")))]

# ------------------------------------------------------------------ truths, jobs, running


def compute_truths(part: str) -> pd.DataFrame:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"truths_{part}.json"
    if path.exists():
        return json.loads(path.read_text())
    out = {}
    if part == "l1":
        for c in l1_cells():
            a = l1_alpha(c)
            out[c["cell"]] = dict(alpha=a, **l1_truths(c, a))
            print(c["cell"], c["kind"], {k: round(v, 3) for k, v in out[c["cell"]].items()}, flush=True)
    else:
        for c in l2_cells():
            a = l2_alpha(c)
            out[c["cell"]] = dict(alpha=a.tolist(), **l2_truths(c, a))
            print(c["cell"], c["kind"], {k: (round(v, 3) if isinstance(v, float) else v)
                                         for k, v in out[c["cell"]].items() if k != "alpha"}, flush=True)
    path.write_text(json.dumps(out, indent=1))
    return out


def jobs_for(part: str, reps: int, reps_a: int, cells: list[str] | None = None) -> list[dict]:
    T = compute_truths(part)
    jobs = []
    if part == "l1":
        for c in l1_cells():
            if cells and c["cell"] not in cells:
                continue
            t = T[c["cell"]]
            for design in c["designs"]:
                n = reps_a if design in ("a", "word") else reps
                jobs += [dict(part="l1", cell=c, rep=r, design=design, alpha=t["alpha"], truth=t) for r in range(n)]
    else:
        for c in l2_cells():
            if cells and c["cell"] not in cells:
                continue
            t = T[c["cell"]]
            jobs += [dict(part="l2", cell=c, rep=r, fit=f, alpha=t["alpha"], truth=t)
                     for f in c["fits"] for r in range(reps)]
    return jobs


L1_COLS = ["part", "cell", "kind", "N", "s_off", "beta", "design", "rep", "n_pairs", "n_off_obs", "n_flip", "n_sub",
           "estimand", "truth", "truth_pool", "truth_coder", "mean", "sd", "q05", "q25", "q50", "q75", "q95", "tip",
           "rhat_max", "ess_min", "divergences", "seconds"]
L2_COLS = ["part", "cell", "kind", "K", "rho_zs", "beta_z", "story", "fit", "rep", "n_neg", "n_non", "n_less",
           "estimand", "truth", "mean", "sd", "q05", "q25", "q50", "q75", "q95", "rhat_max", "ess_min",
           "divergences", "seconds"]


def _write(rows: list[dict], out: Path):
    cols = L1_COLS if rows[0]["part"] == "L1" else L2_COLS
    pd.DataFrame(rows).reindex(columns=cols).to_csv(out, mode="a", header=not out.exists(), index=False)


def job_key(j: dict) -> tuple:
    return (j["cell"]["cell"], j.get("design", j.get("fit")), j["rep"])


def run_job(j: dict) -> list[dict]:
    return fit_l1(j) if j["part"] == "l1" else fit_l2(j)


def run(jobs: list[dict], workers: int, out: Path) -> list:
    done = set()
    if out.exists():
        prev = pd.read_csv(out)
        col = "design" if "design" in prev else "fit"
        done = set(zip(prev["cell"], prev[col].astype(str), prev["rep"]))
    todo = [j for j in jobs if (j["cell"]["cell"], str(j.get("design", j.get("fit"))), j["rep"]) not in done]
    # group by compiled model so each worker reuses its compilations
    todo.sort(key=lambda j: (str(j.get("design", j.get("fit"))), j["cell"].get("N", j["cell"].get("K")),
                             j["cell"]["cell"], j["rep"]))
    print(f"{len(jobs)} fits requested, {len(todo)} to run now -> {out.relative_to(ROOT)}", flush=True)
    failures = []
    fast = [j for j in todo if j.get("design") in ("a", "word")]
    slow = [j for j in todo if j not in fast]
    for j in fast:  # closed-form or MLE: run inline
        try:
            _write(run_job(j), out)
        except Exception as e:  # noqa: BLE001
            failures.append(dict(job=job_key(j), error=repr(e)[:500]))
    if fast:
        print(f"{len(fast)} closed-form/MLE fits done", flush=True)
    if slow:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(run_job, j): j for j in slow}
            for i, fut in enumerate(as_completed(futs), 1):
                j = futs[fut]
                try:
                    rows = fut.result()
                    _write(rows, out)
                    r0 = rows[0]
                    print(f"[{i}/{len(slow)}] {job_key(j)} {r0['kind']}: {r0['seconds']}s rhat {r0['rhat_max']:.3f} "
                          f"div {r0['divergences']}", flush=True)
                except Exception as e:  # noqa: BLE001
                    failures.append(dict(job=job_key(j), error=repr(e)[:500]))
                    print(f"[{i}/{len(slow)}] FAILED {job_key(j)}: {e!r}"[:400], flush=True)
    return failures


def write_log(command: str, args: dict, outputs: list, failures: list, elapsed: float) -> Path:
    import arviz
    import nutpie
    import pymc
    import pytensor
    import scipy
    LOGS.mkdir(exist_ok=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "scripts"], cwd=ROOT, capture_output=True,
                                text=True).stdout.strip())
    log = dict(timestamp=datetime.now().isoformat(timespec="seconds"), script="scripts/d2/d2.py", command=command,
               args=args, argv=sys.argv, git_sha=sha, scripts_dirty=dirty, python=sys.version,
               platform=platform.platform(), pytensor_flags=os.environ.get("PYTENSOR_FLAGS"),
               packages=dict(pymc=pymc.__version__, nutpie=nutpie.__version__, pytensor=pytensor.__version__,
                             arviz=arviz.__version__, numpy=np.__version__, pandas=pd.__version__,
                             scipy=scipy.__version__),
               root_seed=ROOT_SEED, outputs=[str(Path(o).relative_to(ROOT)) for o in outputs], failures=failures,
               elapsed_seconds=round(elapsed, 1))
    path = LOGS / f"d2-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(log, indent=2, default=str))
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("truths")
    p = sub.add_parser("pilot")
    p.add_argument("--workers", type=int, default=2)
    r = sub.add_parser("run")
    r.add_argument("--part", choices=("l1", "l2"), required=True)
    r.add_argument("--reps", type=int, required=True)
    r.add_argument("--reps-a", type=int, default=100)
    r.add_argument("--workers", type=int, default=2)
    r.add_argument("--cells", default=None, help="comma-separated cell ids")
    r.add_argument("--out", default=None)
    args = ap.parse_args()
    t0 = time.time()
    if args.cmd == "truths":
        compute_truths("l1")
        compute_truths("l2")
        print("truths written", flush=True)
        return
    if args.cmd == "pilot":
        # README, "Order of running": two replicates of one L1 design (b) cell and one L2 core cell
        l1c = next(c["cell"] for c in l1_cells() if c["kind"] == "core" and c["N"] == 80 and c["s_off"] == 0.2
                   and c["beta"] == 1.0)
        l2c = next(c["cell"] for c in l2_cells() if c["kind"] == "core" and c["rho_zs"] == -0.5 and c["beta_z"] == -0.4
                   and c["story"] == "A")
        o1, o2 = RESULTS / "pilot_l1.csv", RESULTS / "pilot_l2.csv"
        failures = run(jobs_for("l1", 2, 2, [l1c]), args.workers, o1)
        failures += run(jobs_for("l2", 2, 2, [l2c]), args.workers, o2)
        print("log:", write_log("pilot", vars(args), [o1, o2], failures, time.time() - t0).relative_to(ROOT))
        return
    cells = args.cells.split(",") if args.cells else None
    out = RESULTS / (args.out or f"{args.part}_grid.csv")
    failures = run(jobs_for(args.part, args.reps, args.reps_a, cells), args.workers, out)
    print("log:", write_log("run", vars(args), [out], failures, time.time() - t0).relative_to(ROOT))


if __name__ == "__main__":
    main()
