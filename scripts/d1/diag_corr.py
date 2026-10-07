#!/usr/bin/env python3
"""Post-pilot diagnostic: where does the joint model mix slowly? One fit
(scenario 1, small, rep 0, e at r = .8, centered latents); prints ESS for
scalar parameters and posterior correlations with b_v. Computational only.
Run: .venv/bin/python scripts/d1/diag_corr.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d1  # noqa: E402

if __name__ == "__main__":
    import arviz as az
    import pymc as pm
    d, counts = d1.make_dataset("s1_recovery", "small", 0)
    model = d1.build_joint(d, counts, "e_r80", 1.0, d1.SIZES["small"]["N_g"], "centered_both")
    with model:
        idata = pm.sample(draws=1000, tune=1000, chains=4, cores=4, nuts_sampler="nutpie",
                          target_accept=0.9, random_seed=7, progressbar=False)
    post = idata.posterior
    scal = [k for k in post.data_vars if post[k].ndim == 2]
    flat = {k: np.asarray(post[k]).ravel() for k in scal}
    v = d["v"]
    u = np.asarray(post["u_raw"]).reshape(-1, len(v))
    flat["u_raw·v"] = u @ v / len(v)
    flat["mean(u_raw)"] = u.mean(axis=1)
    rho = np.asarray(post["rho"]).reshape(-1, len(v))
    flat["mean(rho)"] = rho.mean(axis=1)
    flat["sd(rho)"] = rho.std(axis=1)
    alpha = np.asarray(post["alpha"]).reshape(-1, counts.shape[0])
    flat["mean(alpha)"] = alpha.mean(axis=1)
    ess = az.ess(idata, var_names=scal)
    print("ESS (bulk) of scalar parameters:")
    print(pd.Series({k: float(ess[k].values) for k in scal}).sort_values().round(0).to_string())
    df = pd.DataFrame(flat)
    print("\nPosterior correlations with b_v and b_rho (|r| > .3):")
    c = df.corr()
    for target in ("b_v", "b_rho", "g_v"):
        s = c[target].drop(target)
        print(f"{target}:", s[s.abs() > 0.3].round(2).to_dict())
