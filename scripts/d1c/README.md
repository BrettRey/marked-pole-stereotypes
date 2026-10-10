# D1c: categorical production design simulation

This is a prospective specification. No D1c results are assumed here. Commit
the specification and code before running; results inform the plan before it
is FIXED. Simulated data evaluates a design, never supplies research evidence
or replaces unavailable source data. All numerical design choices below are
placeholders **[ours]**; none estimates a property of the actual datasets.

## Design and reporting order

Fit UWA-like and Nicolas-like designs separately: respectively 40 **[ours]**
and 43 **[ours]** groups, with 12 **[ours]** participants answering every group,
giving one and six responses per participant-group. Those response budgets
match the task descriptions; group counts and the complete crossing remain
placeholder designs. The vocabulary has 400 **[ours]** eligible words plus
one explicit outside category. Independent commonness measurements cover
40% **[ours]** of words, chosen at random, with reliability .8 **[ours]**.
Eligibility and measurement coverage are different: uncovered words remain
in the competing vocabulary.

The fixed scenario order is baseline, indicator valence bias, register,
display divergence, and differential register error. Each is crossed with
null and threshold-sized *predictive* H2 truths, both datasets, joint and cut
feedback, omitted register and measured register at reliabilities .5 and
.8 **[ours]**, and coefficient prior SDs 1 and 2.5 **[ours]**. This is a
first-version restricted multiverse, not coverage of every plan dimension.
Both control reliabilities are fitted even in scenarios without confounding.
Specifications share generated data and proxy noise within a replicate.
Datasets, estimands, assumptions and priors stay separate in summaries.

## Generating model

All continuous predictors use fixed population scales. Higher z means greater
within-valence prevalence. Valence v, prevalence residual z and stakes s are
independent standard normals **[ours]**. Observed valence is v plus normal
error of SD .1 **[ours]**, and arousal is s plus error of SD 1 **[ours]**.
The fitted measurement model retains those known sampling errors.

Three distinct register dimensions h are generated, representing origin,
formality and familiarity. In register scenarios, each has mean
−.3z + .2v + .2s and independent residual SD sqrt(.83) **[ours]**.
Otherwise their mean is zero and residual SD is 1 **[ours]**. Origin is a
continuous propensity here, not an observed Latinate/native classification.
Register proxies are h plus paired normal errors of SD sqrt((1−r)/r)
**[ours]**. Differential-error stress additionally shifts every proxy by
.3m + .2v **[ours]**, which the fitted model deliberately does not know.

Marking is binary, with logit probability
−2 − .45z − v − .3s + .4 sum(h) in register scenarios **[ours]**.
The h loading is zero otherwise. This approximates pooled formal negation;
affix-specific H1 models and uncertain act-type coding are outside this
first-version design. Stakes supplies a correlated semantic control, not a
substitute for act type.

Latent log usage ell has mean
−4 + .4z + .3s + .3v − .3m − .25 sum(h), with the register term active only
in register scenarios, and its own residual SD .7 **[ours]**. Corpus counts
are Poisson(exp(ell) × 1,000) **[ours]**. Production uses latent ell,
never log observed counts. There is no extra negative-binomial dispersion.

The commonness indicator measures d + bias*v with known normal error;
bias is .2 normally and .8 in the valence-bias scenario **[ours]**.
Ordinarily d=z. In display divergence,
d=.5z+sqrt(.75)*q **[ours]**, representing frequent minority display versus
occasional majority display. This is a failed construct bridge, not a second
indicator of prevalence. The fitted model implicitly assumes the identity
bridge; results show its failure against both construct-specific truths.

Eligible-word utilities contain z, marking, ell, valence and stakes, plus
register in confounded scenarios. Accessibility is .3, valence −.5, stakes
.1 and direct marking zero **[ours]**. Register production loadings are
.25 each **[ours]**. Shared item effects have SD .2; group-by-word content
has SD .35; group and participant rarity and marking slopes have SD .1
**[ours]**. The outside utility is log(400 × 1.5) **[ours]**.

Conditional on those slopes, each participant-group gives multinomial
counts across the full vocabulary. This is exactly equivalent to independent
categorical draws with that response budget: no group aggregation removes
participant slopes. Nicolas-like responses can repeat a word. Conditional
independence and sampling with replacement are approximations; sequential
depletion, order and participant-group-specific dependence are not modelled.

## Estimands and truth

H2 is the mean log ratio of focal-word choice probabilities under z versus
z+1, averaging over the model's marking and usage distributions, over all
words, groups and the design's participants. Shift one focal word at a time;
hold its competitors, outside option, content effects, valence, stakes and
register fixed. This specifies competition and the target population.
It is a predictive association, not a causal effect.

Marking is integrated exactly over its two states; usage residuals use
five-point Gauss–Hermite quadrature **[ours]**. Each branch changes the focal
word's contribution to the denominator. This is not b_z or a sum of path
coefficients. A deterministic root solve sets generating b_z so prevalence
H2 equals 0 or −.10 **[ours]**, conditional on the generated design.
The latter is a design magnitude, not a justified substantive benchmark.

Also report H1's mean log probability ratio for m=1 versus m=0, with usage
held fixed; conditional b_z; and the marking probability difference for z+1.
Display truth shifts prevalence by .5 **[ours]**, preserving the residual
in the Gaussian prevalence-given-display bridge and holding other controls
fixed. Display and prevalence truths are reported separately, never pooled.
Fitted H2 against prevalence truth explicitly evaluates its identity bridge.

## Feedback, fitting and checks

Let L=(z,s,v,h), E denote commonness/arousal/valence/register measurements,
C corpus counts, M marking and Y production. The joint fit is proportional
to p(L,theta) p(E|L,theta) p(C,M,Y|L,theta).
The cut fit is
q(L,theta_E,theta_D)=p(L,theta_E|E)
×p(theta_D|C,M,Y,L).
Each downstream factor is normalized separately for its upstream draw.
Neither frequency, marking nor production updates L in the cut.
Merely stopping a gradient or inserting a plug-in mean is not this cut.
Omitted-register fits also omit register measurements from E.

Use eight upstream posterior draws **[ours]**, each followed by a conditional
downstream fit, and equally mix their contrasts. This is finite Monte Carlo
integration of the cut; increase it before relying on small uncertainty
differences. Compile once per shape/variant within each worker, with pm.Data,
freeze_model=False and with_data. Use four chains, 500 retained draws,
1,000 tuning steps, target acceptance .95 **[ours]**, with one sampler core
per job. Flag any divergence, R-hat above 1.01, bulk or tail ESS below 100,
or nonfinite diagnostics **[ours]**. Check every sampled variable and the
derived contrasts. All cut components must pass. No automatic retries.

CSV summaries report 50% and 90% coverage with binomial Monte Carlo SEs,
bias and its SE, width, unconditional and 90%-selected sign errors,
selected exaggeration ratios for nonzero truths, selected absolute bias,
and false meaningful support. Selection means the 90% interval excludes zero.
Benchmarks are −.10 for H2 and b_z, +.10 for H1, and −.02 for marking
**[ours]**. False support is conditional on a truth not beyond its benchmark.
Undefined quantities remain missing. Convergence failures and exceptions
have separate rows; bias summaries use converged fits and state that selection.

Run `python scripts/d1c/d1c.py pilot` for two replicates of one baseline
cell and timing, or `python scripts/d1c/d1c.py run --reps R --workers W`.
Outputs are timestamped CSVs under results/d1c and a JSON log under logs,
including seeds, configuration, package versions, git state and timing.
Pilot timing determines practical replication; two replicates cannot assess
coverage. Re-run at frozen sizes and coverage before treating D1c as complete.

## After pilot 1 (2026-10-09)

The first attempt failed during compilation; its failure table and JSON log
(`pilot-20261010T005646227622Z`) are debug records. The interrupted debug run
committed at `e44c1a9` centres the usage latent, computes the multinomial log
likelihood directly from logits, and reuses quadrature terms. Its equivalence
check is recorded in `logs/d1c-equivalence-20261009.json`. It also checks
trace completeness, checkpoints completed pilot traces, accepts ArviZ
DataTrees, and checks contrasts on all 2,000 retained draws.

Lane S resumes only the specified two-replicate pilot, at Brett's request on
2026-10-09, with no commit or push. Compiler scratch and caches move from
`logs/d1c-cache/` to the ignored `.cache/d1c/`, isolated from D2. The model,
seeds and sampler settings stay fixed. A dated launch record preserves the
local source hashes because this session won't publish its changes before
running. The grid and variant-wide timing run remain outside this session.

The resumed pilot (`20261010T014946903490Z`, 2026-10-09 Eastern time) completed
both replicates, including trace saving, diagnostics, contrasts and CSV/JSON
reporting. Both failed the registered R-hat gate: maxima 1.043 and 1.020.
Both had zero divergences and minimum ESS above 100; the derived contrasts
passed their diagnostics. No further fit was launched. The complete record
and proposed next run are in `results/d1c/PILOT-SUMMARY-2026-10-09.md`.

After completion, the two trace checkpoints moved from `results/d1c/` to
the ignored `.cache/d1c/traces/`, and the checkpoint path in `sample()` was
updated to match. Their contents were preserved. The launch record identifies
the exact source used for sampling; the completion verification records the
subsequent cache-path change. There was no model, prior, seed, sampler-budget
or diagnostic-threshold change, and nothing was committed or pushed by lane S.

## Approved longer pilot (2026-10-10; prospective amendment)

Brett approved the proposed next step on 2026-10-10, before this run was
launched: repeat exactly the same two baseline replicates with 2,000 retained
draws per chain instead of 500. Keep four chains, 1,000 warmup steps, target
acceptance .95, one worker and one sampler core, the model, priors, data and
fit seeds, and every diagnostic threshold unchanged. Parameter and contrast
diagnostics use all 8,000 retained draws per replicate; the existing
100-draw contrast-summary subsample is unchanged.

This is one fixed additional pilot, with no automatic further retry. The
source constant now records the approved budget; no grid or other variant
run is authorized. Preserve the earlier failed runs. The local launch record
will contain source hashes and environment details; Brett's instruction
not to commit or push remains in force. No empirical outcomes are used.
