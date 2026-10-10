# Assess what the available data can tell us

Reviewed in Roughdraft without amendments, 2026-10-10. Brett has authorized
making statistical informativeness an explicit part of the design assessment.
This file sets out the implementation and the remaining inputs for replicated
model runs.

## The decision this work supports

Before treating the empirical design as informative, establish how precisely
it can estimate the registered effects and how reliably its intervals
describe uncertainty. Report performance across effect sizes and assumptions.
Keep substantive benchmarks unset, as agreed. A conventional power estimate
can accompany this assessment when its detection rule is stated explicitly;
there is no new requirement to pass an arbitrary power threshold.

## Implement now

Add a separate `scripts/design_assessment/` module with a specification,
input manifest, reporting command and simulation-budget calculator. Link it
from the analysis plan's existing design-check requirement and update
`STATUS.md` and `DECISIONS.md`. Keep the active component queues on their
published source so that their remaining fits can finish.

The reporting command will read completed simulation records, distinguish
independent generated datasets from fitted specifications, and reject
conditional cut components as full study replications. Its first integration
check can use the existing completed D1c pilots, explicitly labelled as
engineering examples with insufficient replication for calibration.

Implement and test the statistical summaries using small analytical fixtures.
These fixtures test arithmetic and record handling; they are not simulated
research findings. The new command will not start model fits.

## Report these quantities

For each dataset, estimand, generating effect and fitted specification:

- Estimated bias, RMSE and the distribution of 50% and 90% interval widths.
- Coverage of those intervals, with uncertainty across independent simulated
  datasets.
- Wrong-sign estimates and, separately, exaggerated estimates among results
  whose 90% intervals exclude zero. Show the conditioning denominator.
- The probability that a 90% interval excludes zero in the correct direction
  at each nonzero generating effect. Label this as the detection rule being
  evaluated, not as the criterion for substantive support.
- At zero truth, the probability that the interval excludes zero in either
  direction. Report this separately from detection at nonzero truth.
- Attempted datasets, completed fits, diagnostic failures and execution
  failures. Conditional-on-convergence summaries must say so. Also report
  successful detection per attempted dataset, so failed fits cannot disappear
  from the assessment of practical performance.

Report Monte Carlo uncertainty for every estimated performance quantity.
For event rates, show event counts, denominators and exact binomial intervals;
zero observed errors must not imply known zero risk. A single replicate
cannot provide an empirical standard error for a continuous summary.
Comparisons between specifications fitted to the same generated data remain
paired. Sampler effective sample size is not the replication count.

Historical simulation benchmarks remain in their original records. The new
primary report will not convert them into substantive support cutoffs.

## Inputs that must be fixed before empirical-design calibration

The manifest will distinguish sourced and frozen inputs, explicit sensitivity
assumptions, and unresolved inputs. It must not silently fill unresolved
fields with the present 400-word/40%-coverage placeholders.

| Input | What must be recorded |
|---|---|
| Vocabulary | Frozen eligibility rule, denominator size and version/hash |
| Participant structure | Participant–group incidence and response budgets for each dataset, preserving repeated responses |
| Measurement coverage | Which eligible words have which instruments, including overlap and missingness |
| Measurement assumptions | Reliability, shared model-judge error, bias and transport assumptions; sensitivity values where unknown |
| Estimands | Their events, denominators and averaging populations; perceived display and prevalence kept distinct |
| Effects | A justified range of generating effects on each estimand's own scale, with the null included |
| Computation | Model version, independent dataset seeds, sampler settings and accuracy of the finite cut approximation |

Freezing metadata must respect the existing outcome-data boundary. If required
structure cannot be established without opening outcomes, resolve and record
that access before using it. Missing source information remains missing.

For H2 and exploratory H1, plan separate effect curves rather than claiming
that varying H2 supplies an H1 power curve. Secondary marking and conditional
coefficient results retain their own known simulated truths. L1/L2 belong
with the existing D2b assessment after the lexical frame is frozen; this work
will record that dependency rather than silently treating D1c as their check.

## Choose replication from precision and cost together

The budget calculator will convert a requested Monte Carlo standard error
into an independent-dataset count, then combine that count with observed
fit timings and the proposed cell list. It will separate worker-hours,
elapsed time under stated concurrency, and estimated HF charges.

For an event rate, the standard error is `sqrt(p(1-p)/R)`. The conservative
bound is `0.5/sqrt(R)`. These are calculations, not performance results:

| Independent datasets per cell | Maximum rate SE | Rate SE if the true rate is .90 |
|---:|---:|---:|
| 25 | 10 percentage points | 6 percentage points |
| 100 | 5 percentage points | 3 percentage points |
| 400 | 2.5 percentage points | 1.5 percentage points |

These counts are budget comparisons, not authorization to launch them.
Selective error rates may have much smaller denominators than the total
replication count. Continuous summaries also need their own uncertainty
estimates; the table alone does not determine their precision.

Before a calibration launch, freeze the actual cell list, replication count,
precision rationale and cost ceiling in a versioned run manifest. If the
complete assessment is unaffordable, narrow the scientific question
prospectively or report the unresolved uncertainty. Do not substitute one
replicate across many cells for repeated assessment of a defined design.

## Completion criteria

The immediate deliverable is tested reporting and budgeting code, a populated
registry of known and missing inputs, and an explicit design-assessment
requirement in the plan. That completes the infrastructure stage, not the
power assessment itself. The latter requires the frozen inputs and replicated
fits, and must be described as pending until those results exist.

Relevant methodological sources: [Gelman and Carlin (2014, pp. 642–644)](https://sites.stat.columbia.edu/gelman/research/published/retropower_final.pdf)
on effect-size-dependent design analysis, sign errors and exaggeration; and
[Morris, White and Crowther (2019)](https://doi.org/10.1002/sim.8086)
on simulation aims, performance measures and Monte Carlo uncertainty.
