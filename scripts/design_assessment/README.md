# Design informativeness: reporting and compute planning

Implements the [reviewed plan](../../notes/design-informativeness-plan-2026-10-10.md).
This module assesses simulation records and previews resource requirements.
It does not generate empirical inputs, fit models or submit compute jobs.
Empirical-design calibration remains pending; `inputs.json` records the known
requirements and unresolved inputs without substituting provisional values.

## Reporting

The initial adapter accepts complete `scripts/d1c/d1c.py` pilot/run outputs:
the fits CSV, attempt-status CSV and matching JSON run log. It checks their
planned cell/replicate sets, statuses, seeds, diagnostics and complete
estimand records. Joint fits require one joint diagnostic record; cut fits
require the upstream fit and every downstream component. Independent
component exports and interrupted run records are rejected. Additional
record formats require an explicit adapter rather than inferred compatibility.
If every attempt ended in an execution exception and the original run wrote
no fits CSV, omit `--fits`; the failure-only assessment still reports every
planned attempt. Omitting fits from a run with completed results is rejected.

Example using the already completed longer pilot:

```bash
.venv/bin/python scripts/design_assessment/report.py \
  --fits results/d1c/pilot-20261010T101037462787Z-fits.csv \
  --statuses results/d1c/pilot-20261010T101037462787Z-failures.csv \
  --run-log logs/d1c-20261010T101037462787Z.json \
  --output results/design-assessment/pilot-integration-20261010
```

The output directory must be new. `assessment.json` contains all metrics,
input hashes, source hashes, environment versions and limitations; `REPORT.md`
provides an overview. Reports are explicitly engineering integration reports,
not completed empirical-design calibration. The two pilot datasets check the
adapter and arithmetic; they cannot establish the study's performance.

For each cell and estimand, compute bias, RMSE, 50%/90% coverage, and mean,
median, tenth and ninetieth percentiles of interval width. Detection means
that the equal-tailed 90% interval lies wholly on the side of zero containing
the nonzero truth. Null false exclusion means that this interval excludes
zero in either direction. These are evaluated statistical rules, not new
substantive-support thresholds. No benchmark-based support labels are added.

Wrong-sign estimates use nonzero truths. Selected sign errors and mean
absolute estimate/truth ratios condition on the 90% interval excluding zero;
their denominators are explicit. Truth magnitudes at most `1e-8` count as
numerical zero, matching the existing generator's root-solve tolerance use.
Every row's actual generated truth is used; varying H2 does not establish an
H1 power curve. Reports show the generated truth range within each cell.

Most performance measures condition on convergence and say so. Report
completed, converged, diagnostically failed and exceptional attempts beside
them. Usable correct detection per attempted dataset counts a failed fit as
no usable detection, not as a null scientific result. This measure's
denominator includes all attempts, including those without a generated truth
record; it is distinct from detection conditional on a known nonzero truth.

For event rates, use exact 95% Clopper–Pearson intervals. The plug-in binomial
Monte Carlo SE is left undefined when the observed rate is zero or one, or
there is only one observation. The interval still communicates uncertainty.
For means, use sample SD divided by the square root of the independent-dataset
count. For RMSE and width quantiles, use the SD of 2,000 bootstrap estimates
with fixed seed `20261010`, resampling whole datasets within the cell.
Continuous SEs are undefined for fewer than two usable datasets. Bootstrap
SEs can be unstable with small samples; a computed SE is not an adequacy claim.

Specifications sharing design, scenario, target, replicate and data seed are
paired for differences in bias and 90% width. Those comparisons use jointly
converged pairs and report unmatched counts. Multiple specifications and
posterior draws never increase a cell's independent-dataset denominator.

## Replication and cost preview

```bash
.venv/bin/python scripts/design_assessment/budget.py --mcse .025
.venv/bin/python scripts/design_assessment/budget.py --mcse .025 \
  --plan scripts/design_assessment/budget-example.json \
  --output results/design-assessment/budget-example-20261010.json
```

`--mcse` is a standard error in proportion units. The default rate `.5`
uses the worst-case binomial variance; `.025` therefore requires 400
independent datasets per assessed cell. `--rate .9` previews a specified
rate assumption instead. This precision applies to that event rate, not to
continuous summaries or a selected subset whose denominator may be smaller.

The optional JSON plan lists unique cell IDs, their assigned platforms and
sourced component timings. Each timing has a positive `count`, `seconds`
and `source`. Platform records specify `machines`, `workers_per_machine`,
`usd_per_machine_hour` and `timeout_hours`. The plan also states the remaining
authorized budget and must have `launch_authorized: false`.

The example prices a hypothetical repetition of the existing single UWA-like
cut on HF. It is not an approved cell list and uses provisional design inputs.
It combines the saved cloud upstream preparation time with the completed HF
downstream trial time. The former is not a matched HF timing, and two-worker
throughput is still being measured. The assumptions stay visible in the file.

The calculator reports total worker-hours, ideal elapsed hours under perfect
load balancing, estimated compute charges, and reservation at full provider
timeouts. Session counts assume resumable work across timeouts. Startup,
dependencies, transfer costs, contention and failures can increase the
projection. No affordable preview authorizes a launch, and no precision target
is silently relaxed to make an expensive plan appear affordable.

## Checks and methodological basis

```bash
.venv/bin/python -m unittest discover -s scripts/design_assessment -p 'test_*.py'
```

Tests use analytical fixtures, including exact boundary probabilities,
failure denominators, paired comparisons and incomplete-cut rejection.
Fixtures are not research results. Existing scientific/sampler files are
unchanged by this module.

See [Gelman and Carlin (2014, pp. 642–644)](https://sites.stat.columbia.edu/gelman/research/published/retropower_final.pdf)
for design analysis beyond power and
[Morris, White and Crowther (2019)](https://doi.org/10.1002/sim.8086)
for simulation performance measures and Monte Carlo uncertainty.
