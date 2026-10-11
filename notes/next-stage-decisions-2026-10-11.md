# Next-stage decisions: reduce the simulation question

2026-10-11. **Adopted by Brett with the clarifications below, 2026-10-11.** Hugging Face remains the compute platform. All sixteen authorized baseline configurations are complete; estimated combined HF compute is $2.3845, not an invoice. Replicated D1c and full-vocabulary coding remain unlaunched and require their final input and resource specifications.

The adopted direction is to report joint and cut together, close the tested frequency-only pipeline for confirmatory use, replace the 240-cell D1c grid with eight decision-relevant cells, and defer replication until the empirical inputs are frozen. Directional reporting replaces substantive benchmarks. Norman extraction is the next implementation task.

The [bounded six-pair review is complete](lexical-six-pair-report-2026-10-11.md). Eleven calls returned and one timed out without retry. Five pairs retain candidate alignments; attentive/unattentive remains unresolved. Of sixteen saved proposals, twelve survive with restrictions, three remain unresolved and one is rejected. No exact complementary reading is established. The report traces every proposal and distinguishes interpretations from independent observations.

| Pair | Disposition of the saved proposals | Target retained |
|---|---|---|
| kind/unkind | Both retained with degree/feeling restrictions | Characteristic |
| friendly/unfriendly | Three retained; helpfulness/friendship alignment unresolved | Characteristic |
| patient/impatient | Endurance/irritability retained; eagerness rejected | Characteristic and state separately; relevant delay/trying situation explicit |
| happy/unhappy | Both experiential alignments retained; mutual exclusivity remains undetermined | State |
| attentive/inattentive | Four candidates retained; attention/care standards remain explicit | Characteristic and state separately; Claude timed out |
| attentive/unattentive | Both unresolved; bare negative cross-reference does not select the interpretation | No released target |

## 1. Report the joint–cut sensitivity directly

The completed baseline now supplies eight matched comparisons across four generated datasets. The dataset identifiers below are the generation seeds. H2's generating target and the generating conditional coefficient b_z are separate quantities. Each joint/cut pair shares its seed and all four generating estimands.

| Dataset seed | Design | H2 truth | b_z truth | Register reliability | Joint b_z | Cut b_z | Cut − joint | Cut / joint |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1207664664 | uwa | 0.00 | -0.10868 | 0.0 | -0.12672 | -0.08258 | 0.04414 | 0.652 |
| 1207664664 | uwa | 0.00 | -0.10868 | 0.8 | -0.11119 | -0.01913 | 0.09206 | 0.172 |
| 3684453537 | uwa | -0.10 | -0.23293 | 0.0 | -0.28370 | -0.16231 | 0.12139 | 0.572 |
| 3684453537 | uwa | -0.10 | -0.23293 | 0.8 | -0.29540 | -0.12360 | 0.17180 | 0.418 |
| 3095741988 | nicolas | 0.00 | -0.13726 | 0.0 | -0.08352 | -0.02008 | 0.06344 | 0.240 |
| 3095741988 | nicolas | 0.00 | -0.13726 | 0.8 | -0.07768 | -0.02130 | 0.05638 | 0.274 |
| 112380434 | nicolas | -0.10 | -0.24009 | 0.0 | -0.29735 | -0.09632 | 0.20103 | 0.324 |
| 112380434 | nicolas | -0.10 | -0.24009 | 0.8 | -0.30714 | -0.11516 | 0.19199 | 0.375 |

The eight cut means recover 15–76% of their generating b_z; the eight joint means recover 57–128%. All four b_z interval misses are Nicolas cut fits. H2's bridge intervals cover all sixteen truths. The eight UWA H1 errors range from −.24 to −.45. These configurations still contain only four generated datasets. The original six-pair cut/joint range was 17–42%; the two recovered UWA fits extend it to 17–65%. These are engineering results, not replicated calibration. [Final independent checks](../logs/d1c-recovery-final-readcheck-20261011.json); [all sixteen configurations and intervals](../results/d1c/baseline-recovery-20261011/REPORT.md).

The code implements the specified cut: upstream latents depend on measurements E alone, and each downstream conditional treats one upstream draw as fixed. It does not substitute a single posterior mean. Withholding outcome information from noisy covariates is a plausible attenuation mechanism here. This nonlinear model also has partial indicator coverage, multiple latents and only eight outer draws; the saved runs do not isolate that mechanism or prove a universal attenuation law. A cut can protect upstream inference from a misspecified downstream module while withholding useful information under a better specified joint model. That tradeoff depends on the specification; see [Jacob et al., *Better together?*, abstract](https://arxiv.org/abs/1708.08719).

**Reporting amendment:** for H2, H1, b_z and marking, show joint and cut estimates with each model's 50% and 90% intervals on the same scale. Define every new signed difference as **cut minus joint**. Report that difference and the range between their means as a **sensitivity range**. That range describes disagreement between assumptions; it is not a credible interval, a coverage guarantee or a bound on truth. Keep b_z secondary to H2's predictive contrast. Retain both specifications without choosing the one closer to truth in these four datasets.

## 2. Replace 240 cells with eight

**D1 verdict adopted:** word frequency alone is not an admissible confirmatory commonness indicator under this project's tested measurement model. The [completed D1 grid](../results/d1/SUMMARY_grid.md) has no converged frequency-only configuration across its tested scenarios and sizes. This is a practical exclusion of that pipeline, not proof that no alternative model could identify commonness from frequency. The retained confirmatory analysis requires an additional commonness indicator. The tested frequency-only pipeline did not yield a usable converged analysis; adding an indicator does not by itself resolve confounding or transport problems.

Every D1c cell already has an E commonness indicator on 40% of words at reliability .8. Its varying “reliability” axis concerns register controls. Repeating D1c therefore cannot adjudicate the absence of a commonness indicator. D1's qualified exclusion is adopted; no additional frequency-only implementation is planned.

Retain this reduced method comparison:

| Axis | Retained choice | Decision it informs |
|---|---|---|
| Production design | UWA-like and Nicolas-like | Does the response structure change the joint–cut tradeoff? |
| Generating scenario | Baseline and unmeasured-register confounding | Does protecting the measurement module trade recovery for resistance to misspecification? |
| Feedback | Joint and the specified eight-component cut | How do bias, uncertainty and coverage differ? |
| H2 generating target | −.10 only | Recovery of a nonzero predictive association; this is a simulation value, not a scientific benchmark. |
| Register in fitted model | Omitted | No empirical register instrument is currently verified. |
| Coefficient prior SD | 1 only | Hold the remaining fitting choices fixed. |

This gives **2 × 2 × 2 = 8 cells**, corresponding to original IDs 12, 18, 60, 66, 132, 138, 180 and 186. Drop the rest from the next simulation run; preserve their specifications and existing outputs as historical records. This reduced experiment does not estimate null false-positive rates, test measured-register corrections, cover the display/prevalence bridge, or establish prior robustness. Those limits must remain explicit rather than acquiring replacement cells automatically.

Use **100 fresh, independent generated datasets per design/scenario**, paired across joint and cut: 400 datasets, 800 fitted configurations. At 90% coverage, the binomial Monte Carlo SE is 3 percentage points; the worst-case SE is 5 points. Report exact binomial intervals, paired differences in recovery, bias with its SE, RMSE, interval widths and diagnostic-failure rates. Use each dataset's generated truth for every estimand. Failed fits remain failures and are not replaced to obtain a desired number of successes. Report conditional-on-convergence coverage with its actual denominator alongside failure rates.

This is a coarse assessment: 90 covered intervals out of 100 usable independent replications give a 95% exact binomial interval of approximately 82.4–95.1% for coverage. Large deficiencies can be detected; small departures from nominal coverage will remain uncertain. This does not automatically enlarge the replication count.

Before comparing methods, report dataset counts for both passing, only joint passing, only cut passing and neither passing. Paired differences in error, recovery or interval width use only datasets where both pass, with that denominator stated. Each method's conditional performance uses its own successful subset, whose membership can differ. The difference between these separate conditional means is not substituted for the paired comparison.

A cut configuration passes only if its upstream fit and **all eight** downstream components pass the registered diagnostics and produce complete valid contrasts, as required in the [original specification](../scripts/d1c/README.md). One failed or missing component makes the whole cut configuration fail. Components are never dropped and the remaining weights are never renormalized. Exceptions, incomplete runs and diagnostic failures remain distinguishable; no automatic replacement fits follow.

The experiment evaluates the implemented eight-component procedure. It cannot claim that eight draws accurately integrate the ideal cut distribution. Its repeated-dataset performance still answers whether that affordable implementation is usable; it does not justify fine comparisons of posterior tails.

**Timing and budget:** the [read-only projection](../logs/d1c-reduced-budget-preview-20261011.json) uses observed maximum HF baseline module times within each design, eight downstream components per cut, two workers per machine and the recorded $0.03 machine-hour rate. It gives 8,687 worker-hours and **$130.31** compute. Twenty machines imply an ideal nine days, before overhead; twenty is a planning assumption, not a verified account concurrency limit. At 50 machines the same arithmetic gives 3.6 days (5.4 with the allowance); at 100, 43 hours (65 with the allowance). These durations start after empirical inputs freeze and assume efficient scheduling. A 50% allowance gives **$195.46**. Register stress has not been timed on HF, and these are projections, not a quote or an invoice. A future launch would need a new cap of approximately **$200**, separate from the existing $15 authorization.

**Adopted order:** defer the replication launch until the vocabulary, source-study response structure and measurement coverage assumptions are fixed. Then update these same eight cells and their budget to that design. Running hundreds more placeholder datasets first would spend most of the budget before answering whether the intended empirical analysis works. No new compute infrastructure or Modal migration is proposed.

## 3. Replace benchmark-dependent falsifiers

Use directional predictions with continuous estimates. Remove “meaningful support”, “evidence against an effect that large”, their overall multiverse labels and the promises to choose L1 and marking thresholds before FIXED. Retain magnitude and exceedance curves without appointing a substantive cutoff.

The adopted wording for the plan is:

> For every estimand, report the estimate, equal-tailed 50% and 90% intervals, and the posterior probability of the predicted sign. The hypothesis makes a directional prediction, not a minimum-size prediction. A 90% interval wholly on the opposite side of zero counts against that directional prediction under the stated specification. An interval wholly in the predicted direction describes evidence for that direction; it does not by itself establish practical importance or mechanism. An interval spanning zero leaves direction unresolved at this interval convention. A narrow interval near zero describes the small values compatible with the data; without a justified equivalence margin it does not establish absence.

| Estimand | Own units and prediction | Directional finding against it |
|---|---|---|
| H2 | Mean log ratio of focal-word choice probability at commonness z+1 versus z, integrating marking and usage as specified; predicted negative | 90% interval wholly above 0 |
| L1 θ_m | Probability difference in the frozen model protocol: positive pole judged rarer for pairs with a negated positive pole minus the other pairs; predicted positive | 90% interval wholly below 0 |
| Word-level marking | Average change in probability of formal negation as within-valence commonness increases over the fixed endpoints; predicted negative | 90% interval wholly above 0 |
| H1 | Exploratory predictive comparison, with usage treatment stated | No confirmatory common-cause falsifier is assigned |

> Apply these statements separately to every admissible specification, construct and target population. Show where the predicted direction is contradicted, where it remains unresolved, and how estimates differ. For a fixed estimand and target population, call a directional contradiction robust across the prespecified set of admissible specifications only when every specification in that set contradicts the prediction. Identify the set in the report. Otherwise state the assumptions on which it depends. Do not average specification votes or interpret their proportions as probabilities. For word-level marking, show word-based and description-based results across their own bias/transport assumptions on the same vocabulary and endpoints. A contradiction at either lexical level cannot be repaired by relabelling the other level as the test after seeing the results. Failed overlap or measurement checks limit interpretation regardless of interval width.

For a continuous posterior, a 90% equal-tailed interval wholly opposite the prediction corresponds to more than 95% posterior probability of the opposite sign. This is an evidential convention, not a substantive magnitude cutoff. For the eight-component cut, intervals and sign probabilities describe the implemented approximation. Findings close to this reporting boundary retain that qualification and are not finely resolved claims about the ideal cut distribution. L1 and word-level marking concern model-judged quantities under the frozen protocol. Their bearing on human commonness, and H2's bearing on actual prevalence, retain the existing transport qualifications. Directional agreement across them is not independent corroboration.

These decisions govern `analysis_plan.md`, the reporting draft and the future D1c specification. Completed baseline jobs retain their frozen code and historical reporting definitions; their archived joint-minus-cut columns keep that explicit historical label. New comparisons use cut minus joint.

## 4. Set the lexical instrument and budget before full coding

The pilot used Sonnet 4.6 because that working instrument was held fixed through the authorized bounded review. That supplies continuity, not evidence that it is the best eventual judge. Anthropic's current [Sonnet 5.5 announcement](https://www.anthropic.com/claude-sonnet-5-5) provides a current candidate for the production pass; availability does not establish superiority for this lexical task.

**Adopted instrument direction:** use Sonnet 5.5 at high effort for the full-frame Claude pass, retaining the isolated Codex-family pass. Freeze the exact available model identifiers, CLI versions, prompt/schema and effort before that pass. Preserve the old pilot as a separate instrument version; do not combine old and new responses as exchangeable replications. The first capped production batch gets schema checks, substantive source-evidence checks and recorded throughput, not another wholesale pilot. No commonness judgments enter lexical screening.

The old 40-form stage cost $1.76 API-equivalent including pair work and incomplete timeout accounting: about $44 per 1,000 forms by crude division. Its word-screening Claude calls alone cost about $29.86 per 1,000. Neither is a representative full-frame quote, a subscription invoice or a conversion into allowance remaining. The six-pair stage adds $1.1203 for completed Claude calls, with its timeout unpriced.

Anderson and Warriner supply 14,082 candidate forms, not 14,082 eligible adjectives. Applying the old word-screening rate to all forms gives about $421 as an illustration; applying the whole-pilot rate gives about $620. These figures exclude several unknown workloads and cannot authorize a full pass. Sonnet 5.5's published API prices also cannot measure the remaining subscription allowance.

Budget coding in three stages:

| Stage | Contents | Purpose |
|---|---|---|
| Evidence inventory | Candidate forms and source membership, dictionary records, candidate senses, evidence lengths, provenance and unresolved coverage | Initial workload estimate; unresolved eligibility and alignment remain visible |
| Capped first production batch | Decisions under the frozen instrument, schema and substantive evidence checks, observed throughput and supplementary-lookup workload | Updated batch budget and continuation decisions |
| Adjudicated inventory | Eligible interpretations, aligned pairs, unresolved dispositions and audit outcomes | Frame freeze before commonness collection |

The initial evidence inventory is not a completed adjudication pass. Some broader Wiktionary triggers can be recognized immediately; others arise during assessment of an in-scope reading. Budget that uncertainty and include two families, pair discovery, rejected/unmatched-form audits, source review and allowance stop rules. The old category-gap count is 10,296; the broader trigger can add cases among the other 3,786. Old dictionary evidence and decision history remain usable across model versions; old and new responses are not exchangeable replications.

Before freezing the adjudicated inventory, tabulate pairs by the positive pole's morphological orientation and retain shared-member identities. The six current pairs do not establish representation of L1's negated-positive comparison group. Record reading applicability and the commonness sampling denominator in separate fields: a waiting-related reading does not change all waking moments into a waiting-conditional denominator. Preserve alternative interpretations without multiplying lexical observations. Set pair weighting separately before commonness collection. No new full-frame allowance is assumed here.

## 5. Housekeeping and the next useful work

The 93 tracked draw archives have been removed from git's index, with local hashes verified unchanged. `*.npz` and `writer.lock` are ignored; summaries and hashes remain public. Old git history still contains earlier archives. STATUS now begins with a short action list and links to run reports. Past DECISIONS entries remain intact; further launches, process IDs, costs and recoveries go to run reports/logs.

Norman work has not advanced. The next implementation stage is its already-described pass-X output/parser repair and failed-row handling, followed by the local Apple Vision pilot against pages 40–41. Keep other extracted values behind the frame-freeze firewall. Wave 1 follows only if the second-pass pilot meets the existing acceptance requirement. This is the next productive task while the frame and empirical design are settled, rather than another expansion of lane S.

Brett accepted this direction and the targeted clarifications in chat on 2026-10-11. His review assessed the document's logic and stated arithmetic; code, convergence and integrity checks remain project findings, not findings independently audited in that review. Acceptance does **not** authorize the $200 replication launch or full-frame model expenditure; those need concrete frozen inputs and a final resource decision.

The final paper will state that computational resources limited the evaluated design. The repository preserves the full 240-cell specification, executable simulation code, seeds, environment records and completed summaries so researchers with larger compute budgets can run the wider grid or extend it. The source manifest identifies empirical inputs and access conditions; third-party raw files are shared only where permitted. The paper distinguishes available specifications from experiments actually completed.
