# Restricted English production analysis: lexical closure and specification

16 October 2026. **The primary analysis will estimate whether lower judged applicability predicts greater coded stereotype production, conditional on emotional valence, among 269 Anderson adjective forms.** UWA Study 2 and Nicolas Study 2 receive separate models and estimates. This is a planned secondary analysis of exposed datasets. No applicability–production association has been estimated for this extension.

Brett authorized “lexical closure and a committed production specification” and approved this document after Roughdraft review on 16 October 2026. The analysis is fixed on commit. Implementation, artificial-data checks and empirical fitting are subsequent stages. The earlier, larger H2 programme's latent prevalence, accessibility, stakes and joint-feedback analyses remain separate.

## The closed vocabulary

The starting inventory is the 330 Anderson entries matched to fitted Koch Study 1 forms. The target is **person-descriptive adjective word forms**, including states, dispositions, capacities and relational or evaluative descriptions. It isn't restricted to enduring psychological traits. Anderson supplies the person-description context; dictionary evidence establishes an adjective use. Neither source establishes the reading intended by a particular Koch or stereotype respondent.

Of the 330 forms, 326 have adjective evidence in pinned WordNet 3.1. Exclude *liar* and *worrier*: their available entries are nouns. Include *resigned* and *soft-hearted*: Cambridge supplies the missing adjective evidence, respectively for acceptance of an unwelcome situation and sympathetic kindness. These two dictionary pages are downloaded, hashed and registered in the source manifest. See [resigned](https://dictionary.cambridge.org/us/dictionary/english/resigned) and [soft-hearted](https://dictionary.cambridge.org/us/dictionary/english/soft-hearted).

This closes the broad frame at **328 forms**. The primary frame contains its **269 forms with unique exact Warriner matches**. The other 59 remain eligible but lack this emotional-valence measure. Their exclusion from the primary analysis is measurement selection, not lexical ineligibility. Keep them in a separately labelled 328-word likableness analysis.

The existing normalization and seven registered Anderson aliases are retained; only *self-centered* adds a match here. No new spelling, synonym, inflection or sense transfer is introduced. All 330 dispositions, source entry identifiers, dictionary packets, available norm values and exact Koch array indices are preserved privately. Of the 328 included forms, 238 have multiple WordNet adjective senses and 75 also have other word classes. These are ambiguity flags, not evidence of incorrect responses or exclusions.

| Frame | UWA matched responses / all text | UWA zero-production words | Nicolas matched responses / all text | Nicolas zero-production words |
|---|---:|---:|---:|---:|
| Shared emotional-valence/likableness frame: 269 | 348 / 1,972 | 174 | 3,959 / 14,997 | 69 |
| Broader Anderson adjective frame: 328 | 356 / 1,972 | 227 | 4,153 / 14,997 | 100 |

Membership does not depend on production frequency, rating count, uncertainty width or fitted association. The denominator is a statistical coding domain, not a menu participants were shown or proof that each word was available to each participant. This word-form closure doesn't release sense-level trait units for the separate lexical programme.

The source and artifact hashes are in [the freeze receipt](../results/h2-preparation-20261016/freeze.json); the reproducible closure script is [close_frame.py](../scripts/h2_production/close_frame.py). Private source-derived vocabulary and norm tables stay out of git.

## Outcomes and source selection

Use the frozen UWA coding and **archived corrected** Nicolas coding identified by the receipt. A response selects word i only when its existing category is `lemma` and that lemma exactly matches the frame. Every other text response selects the explicit outside category. Preserve its original coding category for descriptive reporting. Don't extract an adjective head from syntactic negation, a noun, a phrase or a multiple-adjective response.

For the 269-word frame the outside counts are 1,624 and 11,038; for 328 they are 1,616 and 10,844. Retain unproduced words. UWA's 5,948 `no_response` grid cells supply no choice outcomes: the 198 × 40 grid is not a record of 7,920 presented choices. Use the 1,972 text responses from 198 participants and 40 groups. Response-rated valence is an outcome annotation and doesn't enter as a predictor of the choice.

Nicolas supplies 14,997 text responses from 250 participants and 87 groups. There are 7,499 first-block and 7,498 second-block observations; every observed second response has an observed first response for the same participant and group. Retain the unmatched first response. The trial suffix identifies the group pairing, not a verified chronological presentation position. No response-time filter is applied to this production outcome.

The Koch raters first selected their own descriptors. The measurement source therefore supplies applicability judgments conditional on word production and selected targets, with uneven support. The production datasets don't remove that selection. All datasets, codings and earlier results have already been inspected; this specification is prospective about the new model, not a claim of fresh blinding or independent confirmation.

## Applicability and evaluation measurements

Let qᵢₖ⁽ˢ⁾ be the saved probability of ordinal Koch response category k for word i at measurement draw s. These probabilities average each word's **own observed respondent, target and encounter rows**. They aren't standardized to a common population of people. Use the revised response-style model primarily and the original model as a fixed sensitivity.

The [feasibility audit](h2-feasibility-results-2026-10-16.md) records small aggregate predictive discrepancies alongside remaining sparse-word and within-word limitations. Carrying posterior draws forward preserves estimated uncertainty; it doesn't account for model error. Comparing the original and revised models assesses one modelling choice, without establishing measurement validity for this vocabulary.

Define an equally weighted reference distribution within the relevant frozen frame F:

    rₖ⁽ˢ⁾ = mean over j in F of qⱼₖ⁽ˢ⁾
    aᵢ⁽ˢ⁾ = Σₖ qᵢₖ⁽ˢ⁾ [Σₗ<ₖ rₗ⁽ˢ⁾ + ½ rₖ⁽ˢ⁾]

Thus a is the probability of a higher response than a random reference-word response, with half credit for a tie. It uses category ordering without assuming equal distances between labels. Across the frame its mean is ½ for each draw. Define cᵢ⁽ˢ⁾ = (aᵢ⁽ˢ⁾ − ½) / sₐ, where sₐ is the population SD across words of their posterior mean a values, calculated once from all saved draws. Larger c means higher judged applicability. This isn't person prevalence, trait display frequency, or a pure word effect stripped of source-context differences.

For each measurement model and frame, compute sₐ using its own complete saved array. Freeze these constants before the production likelihood runs. Never draw words independently from their marginal posterior summaries: a complete row of the saved array supplies every word jointly. This retains uncertainty from shared raters, targets and model parameters. Original and revised arrays contain 4,000 and 8,000 joint draws respectively.

Primary evaluation is Warriner emotional valence, using the published mean, SD and rating count. In each measurement component, draw a latent norm mean independently by word from Normal(mean, SD/√n), truncated to [1,9]. This is the posterior under a flat bounded prior and a normal sampling approximation. For Anderson likableness, use Normal(mean, √(variance/100)), truncated to [0,6], reflecting the source's 100 raters. Anderson's paper describes liking a person described by the word; it doesn't supply Warriner emotional valence.

These norm-error approximations omit unavailable cross-word covariance and shared cultural or instrument bias. They don't create missing norms. Independent evaluation draws are also assumed independent of Koch's sampling uncertainty. Retain these assumptions in reporting. A sensitivity to evaluation construct compares the same 269 words, so vocabulary selection doesn't masquerade as a construct difference.

Standardize evaluation v using the mean and population SD of the published norm means in the relevant frame. Include linear v and a centered, scaled quadratic h(v). Fix h's center and scale from those standardized published means; evaluate the same transformation on each uncertainty draw. No outcome-based choice of polynomial degree, knots or covariate set is allowed.

## Production likelihood and partial pooling

Use PyMC, consistent with the project's planned production engine: the custom categorical likelihood, crossed effects and conditional measurement components fit its existing workflow. Koch's Stan models remain unchanged. For each dataset and fixed measurement component, fit a categorical response over W words and outside (0):

    Pr(yₙ = i) = softmax(0, ηₙ₁, …, ηₙW)ᵢ
    ηₙᵢ = −log(W) + α + Aₚ + Gɡ + bₙ δ + bₙ oₚɡ ζ
           + aᵢ + dɡᵢ
           + (β + Bₚ + Cɡ + bₙ β₂)cᵢ
           + (γ + Eₚ + Hɡ + bₙ γ₂)vᵢ
           + (κ + bₙ κ₂)h(vᵢ)
           + bₙ λ I(first response for p,g is word i).

For UWA, b is always zero and all block/history parameters are absent. For Nicolas, b is zero in block 1 and one in block 2; o records whether the first response was outside. The last term captures repetition of a particular in-frame word. ζ instead captures persistence of membership in the broad outside category; it isn't literal repetition of an outside word. Both first and second choices contribute to the likelihood.

A and G are participant/group intercepts for all in-frame words relative to outside. They don't cancel because the outside utility is fixed. B/E and C/H are participant/group applicability and evaluation slopes. The word residual a and group-by-word residual d allow stable word accessibility and group-specific content beyond measured predictors. They don't make those omitted processes independent of applicability in the real world; that remains a model assumption.

Use mutually independent, non-centred Gaussian random effects with learned scales. Center each participant/group vector and a over its levels. Generate d from an independent standard-normal G × W matrix and double-center it across groups and words. Divide centered vectors by √(1−1/N), and d by √[(1−1/G)(1−1/W)], before multiplying by their scales. No extra overall word intercept is included.

| Parameter | Prior, separately in each dataset |
|---|---|
| α | Normal(0, 2) |
| β, γ | Normal(0, 1) |
| κ | Normal(0, 0.5) |
| δ, ζ, λ in Nicolas | Normal(0, 1) |
| β₂, γ₂, κ₂ in Nicolas | Normal(0, 0.5) |
| Word and group-by-word residual scales | Half-Normal(0, 1.5) |
| Participant/group intercept scales | Half-Normal(0, 0.75) |
| Participant/group applicability/evaluation slope scales | Half-Normal(0, 0.5) |

The −log(W) offset makes α=0 correspond to one-half in-frame probability when all other effects are zero. Priors are regularization assumptions on standardized predictors, not substantive effect benchmarks. Inspect their predictive implications before empirical fitting. If they require revision, amend and commit this specification before the empirical likelihood is used.

There is no additional corpus-frequency or morphology coefficient in this restricted H2 model. Its applicability association includes any remaining lexical-accessibility, marking, familiarity and selection pathways. It cannot answer whether applicability predicts production beyond all those factors, nor estimate the full plan's joint marginalization over a learned frequency/marking process. The separate H1 and causal rarity questions remain open.

## Carrying uncertainty forward without feedback

Use a **cut** distribution: average the normalized conditional production posteriors over measurement draws, keeping each source draw's weight fixed. In notation,

    p_cut(ψ,c,v | D_K,D_V,D_P)
      = p(c | D_K) p(v | D_V) p(ψ | D_P,c,v).

Here ψ denotes production parameters. Production outcomes cannot reweight, sharpen or move the Koch or evaluation measurements. Averaging likelihoods under a shared ψ would give a different distribution and is not this procedure. Independent normal errors for Koch word estimates are also not a substitute.

The bounded first implementation uses **eight joint measurement components per specification**, with equal mixture weights. Select eight saved-array rows without replacement using NumPy PCG64 seed 2026101601 for the revised model and 2026101602 for the original model. Reuse the revised row indices across evaluation/frame variants. For evaluation uncertainty use seeds 2026101611 (Warriner) and 2026101612 (Anderson); generate the Anderson vector in the fixed 328-word order and subset it for 269.

Keep the same measurement components for both production datasets. They remain separate production fits but share instrument uncertainty, so their conclusions aren't independent replications of measurement validity. Record exact row indices, normalization constants and predictor-matrix hashes before fitting. Give every component equal posterior weight regardless of chain length or fit convenience; don't silently discard failed components and renormalize the rest.

Eight components are a coarse numerical approximation, not a claim of adequate integration. Report component-specific contrasts, the between-component contribution to uncertainty, first-four versus all-eight summaries and leave-one-component summaries. Inspect Monte Carlo uncertainty within components separately. If the approximation cannot resolve the requested quantity, report that limit. No automatic extra components, replacement fit or method expansion follows.

## Estimands and fixed comparisons

For each posterior draw and eligible word, compare its predicted choice probability at cᵢ+½ and cᵢ−½. Change that word alone, holding competitors, evaluation, random effects and scaling constants fixed. Average log probability ratios equally across words, then equally across participants and their observed first-encounter contexts. UWA contributes its observed text-response contexts; Nicolas contributes block 1. This is a one-SD applicability contrast centered on each word, with H2 predicting a negative value.

Report the mean log probability ratio, its exponentiated ratio and the corresponding mean probability difference per 1,000 text responses. Also report β, group variation and the second-block interaction separately. The primary contrast uses the observed participants/groups; it doesn't average over new populations. Report how often its shifted endpoints exceed the measured frame's posterior-mean applicability range, and describe the reliance on the linear model there.

Summarize each quantity by posterior mean, 50% and 90% equal-tailed intervals, the probability of a negative value and an exceedance curve over the displayed effect range. Interval inclusion of zero, R-hat or an ESS boundary doesn't supply a scientific verdict. Interpret magnitude, uncertainty, predictive adequacy and model dependence together.

The fixed specifications, each fitted separately in UWA and Nicolas, are:

1. **Primary:** revised Koch measurement, 269 words, Warriner emotional valence.
2. **Measurement sensitivity:** original Koch measurement, same 269 words and Warriner measure.
3. **Evaluation sensitivity:** revised Koch measurement, same 269 words, Anderson likableness.
4. **Broader source frame:** revised Koch measurement, 328 words, Anderson likableness; a different vocabulary target, not another estimate of the identical estimand.

Do not select a preferred specification from its effect direction. Differences between emotional valence and likableness are differences between constructs and instruments. Shared vocabulary and measurement do not make agreement independent evidence for a rarity mechanism.

## Implementation checks and stopping point

Before any empirical fit, implement the likelihood and verify it against direct softmax arithmetic on a tiny example, including outside, competition and first/second-block history. Check categorical shift invariance, centring, source hashes, word-index alignment, exact response partitions and retention of zero-production words. Verify the ordinal score against a direct pairwise calculation and verify equal mixture weighting on an analytically tractable example.

Then inspect 200 prior-predictive replications per dataset at its actual design, and run one clearly labelled artificial-data fit at the larger Nicolas design to check recovery arithmetic, implementation and timing. Artificial outcomes test the code; they never substitute for unavailable empirical data. One fit doesn't establish calibration, interval coverage or design precision. Record the generating parameters before that fit and preserve any failure.

The planned conditional sampler starts with four chains, 1,000 warmup and 1,000 retained draws per chain, target acceptance 0.95 and maximum tree depth 12. Seed each conditional fit as 2026101700 + 100×dataset_index + 10×specification_index + component_index, with zero-based dataset/specification indices and components 0–7; chain seeds follow the sampler's recorded convention. This implies 64 conditional empirical fits across the four specifications and two datasets. Benchmark and report the local time/memory budget before asking to launch that stage; this document authorizes none of those fits.

Posterior checks cover overall and participant/group outside shares; within-frame concentration and top-word share; zero-word counts overall and by group; between-group overlap; participant differences in produced applicability/evaluation; and Nicolas block differences and exact in-frame repeats. Generate Nicolas second responses from replicated first responses for joint checks. Retain conditional-history checks separately. Plot observed values against predictive distributions and inspect discrepancies by fixed measurement-support strata, without converting a pointwise interval into a pass/fail verdict.

Report divergences, tree depth, rank-normalized R-hat, bulk/tail ESS, chain traces and Monte Carlo error for the estimands and key scales. Diagnose their consequences for the stated quantities. More iterations cannot repair a wrong likelihood, weak measurement, source selection or semantic mismatch. Any substantive revision gets a separate decision and prospective amendment.

This stage ends with lexical closure, the reviewed specification and a local commit. No production model, artificial fit or new commonness instrument has been run. The next authorized stage would implement and check this exact model, then return the measured compute budget and any limitations before empirical execution.
