# D1c variant timing, 10 October 2026

All twelve scheduled component fits completed. Eight passed the parameter
diagnostic gates; four failed the R-hat limit of 1.01. All eight derived-contrast
checks passed and all twelve fits had zero divergences. No fit was retried.
These artificial-data timings assess computation and diagnostics, not the
substantive hypothesis or calibration across replicates.

The run used four chains, 2,000 retained draws and 1,000 warmup steps per
chain, target acceptance .95, and sequential one-core fits. Source hashes,
seeds and package versions matched the launch record at completion. The
README received dated authorization and prospective implementation additions;
the running model and timing code stayed unchanged.

| Design | Register | Component | Total minutes | Max R-hat | Min ESS | Parameter gates |
|---|---|---|---:|---:|---:|---|
| UWA | Omitted | upstream | 0.18 | 1.00389 | 2357.4 | Pass |
| UWA | Omitted | downstream | 27.20 | 1.00730 | 580.6 | Pass |
| UWA | Omitted | joint | 26.78 | 1.00592 | 851.3 | Pass |
| UWA | Measured (.8) | upstream | 0.33 | 1.02175 | 345.6 | Fail |
| UWA | Measured (.8) | downstream | 28.04 | 1.01368 | 611.3 | Fail |
| UWA | Measured (.8) | joint | 29.58 | 1.00733 | 482.9 | Pass |
| Nicolas | Omitted | upstream | 0.10 | 1.00374 | 2299.1 | Pass |
| Nicolas | Omitted | downstream | 27.74 | 1.00552 | 480.3 | Pass |
| Nicolas | Omitted | joint | 30.70 | 1.00575 | 478.2 | Pass |
| Nicolas | Measured (.8) | upstream | 0.33 | 1.02697 | 309.9 | Fail |
| Nicolas | Measured (.8) | downstream | 51.17 | 1.00563 | 579.0 | Pass |
| Nicolas | Measured (.8) | joint | 57.83 | 1.01156 | 395.8 | Fail |

The twelve recorded fits total 4.67 hours, including compilation,
diagnostics and contrast calculation. This sum excludes generating the four
baseline datasets between timed blocks. UWA measured upstream and Nicolas
measured upstream fail on `h_coef`; UWA measured downstream and Nicolas
measured joint fail on `content_sd`. Their ESS values exceed 100, so these
failures arise from R-hat. Passing scalar contrasts do not override parameter
failures.

Each downstream benchmark conditions on one upstream draw. It does not
validate the full cut, which uses eight separately normalized conditional
fits, and a passing downstream component cannot validate a failed upstream
fit. Timing covered baseline, prior SD 1 and measured reliability .8 only.

## Initial local grid

After timing completed, the prospective specification froze one replicate
of all 240 cells, three workers, four chains, 4,000 retained production draws,
8,000 retained upstream draws, 2,000 warmup, target acceptance .95 and eight
cut components. The original model, cells, priors, seeds, estimands and
diagnostic criteria are unchanged. All retained production contrasts enter
summaries. Completed failures are preserved; there are no automatic retries.

The new budget projects to **17.9 days** at three effective cores. This
is an extrapolation, not measured concurrent throughput or a deadline. It
scales production costs by two and upstream costs conservatively by four,
with compilation added separately. It assumes warm graph reuse, approximates
reliability .5 by .8 and prior SD 2.5 by 1, and uses baseline costs for other
scenarios. It includes the failed timing fits. End-to-end memory and speed
of the larger concurrent run remain unmeasured.

The original script's hypothetical 40-replicate estimate was 357.4 days at
the old sampler budget. Forty replicates were never the frozen launch count.
The initial one-replicate sweep is an execution and diagnostic check. It
cannot establish coverage, sign-error or false-support rates, or Monte Carlo
bias. Single-replicate fractions and zero plug-in binomial standard errors
in the inherited summary format are not calibration evidence. D1c remains
incomplete pending adequate replication and checks at frozen empirical sizes
and measurement coverage.

Seventeen tests passed for recovery, budget routing and diagnostic equivalence
without fitting models. The memory adjustment batches scalar parameter
diagnostics across the same complete chains and draws; numerical equivalence
was checked against the original ArviZ calculation. The AST comparison
confirms that the scientific functions and summary formulas are unchanged.

## Records

- [Timing CSV](timings-20261010T112137001353Z.csv)
- [Completion verification](../../logs/d1c-timing-completion-20261010.json)
- [Initial-grid calculation](../../logs/d1c-initial-grid-estimate-20261010.json)
- [Historical 40-replicate calculation](grid-time-20261010T112137001353Z.json)
- [Prospective grid specification](../../scripts/d1c/README.md)
- [Test output](../../logs/d1c-grid-recovery-tests-20261010.txt)
- [Design-preservation comparison](../../logs/d1c-grid-design-preservation-20261010.json)
