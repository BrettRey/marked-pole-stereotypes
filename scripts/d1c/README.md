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

## Longer pilot result (2026-10-10)

The approved rerun (`20261010T101037462787Z`) completed in 55.4 minutes. Both
replicates passed every unchanged parameter and contrast diagnostic gate:
maximum parameter R-hat 1.00624 and 1.00671, minimum ESS 778.0 and 910.9,
and zero divergences. All eight 90% intervals contain their generating
truths, though point recovery is uneven. Two replicates do not establish
coverage or validate the wider design. Full results and limitations are in
`results/d1c/PILOT-SUMMARY-2026-10-10.md`.

Source hashes matched at completion before this result entry was appended.
Both traces and earlier failed runs are preserved. The approved pilot step
is complete; no further retry, grid or variant-wide timing was launched,
and nothing was staged, committed or pushed.

## Approved variant timing (2026-10-10; prospective record)

Brett approved `notes/d1c-timing-plan-2026-10-10.md` in Roughdraft before
launch. Run the existing `time_variants.py` once, unchanged: twelve fits
cross two designs, register omitted or measured at reliability .8, and
upstream, downstream and joint components. Use baseline artificial data,
null H2, prior SD 1, existing seeds, four chains, 1,000 warmup and 2,000
retained draws per chain, target acceptance .95, sequential fits and one
sampler core. Retain all existing diagnostic gates; no automatic retries.

The downstream timing conditions on one upstream draw; it is not a full
eight-component cut validation. Preserve every diagnostic failure and
exception. The script's 40-replicate, three-worker grid calculation is only
a hypothetical extrapolation, not an approved grid size or launch. Its
reliability, prior and scenario timing approximations must be reported.
Source hashes, package versions, command and environment are recorded
before launch. No commit or push; no empirical outcomes are used.

## Overnight limits lifted (2026-10-10)

Brett lifted the no-commit/no-push instruction and authorized continuing lane S
under `HANDOFF-TO-CODEX.md`: finish variant timing, commit and push, then run
the D1c grid. Sampler-setting changes may be handled and recorded without
further approval; a required change to the design itself must be raised with
Brett. This supersedes the earlier scope restrictions, which remain above
as the historical record of each launch.

At Brett's request, commit `25e368a` first restored exactly the second pilot's
launch-time README. Its SHA-256 matches
`logs/d1c-pilot-launch-20261010T101036Z.json`. Both pilots ran before their
code was committed. The retrospective commit preserves the documented
launch text; it does not claim prospective Git registration. The current
code, results and records follow in a separate commit. The variant-timing
run continues unchanged while this publication record is added.

## Grid recovery (2026-10-10; prospective implementation)

`grid.py` runs the existing `d1c.fit` function and saves each completed cell
and replicate, including its estimates and detailed diagnostics, before
starting more work. Completed records live under `.cache/d1c/grid/`; the
inspectable CSVs and JSON progress log are rebuilt after every completion.
A completed diagnostic failure or ordinary worker exception is retained
and skipped on resumption. An interrupted job without a completion record
is repeated with its original seeds. Partial cut jobs restart as whole jobs;
this implementation doesn't save individual cut components.

The runner checks the source hashes, package versions, Python, platform,
full job list and sampler configuration when resuming. It refuses changed
specifications, damaged records and a second writer. Sampler code and this
README must be committed, and local HEAD must match origin HEAD, before
launch. Runtime outputs can change without invalidating resumption. A lost
worker stops the pool and leaves unfinished jobs pending; it doesn't label
the remaining grid as failed.

All original cells and seeds are retained. Scheduling goes by replicate,
then the original cell order, so the first replicate covers the multiverse
before the second starts. The command is
`python scripts/d1c/grid.py start --reps R --draws D --tune T --workers W`;
resumption uses `python scripts/d1c/grid.py resume RUNSTAMP --workers W`.
The run's sampler budgets persist on resumption. Defaults currently match
the longer pilot. This implementation entry selects neither the final
sampler budgets nor the replication count; those follow completed timing.

Twelve tests pass without fitting a model: completed-job recovery, failed-fit
retention, changed settings, interrupted writes, record corruption, duplicate
writers, lost workers, early worker termination, nonfinite failed diagnostics,
worker sampler budgets, full cell coverage and rebuilding partial progress
outputs. The timing script and `d1c.py` are
unchanged. No grid has been launched by this entry.

## Grid contrast summaries (2026-10-10; prospective setting)

The grid runner uses every retained contrast draw for posterior means,
intervals and probabilities. `posterior_contrasts()` already calculates
these draws for diagnostics; the earlier 100-draw summary subsample discards
most of that calculation. Set `POST_DRAWS = CHAINS * DRAWS` in each grid
worker. The model, eight cut components, equal component weights, data and
sampling seeds, and diagnostic criteria are unchanged. The initial cut
draw selections occur before contrast subsampling, so they are unchanged
too. The completed pilots and running benchmark retain their original
100-draw summaries. This is a prospective Monte Carlo setting for the grid.

## Bounded-memory diagnostics (2026-10-10; prospective implementation)

The timing process reached a 5.3 GB peak physical footprint at 2,000
retained draws per chain (`vmmap`, 2026-10-10 15:01 UTC). Before increasing
the grid's sampler budget, prepare `diagnostic_chunks.py`: calculate the
same rank-normalized R-hat, bulk ESS and tail ESS in batches of at most
256 scalar parameters. Each batch retains every chain and draw. Report the
same extrema and worst variable names, with the same finite-value,
divergence and numerical gates. This changes temporary memory use, not
the diagnostic definitions or model.

Four equivalence tests compare against the original whole-variable ArviZ
calculation at batch sizes 1, 6 and 256, including scalar/vector/matrix
parameters, noncontiguous arrays, reordered dimensions, constants and
divergences. Results match to tolerance 1e-12. No model is fitted by these
tests. Source hashes, versions and the memory observation are recorded in
`logs/d1c-diagnostic-equivalence-20261010.json`. The helper is not imported
by the running timing job; integration follows its completion.

## Completed timing and initial grid (2026-10-10; prospective launch specification)

The twelve-fit timing run `20261010T112137001353Z` is complete. Eight fits
passed the parameter gates. R-hat failures occurred in UWA measured-register
upstream and downstream fits, and Nicolas measured-register upstream and
joint fits. All eight contrast checks passed; every fit had zero divergences.
A passing downstream timing does not validate a cut whose upstream fit
failed. These are baseline timings at prior SD 1 and register reliability
.8; a downstream timing covers one conditional fit, not the full cut.
Source, seed and package verification is recorded in
`logs/d1c-timing-completion-20261010.json`.

Brett chose local execution and is reserving prospective Alliance access
for later work. Select **one initial replicate of all 240 registered cells**
as an engineering sweep. The earlier 40-replicate calculation was a
hypothetical resource estimate, not a frozen replication count. This first
sweep checks execution, diagnostics and recovery across the complete cell
set. One replicate per cell cannot establish coverage, sign-error rates,
false-support rates or Monte Carlo bias. The existing summary format is
retained for reproducibility, but its single-replicate proportions and zero
plug-in binomial SEs must not be treated as calibration evidence. D1c remains
incomplete pending adequate replication and checks at the frozen empirical
sizes and measurement coverage.

Freeze four chains, **4,000 retained draws per chain for joint and downstream
fits, 8,000 for upstream fits, and 2,000 warmup steps for every fit**. Keep
target acceptance .95, the eight equally weighted cut components, one
sampler core per worker, three workers, all priors and diagnostic gates,
and the original seed derivation. The larger upstream posterior changes
the sampled latent bank; it does not change the cut distribution or weighting
rule. All retained production contrasts enter posterior summaries. No
automatic retries or within-run changes to sampler settings.

The tested batched parameter diagnostics are now integrated. Each completed
conditional trace is released after its scalar contrasts are extracted,
before allocating the next conditional trace. The generating model,
likelihood, estimands, cells, seeds, contrast calculation and summary formulas
are unchanged; the AST comparison is in
`logs/d1c-grid-design-preservation-20261010.json`. Seventeen tests pass,
including budget routing through the actual sampling entry point with a
mocked backend. No model fits were performed by those tests.

Launch only after committing and pushing this specification and code:

```bash
.venv/bin/python -u scripts/d1c/grid.py start --reps 1 --draws 4000 --upstream-draws 8000 --tune 2000 --workers 3
```

Allow roughly **18 days** at three effective worker cores, extrapolating the
measured timings to the larger budgets. This is not a measured concurrent
grid speed or a completion deadline. Timing at reliability .5 is approximated
by .8, prior SD 2.5 by 1, and other scenarios by baseline. Memory batching
has been checked for numerical equivalence, but its end-to-end memory peak
and runtime have not yet been measured in the grid. Interrupted unfinished
cut jobs restart as whole jobs; completed jobs, including failures, survive
resumption.

## Grid stopped by Brett (2026-10-10)

Brett stopped the initial grid after questioning the roughly 18-day projected
cost. Run `20261010T161109492336Z` ended at 16:28:32 UTC after 17.4 minutes,
with zero completed cells. The runner and its three workers are stopped;
the saved state is `interrupted`, and the unfinished fits are not diagnostic
failures. Preserve all records. This instruction supersedes the earlier grid
launch authorization: do not resume or launch a replacement without a newly
agreed resource scope. D1c calibration remains incomplete.

## Component recovery and Claude-cloud benchmark (2026-10-10; prospective)

Brett authorized this next step with “do it” after the proposal to add
component checkpoints and run one bounded D1c component in Claude cloud.
The stopped full local grid stays stopped. This authorization covers the
single benchmark below; it does not restart the full grid or authorize
unbounded cloud batches.

Save each completed upstream, downstream and joint component separately.
Upstream recovery retains the exact eight selected latent draws, their
indices, diagnostics and random-generator state. Downstream/joint recovery
retains all scalar contrast draws, diagnostics and the subsequent generator
state. A component is complete only after its archive and checksum-bearing
record are atomically published. Resumption checks the specification and
hashes, preserves completed diagnostic failures and skips completed components.
It never silently substitutes new latent draws. An interruption can still
lose the active component; partial sampler trajectories are not resumed.
Each saved component also gets an immediately readable progress summary.
A partial cut is labelled partial, never a completed eight-component estimate.

The cloud benchmark uses the original baseline UWA-like cut cell at null H2,
measured register reliability .8 and prior SD 1, replicate 0 (cell 10).
Generate the same artificial data with the existing seed derivation. Fit the
upstream module with 8,000 retained draws per chain and retain its eight
selected latent draws; then fit only downstream component 0 with 4,000
retained draws per chain. Both use four chains, 2,000 warmup, target acceptance
.95 and one sampler core. Keep all 16,000 production contrasts. All models,
priors, estimands and diagnostic gates stay unchanged. A failed diagnostic
is retained and reported. It does not trigger a retry. No empirical data enter.

Stop after the one downstream component finishes, with one environment setup
attempt and no automatic retries. After Brett questioned the proposed timeout,
remove the analyst-chosen four-hour cutoff: it could discard useful work while
providing no credit-spend guarantee. The cloud session
must export the completed component records and compact scalar/latent archives
on its dedicated branch after each completion, plus a final report. These
are our artificial-data calculation outputs, not third-party raw datasets or
full model traces. Large-scale archival storage is a later resource decision.

Record wall time, process memory, the container memory limit when available,
Python/packages, code identity, seeds, sampler settings, and all diagnostics.
Record the reported cloud-credit balance before and after when the account
UI exposes it; if unavailable, say so. The last user-reported balance is $216.
There is no verified programmatic dollar cap for Claude cloud. Use one
cloud session and sparse supervision. Do not launch additional sessions or
continue after this benchmark. Commit and push all executable changes before
it runs. Unit tests use fixtures and do not fit models locally.
