# Part 8: draft completion text for the analysis plan
<!-- SUMMARY: Draft completion of the five unwritten plan sections, incorporating Brett's continuous-reporting direction and identifying remaining analyst work; analysis_plan.md unchanged · status: draft · updated: 2026-10-10 -->

This draft assembles the plan's unfinished sections in one place. It draws
on `analysis_plan.md` and `DECISIONS.md` through 2026-10-10, including Brett's
direction to report estimated effect size, uncertainty and changes under
different assumptions. The reporting section below replaces the earlier
threshold-based proposal. It does not require substantive benchmarks.

The plan is not yet FIXED. **STILL OPEN** identifies specification work for
the analyst, not a checklist or file-merging task for Brett. **PROPOSED**
marks implementation details that have not been adopted. The analyst will
prepare the coherent plan and explain any remaining scientific decisions
in plain language before requesting Brett's judgment.

## Data and exclusions

UWA Study 2 and Nicolas et al. provide separate confirmatory production
tests, with dataset-specific effects. Ingendahl et al.'s Irish English
subsample is analysed separately. UWA Study 1 supplies response-normalization
calibration only. It does not select the candidate vocabulary, outcomes or
model specification. Production observations retain participant and group
identifiers and each task's fixed response budget.

The candidate vocabulary comprises Anderson's list plus eligible
person-descriptive adjectives from the Warriner norms. Sense-level rules
for participles, ambiguous adjectives and exclusions are frozen independently
of commonness coverage. Words without commonness measurements remain in
the competing vocabulary. Responses outside the eligible vocabulary form
an explicit outcome category. Anderson-only, expanded-list and norm-covered
analyses define separate target populations and competing vocabularies.

Response-normalization rules are frozen after Study 1 calibration. Strict
and lenient versions are specified in advance. Ambiguous responses are
adjudicated blind to rarity and the hypotheses. Syntactic negation,
intensifiers and compounds retain their distinctions; syntactic negation
is not converted into affixal negation. Exclusions are tabulated by dataset,
group and valence.

Human word-rating sources keep their own constructs: Ziano's perceived
display frequency, Rothbart and Park's expected frequency in the population,
and Norman's applicability to self or chosen acquaintances. Source-specific
associations precede restricted bridge analyses on overlapping words.
Calibration to one source does not establish actual prevalence or transport
to another population. ESCS endorsement is auxiliary and is not a prevalence
indicator. Koch's data have explicit author permission for research use and
publication of derived summaries (email of 2026-10-09, supplied by Brett on
2026-10-10), with citation requested. Cite the paper and OSF project; record
the permission and file-level provenance when retrieving the data. This is
not a recorded CC BY licence. Their measurements still require source-specific
construct and coverage checks before entering a bridge model.

The two Ziano screening specifications are retained: the authors' code as
written and their stated exclusions. Each uses an ordinal respondent-level
model with rater effects. Model judges are calibrated within demonstrated
support. The expanded vocabulary outside that support is labelled
model-judged and reported as a separate population. Description-based
absolute commonness has its own bias bounds and no assumed human-scale
bridge.

For L1, the root/negation frame is detected by rule, hand-checked and frozen
before commonness is collected or joined. Both members must be eligible
person-descriptive adjectives. Uninterpretable pairs remain in an exclusions
table. Words without an eligible extant root are described separately;
exploratory comparisons with an opposite chosen by a frozen rule are not
pooled into the primary frame. Participial pairs are also reported separately.

The main session saw all Rothbart and Park Appendix values before the
frame was frozen. L1 and the word-level marking analysis are therefore
reported with and without the relevant words, and neither presents the
remainder as untouched confirmation. Norman extraction values remain
separate from morphology until the frame is frozen, subject to the
documented extraction-pilot exception.

**STILL OPEN:** verify and name every production data release and its
licence; freeze the vocabulary and dictionary senses; list normalization
rules, source-specific exclusions and missing-data handling; specify support
diagnostics and the consequences of failing them. The plan's settled
eligibility principles do not supply those operational details.

## Variables

Valence, formal negation, order markedness and scalar polarity are separate
quantities. Formal negation is the morphological variable for H1 and the
lexical models. Contrary prefixes, *non-* and privative *-less* are coded
separately. Contrary prefixes are partially pooled within their class.
Record base valence, morphological process, sense, reading and root
availability; hand-check apparent affixes. Negated words without extant
roots form their own category and enter word-level sensitivity analyses
with and without that category.

Within-valence commonness has a fixed reference scale and orientation:
higher values mean more common. Human-supported display frequency,
model-judged prevalence, source-specific applicability and bridge-dependent
prevalence effects retain their construct labels. Scaling is not recomputed
within each vocabulary subset. Indicator models distinguish sampling error
from shared familiarity, valence and morphological bias. Known item-level
standard errors constrain sampling error, not systematic misjudgment.

Warriner valence enters with uncertainty in the mean. Stakes is latent and
uses arousal where the valence adjustment would make extremity redundant.
Its interpretation and measurement reliability remain assumptions to be
checked and varied. Register comprises distinct origin, formality and
familiarity measures. These are not combined into one undifferentiated
control.

Act type is coded by several model families from morphology-free
descriptions. The measurement model allows ambiguity, correlated family
errors and shared misclassification, including dependence on negation.
Word-based act-type coding is a secondary specification diagnosing lexical
cueing. Coding agreement measures consistency and does not validate a true
act type. Adjusted and unadjusted contrasts use the same target population.

Word frequency has a latent log usage rate and an observed corpus count.
The production model uses the latent rate. It does not insert the log of
the observed count as if measured without error. Corpus size defines the
exposure. An additional count-dispersion parameter requires information
that separates it from between-word variation in usage.

**STILL OPEN:** name the register sources and coding versions; freeze
reference scales, commonness endpoints, corpus release and exposure, and
the exact probability outcome for the word-level marking comparison.
Freeze the prompts, model versions, dictionary and sense rules before
judging. State how disputable readings and missing codes enter each fit.

## Models

The commonness module reuses the acceptometer's Stan measurement model
and validation machinery after checking its assumptions for commonness.
Its posterior draws feed the PyMC model. The joint model remains in PyMC,
which implements the linked measurement, lexical and production submodels
and the restricted-feedback alternatives. Measured uncertainty is propagated
within a model; unidentified bias and transport assumptions remain separate
sensitivity specifications.

Production uses categorical choices among the full eligible vocabulary and
the outside option, respecting the response budget. The model includes
group-by-word content, item variation and partially pooled group and
participant slopes. A participant intercept shared by every alternative
cancels in a choice model. Posterior predictive checks examine concentration,
zeros and between-group overlap. Participant dependence is retained in both
confirmatory datasets.

The corpus model is Poisson conditional on latent usage and corpus exposure.
Usage depends on commonness, stakes, valence and the other specified
predictors, with its own between-word residual. Formal negation is modelled
by morphological class. H1 compares pre-specified combinations of no
word-level controls, register, act type and both. Causal diagrams determine
what each adjusted comparison conditions on; coefficient movement is not
interpreted as bias removed.

L1 estimates the probability contrast for one comparison under the frozen
model-judge protocol, averaging over its panel. Process and finite-frame
contrasts are reported separately. The response model retains “about equal”
and records “can't say” handling. Reading-specific contrasts are estimated
where both pair types occur; pooled differences are separated from reading
composition. Description wording, pair and family variation are modelled,
with shared-error sensitivity specifications.

L2 uses a categorical outcome distinguishing simple forms, contrary
prefixes, *non-* and *-less*, with partial pooling within the contrary class
and varying intercepts for morphological family and semantic domain.
Checks compare negation shares by valence, affix counts and the informative
off-diagonal counts. Stakes and commonness overlap is checked before
interpreting their adjusted comparisons.

H2 averages production over marking and usage, holding the specified
competitors and other controls fixed. Conditional coefficients are
secondary. H1's held-fixed and integrated usage comparisons remain
different estimands. Word and morphological-family holdouts assess H1's
predictive contribution. Calibration steps are fitted within training
folds when assessing judges' incremental prediction of human commonness.

The joint and cut specifications state their factors and normalization
explicitly. In D1c, the cut is

\[
q(L,\theta_E,\theta_D)
=p(L,\theta_E\mid E)\,
p(\theta_D\mid C,M,Y,L),
\]

where L contains the upstream latents, E their measurements, C corpus
counts, M marking and Y production. Each downstream conditional is
normalized separately, so C, M and Y do not update L. An empirical model
must specify its own measurement factors and shared parameters; inserting
posterior means or stopping a gradient does not implement this distribution.

**STILL OPEN:** complete D1b/D1c and the required frame-specific design
checks; settle the indicator verdict; specify numerical priors, shared-bias
bounds, bridge models, admissible multiverse combinations, scoring rules,
predictive-check criteria, convergence budgets and retry rules. Simulation
placeholders are not empirical priors. The plan requires calibrated
identifying priors as sensitivity assumptions, not only wider generic priors.

## What would count against each hypothesis

**Reporting direction agreed by Brett, 2026-10-10:** report the estimated
size, its uncertainty, and how it changes under different assumptions.
For every estimand, lead with its estimate and uncertainty interval on the
stated scale. Give predictive probabilities where they make the size easier
to understand. State each probability's event, denominator, comparison and
averaging population. Keep the posterior and exceedance curves available.

Substantive benchmarks remain unset. The report does not classify findings
by whether an interval clears an analyst-chosen scientific cutoff. No such
choice is required before reporting. A future benchmark proposal would
need a reason grounded in the claim or a decision it informs. Simulation
test values and computational diagnostic limits retain their separate roles.

H2 predicts a negative production contrast as commonness increases. Report
the sizes that remain plausible, how much uncertainty remains about the
direction, and how the estimate moves under the stated measurement and
transport assumptions. Keep perceived-display and bridge-dependent
prevalence contrasts separate. H1 is exploratory: report its predictive
comparison and held-out contribution without presenting them as a test of
the common-cause mechanism.

L1 predicts that model judges are more likely to call the positive pole
rarer when that pole is negated. Report this probability difference and
its uncertainty under the frozen protocol, separately for the pair-generating
population and the frame's pairs. Word-level marking predicts lower
negation probability at higher commonness. Compare the word-based and
description-based estimates on the same vocabulary and endpoints, showing
both across the admissible bias and transport assumptions.

For each prediction, describe whether the estimated relationship follows
the predicted direction, is precisely concentrated near zero, spans a broad
range, or favours the opposite direction, using the estimates and posterior
uncertainty to make the description explicit. Do not turn those descriptions
into new undisclosed cutoffs. A failed overlap or measurement check limits
the interpretation even when the fitted interval is narrow.

Report every admissible specification in a fixed order, separately by
dataset, target population and estimand. Show changes in estimated size and
uncertainty directly. Within-model uncertainty and differences between
assumptions are distinct; their spread is not one posterior interval.
Specification counts are descriptive, not probabilities or weights.
Agreement among H2, L1 and L2 is not independent corroboration because they
share vocabulary and commonness instruments.

Strand A retains the conditional forward map. With no true group
differences, fresh-sample PPV is compared with the target group's share.
Valence and content consensus are reported under the specified sampling
structure: independent samples and overlapping samples from a small society
need not agree. Consensus is reported beside prevalence shifts and recovery.
Observed consensus is not inverted into an estimate of true differences.

**PROPOSED interval convention:** display the posterior median and
equal-tailed 50% and 90% intervals, accompanied by the posterior or
exceedance curve where useful. These intervals summarize uncertainty; they
are not pass/fail boundaries. This presentation choice remains distinct
from the agreed decision to leave substantive benchmarks unset.

**STILL OPEN:** specify overlap and measurement-adequacy checks and the
final strand A comparisons. A precisely estimated association cannot by
itself establish the proposed mechanism.

## Seeds and environment

Specifications and executable code are committed and pushed before model
runs. Each run records its root seed and deterministic seed allocation,
Python and package versions, command, sampler settings, code identity,
environment, elapsed time, convergence diagnostics and output paths.
Source inputs retain URL, access date, SHA-256 and licence in
`data/manifests/sources.csv`. Raw data and third-party PDFs remain outside
Git; shareable derived outputs retain provenance.

Fake-data design simulations are labelled as such and do not supply
research evidence. Failed fits and exceptions remain visible. Non-trivial
decisions are appended to `DECISIONS.md` when made. The final analysis plan
is committed as FIXED before any outcome model; any outcome exposure before
that point is documented as post hoc.

**PROPOSED operational detail:** use distinct deterministic seed streams
for generated data, fitting and predictive calculations; preserve identical
data across sensitivity specifications where the comparison permits it.
Record the complete ordered specification table before launch and save
completed-fit diagnostics incrementally, with checks against changed code
or settings on resumption. D1c's prospective grid runner implements this
recovery approach.

**STILL OPEN:** freeze empirical-analysis root seeds, package versions,
model-judge versions and prompts, the final ordered multiverse, and the
commonness-module handoff format. The two D1c pilots ran before their code
was committed under Brett's then-active overnight restriction; their launch
hashes and retrospective publication are preserved. Later commits must not
be described as prospective registration of those pilots.

## Source map for merging

| Draft section | Settled project text |
|---|---|
| Data and exclusions | `analysis_plan.md`: H2 details; Existing human data; Commonness judges; Model judges only; L1 frame |
| Variables | Variables; H1 details; Which rarity; Display frequency is not prevalence; L2 |
| Models | Proposed revisions; H2 details; H1 details; Multiverse; Commonness judges, engine; L1; L2 |
| What would count against | H2/L1/L2 estimands and predictions; settled strand A forward map; 2026-10-10 reporting decision in DECISIONS.md, which supersedes the earlier requirement to choose substantive cutoffs |
| Seeds and environment | Project rules; `HANDOFF-TO-CODEX.md`; dated D1c records and `DECISIONS.md` |

The draft leaves `analysis_plan.md` unchanged. Its later integration must
also reconcile the older threshold rules elsewhere in that file. Numerical
results, external factual claims and citations already in the plan retain
their existing source checks. The analyst handles that integration; Brett
does not need to reconcile the files.
