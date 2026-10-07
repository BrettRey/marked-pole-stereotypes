#!/usr/bin/env python3
"""D1: design simulation for strand B (fake data only; never evidence).

Spec: scripts/d1/README.md, written and committed before this ran.

Run in the project venv, e.g.
    .venv/bin/python scripts/d1/d1.py pilot
    .venv/bin/python scripts/d1/d1.py grid --reps 20 --workers 2
    .venv/bin/python scripts/d1/d1.py export-brms
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# pytensor appends "-ld64" on macOS >= 15; the wrapper drops it (README, Environment).
# Must be set before pytensor is imported.
if sys.platform == "darwin":
    os.environ.setdefault("PYTENSOR_FLAGS", f"cxx={ROOT / 'scripts' / 'd1' / 'bin' / 'clang++'}")

import argparse  # noqa: E402
import itertools  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402
from concurrent.futures import ProcessPoolExecutor, as_completed  # noqa: E402
from datetime import datetime  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.optimize import brentq  # noqa: E402
from scipy.special import expit, logsumexp  # noqa: E402

RESULTS = ROOT / "results" / "d1"
LOGS = ROOT / "logs"
ROOT_SEED = 20261008
I_ITEMS = 400

SCENARIOS = ("s1_recovery", "s2_register", "s3_mechanism")
SIZES = {"small": dict(G=40, N_g=18), "large": dict(G=43, N_g=134)}
INDICATORS = {"f_only": None, "e_r50": 0.5, "e_r80": 0.8}

# Generating values (README, "Generating model")
KAPPA, TAU = 0.5, -0.3
GAMMA = dict(g_rho=-0.5, g_v=-1.0, g_s=-0.3)
LAMBDA = dict(rho=0.4, s=0.3, v=0.3, m=-0.3, resid=0.7)
P_MARKED = 0.15
E_VALENCE_BIAS = 0.2
PHI = 2.0
U_SD = 0.5
H_LOADINGS = dict(f=-0.5, m=0.8, prod=0.4)  # scenario 2 only
BETA = {
    "s1_recovery": dict(b_rho=-0.3, b_m=0.0, b_f=0.3, b_v=-0.5),
    "s2_register": dict(b_rho=0.0, b_m=0.0, b_f=0.3, b_v=-0.5),
}
MECH = dict(base_logit=np.log(0.25 / 0.75), society_M=100, sample_n=30, sel=5.0, acc=0.3)

# Tracked coefficients (post-pilot reparameterization, README "Fitting model, v2"):
# z = within-valence rarity (standardized residual of rho given valence);
# *_vt = total valence association (direct + via rarity). The split of the
# valence association into direct and via-rarity parts is not identified.
TRACKED_PROD = ("b_z", "b_m", "b_f", "b_vt")
TRACKED_MARK = ("g_z", "g_vt", "g_s")
SQ = np.sqrt(1 - KAPPA**2)


def truths(scenario: str) -> dict:
    """True values of tracked coefficients (None = no single true value)."""
    t = dict(g_z=GAMMA["g_rho"] * SQ, g_vt=GAMMA["g_v"] + GAMMA["g_rho"] * KAPPA, g_s=GAMMA["g_s"])
    # c_z = b_z + b_f * lam_z: total effect of within-valence rarity on production,
    # including the path through word frequency's direct dependence on rarity
    # (f's loading on z is LAMBDA["rho"] * SQ); excludes the small path via marking.
    if scenario == "s3_mechanism":
        # The process has no direct marking or valence term and no log-linear
        # rarity or frequency coefficient: b_z, b_f, b_vt are compared with the
        # oracle; b_m's truth is 0.
        t.update(b_z=None, b_m=0.0, b_f=None, b_vt=None, c_z=None)
    else:
        b = BETA[scenario]
        t.update(b_z=b["b_rho"] * SQ, b_m=b["b_m"], b_f=b["b_f"], b_vt=b["b_v"] + b["b_rho"] * KAPPA,
                 c_z=(b["b_rho"] + b["b_f"] * LAMBDA["rho"]) * SQ)
    return t


def seed_seq(*key: int) -> np.random.SeedSequence:
    return np.random.SeedSequence(ROOT_SEED, spawn_key=key)


# ------------------------------------------------------------------ data

def gen_items(rng, scenario: str) -> dict:
    n = I_ITEMS
    v = rng.normal(size=n)
    zres = rng.normal(size=n)  # within-valence rarity, standardized
    rho = KAPPA * v + np.sqrt(1 - KAPPA**2) * zres
    s = TAU * v + np.sqrt(1 - TAU**2) * rng.normal(size=n)
    h = rng.normal(size=n) if scenario == "s2_register" else np.zeros(n)
    lin_m = GAMMA["g_rho"] * rho + GAMMA["g_v"] * v + GAMMA["g_s"] * s + H_LOADINGS["m"] * h
    g0 = brentq(lambda c: expit(c + lin_m).mean() - P_MARKED, -20, 20)
    m = (rng.random(n) < expit(g0 + lin_m)).astype(float)
    f = (LAMBDA["rho"] * rho + LAMBDA["s"] * s + LAMBDA["v"] * v + LAMBDA["m"] * m
         + H_LOADINGS["f"] * h + LAMBDA["resid"] * rng.normal(size=n))
    a = s + rng.normal(size=n)
    eps_e = rng.normal(size=n)  # one draw, scaled per reliability: paired conditions
    e = {k: rho + E_VALENCE_BIAS * v + np.sqrt((1 - r) / r) * eps_e
         for k, r in INDICATORS.items() if r is not None}
    u = rng.normal(size=n)
    return dict(v=v, rho=rho, z=zres, s=s, h=h, m=m, f=f, a=a, e=e, u=u, g0=g0)


def gen_counts_nb(rng, d: dict, G: int, N_g: int, scenario: str) -> np.ndarray:
    b = BETA[scenario]
    eta = (b["b_rho"] * d["rho"] + b["b_m"] * d["m"] + b["b_f"] * d["f"] + b["b_v"] * d["v"]
           + H_LOADINGS["prod"] * d["h"] + U_SD * d["u"])
    alpha = np.log(N_g) - logsumexp(eta)
    mu = np.broadcast_to(np.exp(alpha + eta), (G, len(eta)))
    return rng.negative_binomial(PHI, PHI / (PHI + mu))


def gen_counts_mech(rng, d: dict, G: int, N_g: int) -> np.ndarray:
    """Stylized UWA-type process (README, scenario 3). One response per
    simulated participant per group; N_g participants each answer every group."""
    n_items = len(d["rho"])
    pi = expit(MECH["base_logit"] + d["rho"])
    M, n = MECH["society_M"], MECH["sample_n"]
    society = rng.binomial(M, pi, size=(G, n_items))
    samp = rng.hypergeometric(society[None], M - society[None], n, size=(N_g, G, n_items))
    tot = samp.sum(axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        ppv = np.where(tot > 0, samp / tot, 0.0)
    sd = ppv.std(axis=2, keepdims=True)
    z = (ppv - ppv.mean(axis=2, keepdims=True)) / np.where(sd > 0, sd, 1.0)
    logits = MECH["sel"] * z + MECH["acc"] * d["f"][None, None, :]
    logits -= logits.max(axis=2, keepdims=True)
    p = np.exp(logits)
    p /= p.sum(axis=2, keepdims=True)
    cum = p.cumsum(axis=2)
    choice = (cum < rng.random((N_g, G, 1))).sum(axis=2).clip(max=n_items - 1)
    counts = np.zeros((G, n_items), dtype=int)
    np.add.at(counts, (np.broadcast_to(np.arange(G), (N_g, G)), choice), 1)
    return counts


def make_dataset(scenario: str, size: str, rep: int) -> tuple[dict, np.ndarray]:
    si, zi = SCENARIOS.index(scenario), list(SIZES).index(size)
    rng = np.random.default_rng(seed_seq(1, si, zi, rep))
    d = gen_items(rng, scenario)
    G, N_g = SIZES[size]["G"], SIZES[size]["N_g"]
    counts = gen_counts_mech(rng, d, G, N_g) if scenario == "s3_mechanism" else gen_counts_nb(rng, d, G, N_g, scenario)
    return d, counts


# ------------------------------------------------------------------ models

def build_joint(d: dict, counts: np.ndarray, indicator: str, prior_scale: float, N_g: int):
    """Fitting model, v2 (post-pilot). The latent is within-valence rarity z
    (standard normal); every equation has its own total valence coefficient.
    v1 modelled rho = kappa v + ..., which left kappa, each indicator's valence
    bias and the valence coefficients trading off along a ridge (pilot 1 and
    scripts/d1/diag_corr.py)."""
    import pymc as pm

    v, m, f, a = d["v"], d["m"], d["f"], d["a"]
    G, n_items = counts.shape
    ps = prior_scale
    with pm.Model() as model:
        z = pm.Normal("z", 0, 1, shape=n_items)
        tau = pm.Uniform("tau", -1, 1)
        s = pm.Deterministic("s", tau * v + pm.math.sqrt(1 - tau**2) * pm.Normal("xi", 0, 1, shape=n_items))
        # word frequency (lam_z > 0 fixes the sign of z)
        lam_z = pm.HalfNormal("lam_z", ps)
        lam = {k: pm.Normal(f"lam_{k}", 0, ps) for k in ("s", "vt", "m")}
        pm.Normal("f_obs", pm.Normal("c_f", 0, 2.5) + lam_z * z + lam["s"] * s + lam["vt"] * v + lam["m"] * m,
                  pm.HalfNormal("sig_f", 1), observed=f)
        # arousal: loading on s fixed at 1 (identifies tau)
        pm.Normal("a_obs", pm.Normal("c_a", 0, 2.5) + s, pm.HalfNormal("sig_a", 1), observed=a)
        # prevalence indicator: free positive loading on z, free total valence term.
        # v2.2 (post-pilot): its measurement-error SD is known, as it would be for a
        # norm averaged over raters (item-level standard errors). With only one
        # strong indicator, a free error SD leaves the split between true rarity
        # and error unidentified, and every rarity coefficient scales with it.
        if indicator != "f_only":
            r = INDICATORS[indicator]
            pm.Normal("e_obs", pm.Normal("c_e", 0, 2.5) + pm.HalfNormal("lam_e", ps) * z
                      + pm.Normal("c_ev", 0, ps) * v, np.sqrt((1 - r) / r), observed=d["e"][indicator])
        # marking
        g = {k: pm.Normal(k, 0, ps) for k in TRACKED_MARK}
        pm.Bernoulli("m_obs", logit_p=pm.Normal("g0", 0, 2.5) + g["g_z"] * z + g["g_vt"] * v + g["g_s"] * s,
                     observed=m)
        # production. Shear reparameterization (v2.1, post-pilot): f is both an
        # indicator of z and a predictor here, so b_z and b_f trade off through
        # lam_z (posterior r = -.93). Sample c_z = b_z + b_f * lam_z (the total
        # z effect) and derive b_z; the prior stays N(0, ps) on b_z via a
        # Potential, and the map has Jacobian 1, so the model is unchanged.
        b = {k: pm.Normal(k, 0, ps) for k in ("b_m", "b_f", "b_vt")}
        c_z = pm.Flat("c_z")
        b_z = pm.Deterministic("b_z", c_z - b["b_f"] * lam_z)
        pm.Potential("b_z_prior", pm.logp(pm.Normal.dist(0, ps), b_z))
        sig_u = pm.HalfNormal("sig_u", 1)
        eta = (b_z * z + b["b_m"] * m + b["b_f"] * f + b["b_vt"] * v
               + sig_u * pm.Normal("u_raw", 0, 1, shape=n_items))
        alpha = pm.Normal("alpha", np.log(N_g / n_items), 2, shape=G)
        pm.NegativeBinomial("n_obs", mu=pm.math.exp(alpha[:, None] + eta[None, :]),
                            alpha=pm.HalfNormal("phi", 5), observed=counts)
    return model


def build_oracle(d: dict, counts: np.ndarray, prior_scale: float, N_g: int):
    """Production submodel with the true within-valence rarity z as data (scenario 3 reference)."""
    import pymc as pm

    G, n_items = counts.shape
    with pm.Model() as model:
        b = {k: pm.Normal(k, 0, prior_scale) for k in TRACKED_PROD}
        sig_u = pm.HalfNormal("sig_u", 1)
        eta = (b["b_z"] * d["z"] + b["b_m"] * d["m"] + b["b_f"] * d["f"] + b["b_vt"] * d["v"]
               + sig_u * pm.Normal("u_raw", 0, 1, shape=n_items))
        alpha = pm.Normal("alpha", np.log(N_g / n_items), 2, shape=G)
        pm.NegativeBinomial("n_obs", mu=pm.math.exp(alpha[:, None] + eta[None, :]),
                            alpha=pm.HalfNormal("phi", 5), observed=counts)
    return model


# ------------------------------------------------------------------ fitting

def fit_job(job: dict) -> list[dict]:
    """One fit. Regenerates its dataset from the seed, so jobs are independent."""
    import arviz as az
    import pymc as pm

    scenario, size, rep = job["scenario"], job["size"], job["rep"]
    d, counts = make_dataset(scenario, size, rep)
    N_g = SIZES[size]["N_g"]
    if job["model"] == "oracle":
        model, tracked = build_oracle(d, counts, job["prior_scale"], N_g), TRACKED_PROD
    else:
        model = build_joint(d, counts, job["indicator"], job["prior_scale"], N_g)
        tracked = TRACKED_PROD + TRACKED_MARK
    fit_seed = int(seed_seq(2, SCENARIOS.index(scenario), list(SIZES).index(size), rep,
                            list(INDICATORS).index(job["indicator"]) if job["indicator"] else 9,
                            int(job["prior_scale"] * 10), 1 if job["model"] == "oracle" else 0
                            ).generate_state(1)[0])
    t0 = time.time()
    with model:
        kw = {"nuts_sampler_kwargs": {"adaptation": "low_rank"}} if job.get("low_rank") else {}
        idata = pm.sample(draws=1000, tune=job.get("tune", 1000), chains=4, cores=4, nuts_sampler="nutpie",
                          target_accept=0.9, random_seed=fit_seed, progressbar=False, **kw)
    elapsed = time.time() - t0
    if "c_z" in model.named_vars:  # v2.1: total within-valence rarity effect on production
        tracked = tuple(tracked) + ("c_z",)
    diag_vars = list(tracked) + [x for x in ("tau", "lam_z", "lam_e", "sig_u", "phi") if x in model.named_vars]
    rhat = az.rhat(idata, var_names=diag_vars)
    ess = az.ess(idata, var_names=diag_vars)
    rhat_max = max(float(np.max(rhat[x].values)) for x in diag_vars)
    ess_min = min(float(np.min(ess[x].values)) for x in diag_vars)
    divergences = int(np.asarray(idata.sample_stats["diverging"]).sum())
    tr = truths(scenario)
    rows = []
    for k in tracked:
        x = np.asarray(idata.posterior[k]).ravel()
        rows.append(dict(scenario=scenario, size=size, rep=rep, model=job["model"],
                         param="v2_within_valence", low_rank=bool(job.get("low_rank")),
                         tune=job.get("tune", 1000),
                         indicator=job["indicator"], prior_scale=job["prior_scale"], coef=k,
                         truth=tr.get(k), mean=x.mean(), sd=x.std(ddof=1),
                         q05=np.quantile(x, 0.05), q95=np.quantile(x, 0.95),
                         prior_sd=job["prior_scale"], rhat_coef=float(np.max(rhat[k].values)),
                         ess_coef=float(np.min(ess[k].values)), rhat_max=rhat_max, ess_min=ess_min,
                         divergences=divergences, seconds=round(elapsed, 1), fit_seed=fit_seed,
                         n_marked=int(d["m"].sum()), total_count=int(counts.sum()),
                         nonzero_cells=int((counts > 0).sum())))
    return rows


def jobs_for(reps: range) -> list[dict]:
    jobs = []
    for scenario, size, rep in itertools.product(SCENARIOS, SIZES, reps):
        for ind in INDICATORS:
            jobs.append(dict(scenario=scenario, size=size, rep=rep, model="joint", indicator=ind, prior_scale=1.0))
            if ind == "f_only":
                jobs.append(dict(scenario=scenario, size=size, rep=rep, model="joint", indicator=ind, prior_scale=2.5))
        if scenario == "s3_mechanism":
            jobs.append(dict(scenario=scenario, size=size, rep=rep, model="oracle", indicator=None, prior_scale=1.0))
    return jobs


def chunk_jobs(reps: int, chunk: int, n_chunks: int) -> list[dict]:
    """Deterministic slice of the full grid for one machine: job i goes to
    chunk i mod n_chunks, which spreads scenarios and sizes across chunks."""
    return [j for i, j in enumerate(jobs_for(range(reps))) if i % n_chunks == chunk]


def run(jobs: list[dict], workers: int, out_name: str, max_fits: int | None = None) -> tuple[Path, list]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / out_name
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():  # resume: skip fits already written
        prev = pd.read_csv(out)
        done = {tuple(r) for r in prev[["scenario", "size", "rep", "model", "indicator", "prior_scale"]]
                .astype(str).drop_duplicates().itertuples(index=False)}
    todo = [j for j in jobs if (j["scenario"], j["size"], str(j["rep"]), j["model"], str(j["indicator"]),
                                str(j["prior_scale"])) not in done]
    if max_fits is not None:
        todo = todo[:max_fits]
    print(f"{len(jobs)} fits requested, {len(todo)} to run now", flush=True)
    failures = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fit_job, j): j for j in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            j = futs[fut]
            try:
                rows = fut.result()
                pd.DataFrame(rows).to_csv(out, mode="a", header=not out.exists(), index=False)
                print(f"[{i}/{len(todo)}] {j['scenario']} {j['size']} rep{j['rep']} {j['model']} "
                      f"{j['indicator']} prior{j['prior_scale']}: {rows[0]['seconds']}s, "
                      f"rhat_max {rows[0]['rhat_max']:.3f}, div {rows[0]['divergences']}", flush=True)
            except Exception as e:  # noqa: BLE001
                failures.append(dict(job=j, error=repr(e)[:500]))
                print(f"[{i}/{len(todo)}] FAILED {j}: {e!r}"[:400], flush=True)
    return out, failures


# ------------------------------------------------------------------ brms export

def export_brms():
    """One scenario-1 dataset (small, rep 0) as CSV for scripts/d1/brms_check.R."""
    d, counts = make_dataset("s1_recovery", "small", 0)
    outdir = RESULTS / "brms_check"
    outdir.mkdir(parents=True, exist_ok=True)
    items = pd.DataFrame(dict(item=np.arange(1, I_ITEMS + 1), v=d["v"], m=d["m"].astype(int), f=d["f"],
                              a=d["a"], e=d["e"]["e_r80"]))
    G = counts.shape[0]
    long = pd.DataFrame(dict(group=np.repeat(np.arange(1, G + 1), I_ITEMS),
                             item=np.tile(np.arange(1, I_ITEMS + 1), G), n=counts.ravel()))
    items.to_csv(outdir / "items.csv", index=False)
    long.to_csv(outdir / "counts_long.csv", index=False)
    print("wrote", outdir.relative_to(ROOT))


# ------------------------------------------------------------------ logging

def write_log(command: str, args: dict, outputs: list, failures: list, elapsed: float) -> Path:
    import arviz
    import nutpie
    import pymc
    import pytensor
    import scipy

    LOGS.mkdir(exist_ok=True)
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
                                    text=True).stdout.strip())
    except Exception:  # noqa: BLE001
        sha, dirty = None, None
    log = dict(timestamp=datetime.now().isoformat(timespec="seconds"), script="scripts/d1/d1.py",
               command=command, args=args, argv=sys.argv, git_sha=sha, git_dirty=dirty,
               python=sys.version, platform=platform.platform(), pytensor_flags=os.environ.get("PYTENSOR_FLAGS"),
               packages=dict(pymc=pymc.__version__, nutpie=nutpie.__version__, pytensor=pytensor.__version__,
                             arviz=arviz.__version__, numpy=np.__version__, pandas=pd.__version__,
                             scipy=scipy.__version__),
               root_seed=ROOT_SEED, outputs=[str(Path(o).relative_to(ROOT)) for o in outputs],
               failures=failures, elapsed_seconds=round(elapsed, 1))
    path = LOGS / f"d1-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(log, indent=2, default=str))
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("pilot", help="1 rep per cell")
    p.add_argument("--workers", type=int, default=2)
    g = sub.add_parser("grid", help="full grid")
    g.add_argument("--reps", type=int, required=True)
    g.add_argument("--workers", type=int, default=2)
    c = sub.add_parser("chunk", help="one slice of the grid (resumable)")
    c.add_argument("--reps", type=int, required=True)
    c.add_argument("--chunk", type=int, required=True)
    c.add_argument("--of", type=int, required=True, dest="n_chunks")
    c.add_argument("--max-fits", type=int, default=None, help="stop after this many new fits")
    c.add_argument("--workers", type=int, default=1)
    c.add_argument("--list", action="store_true", help="print the chunk's jobs and exit")
    fj = sub.add_parser("fits", help="run an explicit list of jobs")
    fj.add_argument("--jobs-json", required=True, help="JSON list of job dicts")
    fj.add_argument("--out", required=True, help="CSV name under results/d1/")
    fj.add_argument("--workers", type=int, default=2)
    sub.add_parser("export-brms")
    args = ap.parse_args()
    t0 = time.time()
    if args.command == "export-brms":
        export_brms()
        return
    if args.command == "chunk":
        jobs = chunk_jobs(args.reps, args.chunk, args.n_chunks)
        if args.list:
            for j in jobs:
                print(j)
            print(len(jobs), "jobs")
            return
        out_name = f"grid/chunk_{args.chunk:02d}_of_{args.n_chunks:02d}.csv"
        out, failures = run(jobs, args.workers, out_name, args.max_fits)
    elif args.command == "fits":
        out, failures = run(json.loads(args.jobs_json), args.workers, args.out)
    else:
        reps = range(1) if args.command == "pilot" else range(args.reps)
        out, failures = run(jobs_for(reps), args.workers, "pilot_fits.csv" if args.command == "pilot" else "fits.csv")
    print("log:", write_log(args.command, vars(args), [out], failures, time.time() - t0).relative_to(ROOT))


if __name__ == "__main__":
    main()
