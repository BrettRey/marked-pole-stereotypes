# D1c pilot: completed execution, convergence gate failed
<!-- SUMMARY: Lane S ran the two-replicate baseline pilot end to end; both fits fail R-hat, with zero divergences; a longer fixed pilot is proposed for approval; no lane-S commit or push · status: awaiting-approval · updated: 2026-10-09 -->

The pilot now completes data generation, compilation, four-chain sampling, trace saving, diagnostics, predictive contrasts and CSV/JSON reporting. Both replicates failed the pre-specified convergence gate. No further sampling or grid was launched. All inputs were artificial design data; no empirical outcome data were opened.

## Run and changes

- Command: `.venv/bin/python -u scripts/d1c/d1c.py pilot`.
- Run ID: `20261010T014946903490Z` (2026-10-09, Eastern time). Elapsed time: 49.9 minutes.
- Two replicates of the existing UWA-like baseline, null H2, joint feedback, omitted register, coefficient prior SD 1. Four chains per replicate; 1,000 warmup and 500 retained draws per chain; target acceptance .95; one worker and one sampler core.
- The only code changes were cache destinations: compiler scratch, Numba and Matplotlib caches now use `.cache/d1c/`; completed trace checkpoints moved to `.cache/d1c/traces/` after the run. Checkpoint hashes were verified before and after relocation.
- Model, priors, seeds and diagnostic thresholds were unchanged. The launch source hashes matched at completion, before the recorded checkpoint-path edit. The interrupted debug run supplied the substantive model and reporting fixes already present at session start.
- No commit, staging or push by lane S. No D1c grid, variant-wide timing, D1b, threshold examples or Part 8 work.

## Diagnostics

The gate requires every sampled variable and derived contrast to have R-hat at most 1.01, bulk and tail ESS at least 100, finite diagnostics and no divergences. The derived contrasts passing does not override a failed parameter check.

| Replicate (CSV ID) | Maximum parameter R-hat | Worst variable | Minimum parameter ESS | Divergences | Contrast R-hat | Contrast ESS | Result |
|---|---:|---|---:|---:|---:|---:|---|
| 1 (0) | 1.0434 | `item_sd` | 144.5 | 0 | 1.0024 | 894.7 | Failed |
| 2 (1) | 1.0204 | `content_raw` | 240.4 | 0 | 1.0050 | 1056.3 | Failed |

`item_sd` is the shared item-effect standard deviation; `content_raw` contains standardized group-by-word effects. In replicate 1, `content_sd` also had R-hat 1.032. The complete per-variable check for that replicate is in the diagnostic log below. The aggregate CSV correctly records zero converged fits and leaves convergence-selected performance estimates undefined.

| Replicate | Compilation (seconds) | Sampling (minutes) | Total (minutes) |
|---|---:|---:|---:|
| 1 | 25.3 | 32.9 | 34.3 |
| 2 | 0.0 | 14.5 | 15.5 |

The second replicate reused the compiled graph. Machine load changed during the run, so the timing difference is not an estimate of a model change.

## Estimates retained for debugging

These are the saved estimates from diagnostically failed fits, not accepted results. All eight 90% intervals contain their generating truths, but two replicates cannot establish coverage. Point recovery is uneven, including H1 in replicate 1 and conditional b_z in replicate 2.

| Replicate | Estimand | Generating truth | Posterior mean | 90% interval |
|---|---|---:|---:|---|
| 1 | H2 prevalence bridge | 0.000 | -0.012 | [-0.258, 0.255] |
| 1 | H1, usage fixed | -0.013 | -0.323 | [-0.809, 0.094] |
| 1 | Conditional b_z | -0.109 | -0.142 | [-0.435, 0.108] |
| 1 | Marking probability difference | -0.049 | -0.060 | [-0.099, -0.010] |
| 2 | H2 prevalence bridge | 0.000 | 0.107 | [-0.079, 0.315] |
| 2 | H1, usage fixed | -0.007 | 0.007 | [-0.382, 0.363] |
| 2 | Conditional b_z | -0.124 | 0.019 | [-0.215, 0.256] |
| 2 | Marking probability difference | -0.046 | -0.025 | [-0.067, 0.021] |

## Approval needed before another run

The README specifies “No automatic retries.” The remaining step changes the pre-specified sampling budget, rather than repairing a runtime exception. Brett asked lane S to stop and summarize when approval is needed.

**Recommendation, not implemented:** pre-specify one further two-replicate baseline pilot with **2,000 retained draws per chain**, keeping 1,000 warmup steps, four chains, target acceptance .95, both seeds, model, priors and all diagnostic thresholds unchanged. Record the amendment before launching it.

This doubles the transitions per chain and quadruples the retained trace size. Allow roughly 1–2½ hours under the observed range of machine load; this is a planning estimate, not a benchmark. There is no guarantee that it will pass, and no automatic subsequent retry.

No scientific conclusion or D1 indicator verdict follows from this pilot. The grid remains outside tonight’s scope.

## Records

- [Fits](pilot-20261010T014946903490Z-fits.csv), [summary](pilot-20261010T014946903490Z-summary.csv), [statuses](pilot-20261010T014946903490Z-failures.csv).
- [Run configuration, package versions and diagnostics](../../logs/d1c-20261010T014946903490Z.json).
- [Launch authorization, source hashes and environment](../../logs/d1c-pilot-launch-20261010T014927Z.json).
- [Completion and checkpoint relocation verification](../../logs/d1c-pilot-completion-20261009.json).
- [Replicate 1 parameter diagnostics](../../logs/d1c-pilot-rep0-diagnostics-20261009.json).
- [Console output](../../logs/d1c-pilot-20261009-lane-s-stdout.txt).
- Both complete traces remain locally in `.cache/d1c/traces/`, ignored by git. No D1c pilot process remains running.
