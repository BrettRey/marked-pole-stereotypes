# D1c longer pilot: both replicates pass
<!-- SUMMARY: Approved two-replicate baseline rerun passed every convergence gate with 2,000 retained draws per chain; 55.4 minutes; no grid, further retry, commit or push · status: complete · updated: 2026-10-10 -->

Both baseline replicates passed the unchanged convergence gate. Increasing the fixed sampling budget from 500 to 2,000 retained draws per chain resolved the observed R-hat failures in these two replicates. The approved pilot step is complete. The wider D1c design assessment remains unfinished.

## Run and verification

Brett approved this rerun on 2026-10-10. The amendment was recorded in `scripts/d1c/README.md` and `DECISIONS.md` before launch. The command was `.venv/bin/python -u scripts/d1c/d1c.py pilot`; run ID `20261010T101037462787Z`. Total elapsed time was 55.4 minutes.

The two UWA-like baseline replicates used null H2, joint feedback, omitted register and coefficient prior SD 1. Each used four chains, 1,000 warmup steps and 2,000 retained draws per chain, target acceptance .95, one worker and one sampler core. Models, priors, data and fit seeds, and diagnostic thresholds were unchanged. All data were artificial design data; no empirical outcomes were opened.

The source, prospective specification, analysis plan and compiler hashes matched their launch values at completion, before the post-run README entry. Package versions, cell, seeds and generating truths match the earlier run. The eight fit rows, four aggregate rows and two status rows agree. Both complete trace checkpoints are retained locally and checksummed; no D1c process remains running.

## Diagnostics

The gate requires finite diagnostics, R-hat at most 1.01, bulk and tail ESS at least 100, and no divergences for every sampled variable and derived contrast. Diagnostics use all 8,000 retained draws per replicate. Minimum ESS below means the minimum across bulk and tail checks.

| Replicate (CSV ID) | Earlier parameter R-hat | Current parameter R-hat | Worst variable | Minimum parameter ESS | Divergences | Contrast R-hat | Contrast ESS | Result |
|---|---:|---:|---|---:|---:|---:|---:|---|
| 1 (0) | 1.0434 | 1.0062 | `item_sd` | 778.0 | 0 | 1.0007 | 4001.2 | Passed |
| 2 (1) | 1.0204 | 1.0067 | `content_raw` | 910.9 | 0 | 1.0011 | 3710.6 | Passed |

`item_sd` is the shared item-effect standard deviation; `content_raw` contains standardized group-by-word effects. `content_sd` has the lowest parameter ESS in both replicates. Both fits now enter the convergence-selected summaries; the earlier failed fits remain preserved as separate records.

| Replicate | Compilation (seconds) | Sampling (minutes) | Total (minutes) |
|---|---:|---:|---:|
| 1 | 4.7 | 23.0 | 26.4 |
| 2 | 0.0 | 25.3 | 28.9 |

The second replicate reused the compiled graph. These timings describe this baseline cell under the observed machine load; they do not establish timings for other variants.

## Recovery check

All eight 90% intervals contain their generating truths. Point recovery remains uneven: H1 in replicate 1 and H2 and conditional b_z in replicate 2 are visibly displaced from truth. The estimates and intervals below retain the existing 100-draw summary subsample. Passing convergence establishes computational adequacy under the specified checks, not calibrated coverage or uniformly accurate point estimates.

| Replicate | Estimand | Generating truth | Posterior mean | 90% interval |
|---|---|---:|---:|---|
| 1 | H2 prevalence bridge | 0.000 | 0.010 | [-0.184, 0.251] |
| 1 | H1, usage fixed | -0.013 | -0.354 | [-0.854, 0.082] |
| 1 | Conditional b_z | -0.109 | -0.106 | [-0.345, 0.199] |
| 1 | Marking probability difference | -0.049 | -0.057 | [-0.091, -0.018] |
| 2 | H2 prevalence bridge | 0.000 | 0.128 | [-0.080, 0.308] |
| 2 | H1, usage fixed | -0.007 | -0.028 | [-0.562, 0.381] |
| 2 | Conditional b_z | -0.124 | 0.039 | [-0.230, 0.269] |
| 2 | Marking probability difference | -0.046 | -0.030 | [-0.065, 0.012] |

Two replicates cannot establish coverage, bias or false-support rates. The pilot supplies no scientific conclusion about stereotypes and no D1 indicator verdict. Other designs, feedback variants and stress scenarios remain untested by this run. Any broader D1c work is a separate scope decision; no grid, variant timing run or additional retry was launched. Nothing was staged, committed or pushed.

## Records

- [Fits](pilot-20261010T101037462787Z-fits.csv), [aggregate summary](pilot-20261010T101037462787Z-summary.csv), [statuses](pilot-20261010T101037462787Z-failures.csv).
- [Run configuration, versions and diagnostics](../../logs/d1c-20261010T101037462787Z.json).
- [Prospective launch record and source hashes](../../logs/d1c-pilot-launch-20261010T101036Z.json).
- [Completion verification and trace checksums](../../logs/d1c-pilot-completion-20261010.json).
- [Console output](../../logs/d1c-pilot-20261010T101036Z-stdout.txt).
- [Earlier pilot and approved recommendation](PILOT-SUMMARY-2026-10-09.md).

The two new traces are `.cache/d1c/traces/trace-fa679ed1d11f48cb-4202202426.pickle` and `.cache/d1c/traces/trace-fa679ed1d11f48cb-283345801.pickle`, ignored by git. The earlier traces are also preserved.
