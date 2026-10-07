#!/usr/bin/env python3
"""SUPERSEDED by the v2 fitting model (build_joint no longer takes a
parameterization argument); kept as the record of the check that was run.

Post-pilot computational check (added after pilot 1): which parameterization
of the latents samples cleanly? Same model and priors in every variant; one
scenario-1 dataset (small, rep 0) at each indicator condition. Pilot 1 already
has the non-centered baseline for this dataset (results/d1/pilot1_fits_stopped.csv).
Run: .venv/bin/python scripts/d1/param_check.py
"""
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d1  # noqa: E402

VARIANTS = [dict(param="centered_rho", low_rank=False), dict(param="centered_both", low_rank=False),
            dict(param="centered_rho", low_rank=True)]

if __name__ == "__main__":
    jobs = [dict(scenario="s1_recovery", size="small", rep=0, model="joint", indicator=ind, prior_scale=1.0, **v)
            for v in VARIANTS for ind in d1.INDICATORS]
    out = d1.RESULTS / "param_check_fits.csv"
    with ProcessPoolExecutor(max_workers=2) as ex:
        futs = {ex.submit(d1.fit_job, j): j for j in jobs}
        for fut in as_completed(futs):
            j = futs[fut]
            try:
                rows = fut.result()
                pd.DataFrame(rows).to_csv(out, mode="a", header=not out.exists(), index=False)
                r = rows[0]
                print(f"{j['param']:14s} low_rank={j['low_rank']!s:5s} {j['indicator']:6s}: {r['seconds']}s "
                      f"rhat_max {r['rhat_max']:.3f} ess_min {r['ess_min']:.0f} div {r['divergences']}", flush=True)
            except Exception as e:  # noqa: BLE001
                print("FAILED", j, repr(e)[:300], flush=True)
