# Next-stage decisions: reduce the simulation question

2026-10-11. **Proposed for review; no new fits or full-vocabulary model calls are authorized by this document.** Hugging Face remains the compute platform. The two already-authorized baseline recovery jobs may finish within the existing $15 cap.

My recommendation is to report joint and cut together, close the frequency-only route for confirmatory use under the tested model, replace the 240-cell D1c grid with eight decision-relevant cells, and defer their replication until the empirical inputs are frozen. Resolve the directional falsifiers now. Finish Norman's extraction work before expanding simulation work again.

The [bounded six-pair review is complete](lexical-six-pair-report-2026-10-11.md). Eleven calls returned and one timed out without retry. Five pairs retain candidate alignments; attentive/unattentive remains unresolved. Of sixteen saved proposals, twelve survive with restrictions, three remain unresolved and one is rejected. No exact complementary reading is established. The report traces every proposal and distinguishes interpretations from independent observations.

| Pair | Disposition of the saved proposals | Target retained |
|---|---|---|
| kind/unkind | Both retained with degree/feeling restrictions | Characteristic |
| friendly/unfriendly | Three retained; helpfulness/friendship alignment unresolved | Characteristic |
| patient/impatient | Endurance/irritability retained; eagerness rejected | Characteristic and state separately; relevant delay/trying situation explicit |
| happy/unhappy | Both experiential alignments retained; exclusion unresolved | State |
| attentive/inattentive | Four candidates retained; attention/care standards remain explicit | Characteristic and state separately; Claude timed out |
| attentive/unattentive | Both unresolved; bare negative cross-reference does not select the interpretation | No released target |

## 1. Report the joint–cut sensitivity directly

I checked all six completed matched pairs against their saved data seeds and generated truths. Each pair uses the same dataset. The conditional prevalence coefficient's posterior means are:

| Design | H2 generating target | Register measurement reliability | Joint b_z | Cut b_z | Cut / joint |
|---|---:|---:|---:|---:|---:|
| UWA | 0 | .8 | −.1112 | −.0191 | .172 |
| UWA | −.10 | .8 | −.2954 | −.1236 | .418 |
| Nicolas | 0 | 0 | −.0835 | −.0201 | .240 |
| Nicolas | 0 | .8 | −.0777 | −.0213 | .274 |
| Nicolas | −.10 | 0 | −.2974 | −.0963 | .324 |
| Nicolas | −.10 | .8 | −.3071 | −.1152 | .375 |

The eight cut means recover 15–76% of their generating b_z; the six joint means recover 57–128%. All four b_z interval misses are Nicolas cut fits. H2's bridge interval covers its truth in 14/14 configurations; the six UWA H1 errors range from −.24 to −.44. These configurations contain only four independently generated datasets. They establish a pattern to investigate, not coverage, unbiasedness or calibration. [Read check](../logs/d1c-side-by-side-readcheck-20261011.json); [all original intervals](../results/d1c/baseline-batch-20261010/REPORT.md).

The code implements the specified cut: upstream latents depend on measurements E alone, and each downstream conditional treats one upstream draw as fixed. It does not substitute a single posterior mean. Withholding outcome information from noisy covariates is a plausible attenuation mechanism here. This nonlinear model also has partial indicator coverage, multiple latents and only eight outer draws; the saved runs do not isolate that mechanism or prove a universal attenuation law.

**Reporting amendment:** for H2, H1, b_z and marking, show joint and cut estimates with each model's 50% and 90% intervals on the same scale. Report their signed mean difference and the range between their means as a **sensitivity range**. That range describes disagreement between assumptions; it is not a credible interval, a coverage guarantee or a bound on truth. Keep b_z secondary to H2's predictive contrast. Retain both specifications without choosing the one closer to truth in these four datasets.

## 2. Replace 240 cells with eight

**D1 verdict proposed:** word frequency alone is not an admissible confirmatory commonness indicator under this project's tested measurement model. The [completed D1 grid](../results/d1/SUMMARY_grid.md) has no converged frequency-only configuration across its tested scenarios and sizes. This is a practical exclusion of that pipeline, not proof that no alternative model could identify commonness from frequency. An additional indicator is necessary for this proposed analysis but is not sufficient to remove confounding or transport problems.

Every D1c cell already has an E commonness indicator on 40% of words at reliability .8. Its varying “reliability” axis concerns register controls. Repeating D1c therefore cannot adjudicate the absence of a commonness indicator. I recommend accepting D1's qualified exclusion rather than adding another frequency-only implementation.

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

The experiment evaluates the implemented eight-component procedure. It cannot claim that eight draws accurately integrate the ideal cut distribution. Its repeated-dataset performance still answers whether that affordable implementation is usable; it does not justify fine comparisons of posterior tails.

**Timing and budget:** the [read-only projection](../logs/d1c-reduced-budget-preview-20261011.json) uses observed maximum HF baseline module times within each design, eight downstream components per cut, two workers per machine and the recorded $0.03 machine-hour rate. It gives 8,687 worker-hours and **$130.31** compute. Twenty machines imply an ideal nine days, before overhead. A 50% allowance gives **$195.46**. Register stress has not been timed on HF, and these are projections, not a quote or an invoice. A future launch would need a new cap of approximately **$200**, separate from the existing $15 authorization.

**Recommended order:** approve the reduced scientific question now, but defer the replication launch until the vocabulary, source-study response structure and measurement coverage assumptions are fixed. Then update these same eight cells and their budget to that design. Running hundreds more placeholder datasets first would spend most of the budget before answering whether the intended empirical analysis works. No new compute infrastructure or Modal migration is proposed.

## 3. Replace benchmark-dependent falsifiers

Use directional predictions with continuous estimates. Remove “meaningful support”, “evidence against an effect that large”, their overall multiverse labels and the promises to choose L1 and marking thresholds before FIXED. Retain magnitude and exceedance curves without appointing a substantive cutoff.

The replacement wording for the plan is:

> For every estimand, report the estimate, equal-tailed 50% and 90% intervals, and the posterior probability of the predicted sign. The hypothesis makes a directional prediction, not a minimum-size prediction. A 90% interval wholly on the opposite side of zero counts against that directional prediction under the stated specification. An interval wholly in the predicted direction describes evidence for that direction; it does not by itself establish practical importance or mechanism. An interval spanning zero leaves direction unresolved at this interval convention. A narrow interval near zero describes the small values compatible with the data; without a justified equivalence margin it does not establish absence.

| Estimand | Own units and prediction | Directional finding against it |
|---|---|---|
| H2 | Mean log ratio of focal-word choice probability at commonness z+1 versus z, integrating marking and usage as specified; predicted negative | 90% interval wholly above 0 |
| L1 θ_m | Probability difference in the frozen model protocol: positive pole judged rarer for pairs with a negated positive pole minus the other pairs; predicted positive | 90% interval wholly below 0 |
| Word-level marking | Average change in probability of formal negation as within-valence commonness increases over the fixed endpoints; predicted negative | 90% interval wholly above 0 |
| H1 | Exploratory predictive comparison, with usage treatment stated | No confirmatory common-cause falsifier is assigned |

> Apply these statements separately to every admissible specification, construct and target population. Show where the predicted direction is contradicted, where it remains unresolved, and how estimates differ. Call a directional contradiction robust across assumptions only when each admissible specification contradicts the prediction. Otherwise state the assumptions on which it depends. Do not average specification votes or interpret their proportions as probabilities. For word-level marking, show word-based and description-based results across their own bias/transport assumptions on the same vocabulary and endpoints. A contradiction at either lexical level cannot be repaired by relabelling the other level as the test after seeing the results. Failed overlap or measurement checks limit interpretation regardless of interval width.

The 90% convention states a degree of posterior directional certainty; it is not a minimum substantively important effect. L1 and word-level marking concern model-judged quantities under the frozen protocol. Their bearing on human commonness, and H2's bearing on actual prevalence, retain the existing transport qualifications. Directional agreement across them is not independent corroboration.

On acceptance, reconcile all old benchmark wording in `analysis_plan.md`, the reporting draft and the future D1c specification together. The running baseline jobs retain their frozen code and historical reporting definitions.

## 4. Set the lexical instrument and budget before full coding

The pilot used Sonnet 4.6 because that working instrument was held fixed through the authorized bounded review. That supplies continuity, not evidence that it is the best eventual judge. Anthropic's current [Sonnet 5.5 announcement](https://www.anthropic.com/claude-sonnet-5-5) confirms that the model choice needs updating.

**Proposal:** use Sonnet 5.5 at high effort for the full-frame Claude pass, retaining the isolated Codex-family pass. Freeze the exact available model identifiers, CLI versions, prompt/schema and effort before that pass. Preserve the old pilot as a separate instrument version; do not combine old and new responses as exchangeable replications. The first production batch gets schema/evidence checks and recorded throughput, not another wholesale pilot. No commonness judgments enter lexical screening.

The old 40-form stage cost $1.76 API-equivalent including pair work and incomplete timeout accounting: about $44 per 1,000 forms by crude division. Its word-screening Claude calls alone cost about $29.86 per 1,000. Neither is a representative full-frame quote, a subscription invoice or a conversion into allowance remaining. The six-pair stage adds $1.1203 for completed Claude calls, with its timeout unpriced.

Anderson and Warriner supply 14,082 candidate forms, not 14,082 eligible adjectives. Applying the old word-screening rate to all forms gives about $421 as an illustration; applying the whole-pilot rate gives about $620. These figures exclude several unknown workloads and cannot authorize a full pass. Sonnet 5.5's published API prices also cannot measure the remaining subscription allowance.

Before full coding, produce the actual source-supported candidate/interpretation inventory and a batch budget that includes the broader Wiktionary trigger, evidence length, two families, pair discovery, rejected/unmatched-form audits, source review and allowance stop rules. The old category-gap count is 10,296; the broader trigger can add cases among the other 3,786. Preserve multiple interpretations without multiplying lexical observations. Set pair weighting separately before commonness collection. No new full-frame allowance is requested or assumed here.

## 5. Housekeeping and the next useful work

The 93 tracked draw archives have been removed from git's index, with local hashes verified unchanged. `*.npz` and `writer.lock` are ignored; summaries and hashes remain public. Old git history still contains earlier archives. STATUS now begins with a short action list and links to run reports. Past DECISIONS entries remain intact; further launches, process IDs, costs and recoveries go to run reports/logs.

Norman work has not advanced. The next implementation stage is its already-described pass-X output/parser repair and failed-row handling, followed by the local Apple Vision pilot against pages 40–41. Keep other extracted values behind the frame-freeze firewall. Wave 1 follows only if the second-pass pilot meets the existing acceptance requirement. This is the next productive task while the frame and empirical design are settled, rather than another expansion of lane S.

Reviewing this document can settle the reporting, reduced question, falsifiers, model direction and work order. It does **not** authorize the $200 replication launch or full-frame model expenditure; those need concrete frozen inputs and a final resource decision.
