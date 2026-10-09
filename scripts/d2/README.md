# D2: fake-data check of the lexical models (L1, L2)
<!-- SUMMARY: D2 spec, written before any D2 code ran (v2, revised after a Codex review of v1): fake-data simulation of L1's pair-level comparisons and L2's word-level marking model at placeholder sizes; reports calibration with Monte Carlo error, Type S/M, and false-support rates under systematic bias · status: spec 2026-10-09 · updated: 2026-10-09 -->

Fake-data simulation in the sense of Gelman et al. (2020, *Bayesian Workflow*, §4.1), for L1 and L2 in `analysis_plan.md` ("L1", "L2", "D2"). Simulated data is used only to evaluate the design. It is never analysed as evidence and never stands in for a dataset that should come from a source. Every number marked **[ours]** is a placeholder chosen for plausibility, not taken from a source. Sizes are placeholders until the frame is frozen; D2 is then rerun at the realized sizes (D2b).

v1 of this spec (commit 7398633) was reviewed by Codex before any code was written (`reviews/codex-d2-spec-2026-10-09/`). v2 changes: L1's estimand becomes a response-probability contrast for one fixed blind-coder protocol; designs are compared on that target; L2's stakes rest on arousal alone, since within negative words valence extremity is a linear function of valence; the predictive comparison is defined exactly; stress cells cover root availability, separation, orientation errors, sparse affix classes and floor compression; Monte Carlo error is reported.

**Sign convention.** Throughout, δ > 0 means the negated pole or word is judged rarer than it is: the direction that manufactures support for the rarity account. Both signs are run, for L1 and for L2.

## What D2 decides

1. Whether L1's primary design (one blind human comparison per pair) is informative at plausible frame sizes, what a second blind judge on a subset adds (precision, reproducibility), and how model judges alone compare. This bears on whether the blind coder's comparisons are worth their time.
2. How far a bias that tracks the negated pole (description bias in the primary design, morphological bias in the word-based one) produces false support, and the size at which it does.
3. Whether L2's rarity coefficient is identified next to stakes measured by one crude indicator, and what adjusting for act type does under the two causal stories.
4. Whether the planned estimands and priors are calibrated, and the sign-error and exaggeration rates.

## D2-L1: which pole carries the negator

**Units.** Pairs *i* = 1..N in the frozen frame: a positive pole P and a negative pole Q, one of them negated.

**Generating model.**

- Pole prevalences on the logit scale: ρ_Q ~ N(−1.5, 1); relative prevalence r = ρ_P − ρ_Q ~ N(1.0, 1.2), so positive poles are usually the more common **[ours]**.
- Which pole is negated: Y = 1 if the positive pole is negated, Y ~ Bernoulli(logistic(α − β·r_std + β_x·x)), r_std = (r − 1.0)/1.2. β is the rarity-to-marking link; α is set per cell so the frame's share of Y = 1 pairs is s_off.
- Sizing (computed before any D2 code by simulating this model): β = .5, 1, 2 move the mean of r by about .6, 1.0 and 1.6 between pair types, and even at β = 1 the positive pole is the rarer one in only about 40–50% of Y = 1 pairs. So the test is always the contrast between pair types, never "the negated pole is usually rarer".
- Confound outside the fitted model (stress): x = −.5 r_std + √.75 ξ, a salience variable that pushes Y = 1 where the positive pole is rarer, with β = 0 and β_x = 1 **[ours]**. The association is then real and the causal link absent.
- Valence orientation: the poles' valence difference Δv ~ N(1.5, .6), observed with error N(0, .3); where the observed difference has the wrong sign, P and Q swap in the analysis (Y and the response coding both flip). Stress: Δv ~ N(.8, .6), about 10% swapped **[ours]**.
- Eligibility selection (stress): a pool of 6N pairs, P(eligible) = logistic(−.5 + .8 ρ̃ − .5 Y), ρ̃ the standardized prevalence of the negated pole **[ours]**; N drawn from the eligible ones.
- Root availability (stress): a pair exists in the frame only if its root is an eligible adjective, P = logistic(.5 + .8 ρ̃_root) **[ours]**.
- Shared roots (stress): 15% of pairs share their root pole, its prevalence and its descriptions with another pair **[ours]**.

**Judgments.** Each comparison shows one wording set (a description of P and one of Q; two sets per pair). The judge's latent is d = r + ω_w + b_j + η_i + φ_ij − δ(2Y − 1) + ε, with ω_w ~ N(0, .5) the wording-set effect, b_j the judge's tilt toward positive poles, η_i and φ_ij shared and family errors (model judges only), ε ~ Logistic(0, s_j), and δ a bias that tracks the negated pole (sign convention above; in d, a negated positive pole is pushed down and a negated negative pole up). Responses: P more common if d > .4, Q more common if d < −.4, about equal otherwise; "can't say" at random with probability .05 **[ours]**.

- Blind coder: every pair once, wording set at random; b = .3, s = .6; stress s ∈ {.4, .9} **[ours]**.
- Second blind judge: every Y = 1 pair plus random Y = 0 pairs, 10 or 30 of them; half the subset sees the coder's wording set and half the other one, so judge and wording disagreement can be separated; b = .1, s = .7 **[ours]**.
- Model judges: three families, both wording sets; η ~ N(0, .4), φ ~ N(0, .25), b = .5, s = .3; stress: availability bias a_m(2Y − 1), a_m = .3 **[ours]**.
- Floor compression (stress): when both poles are rare (both logit prevalences below −2), the about-equal band widens from ±.4 to ±1.2 **[ours]**.
- Informative "can't say" (stress): .05 for Y = 0 pairs, .20 for Y = 1 **[ours]**.

**Estimand (protocol contrast).** θ = P(the blind coder judges the positive pole the rarer | Y = 1) − P(the same | Y = 0), for one comparison under the fixed protocol (one wording set at random, about-equal allowed, can't-say excluded), over the frame's pairs. Positive under the rarity account. The full three-category response distribution by pair type is reported beside it. **Truth:** computed under that protocol from 400,000 simulated pairs of the cell's generating model, with the coder as generated and δ = 0; under selection, the pool's value is reported beside the frame's. For model judges, θ_m is the same contrast for a model judge's response; its truth is computed the same way, and its gap from θ is reported, since models alone estimate θ only through a bridge.

**Designs and analysis models.**

- (a) Coder alone: multinomial regression of the three responses on Y (Dirichlet(1,1,1) priors per pair type, conjugate), giving θ directly.
- (b) Coder plus second judge: ordered logit with judge-specific cutpoints and noise scales, pair effects u_i and wording-set effects, identified by the overlap; θ is computed from the posterior predictive for a new coder comparison of each frame pair, averaged over pairs. Also reported: the posterior for inter-judge agreement (the correlation of the two judges' latents), the reproducibility the second judge is there to show.
- (c) Model judges alone: the same ordered logit for the three families (family-specific cutpoints and scales, pair and pair-by-family effects), giving θ_m, defined as the protocol contrast for a model judge's response averaged over the three families of the panel, one comparison with a wording set at random.

In (b), the inter-judge agreement is the latent correlation of the two judges' judgments of the same pair under different wording sets, within pair type; its truth is the same correlation in the generating model, from the large simulated population.

PyMC with nutpie for (b) and (c), four chains, 1000 draws after 1000 tuning steps; priors N(0, 1.5) on coefficients, HalfNormal(1) on SDs, ordered N(0, 2) cutpoints **[ours]**.

**Grid.** Core: N ∈ {40, 80, 160} × s_off ∈ {.1, .2, .3} × β ∈ {0, 1}, plus β = .5 at N = 80. Stress, at N = 80 and s_off = .2, with β ∈ {0, 1} unless noted: δ = +.4; δ = −.4; confound (β = 0); eligibility selection; root availability; orientation errors; shared roots; informative can't-say; floor compression; coder noise .4 and .9; model availability bias (design c). 100 replicates per cell for design (a) and 60 for (b) and (c); seeds fixed per cell and replicate **[ours]**.

**Word-based specification (secondary).** At N = 80 and s_off = .2: each pole also gets a commonness rating from its word, e = ρ + δ_m·[negated] + N(0, .5) (known SE), δ_m ∈ {−.4, 0, .4}, floored at the scale minimum (logit −2.5) to give floor compression; the logistic slope of Y on the rating difference (the positive pole's relative rarity), with the valence difference, is fitted by maximum likelihood for speed, using the ratings as observed. Each dataset is refitted over an assumed-bias grid (the negated pole's rating corrected by −.6 to .6 in steps of .05), and the tipping point, the assumed bias at which the 90% interval for the slope reaches 0, is recorded.

## D2-L2: which negative concepts get negated forms

**Units.** Negative person-descriptive words *k* = 1..K.

**Generating model.**

- Within-valence prevalence z ~ N(0, 1) (higher = more common); stakes s = ρ_zs z + √(1 − ρ_zs²) ξ, ρ_zs ∈ {0, −.5, −.8}; valence within negatives v = −.4 s + √.84 ζ **[ours]**.
- Outcome, six categories: simple (reference), *un-*, *in-* (and allomorphs), *dis-*, *non-*, *-less*, with shares about .68, .14, .08, .03, .02, .05 **[ours]**. For each negated category c, η_c = α_c + β_z,c z + β_s s − .3 v + β_a a. The three contrary prefixes' z coefficients are β_z + (−.2, 0, .2) (fixed, so each cell has one truth), and 0 under the null; *non-* and *-less* have β_z and .5β_z. β_z ∈ {0, −.4} (rarer, more often negated, under the rarity account), β_s = −.5 **[ours]**.
- Act type, two causal stories. **A:** act type a ~ Bernoulli(.4) comes first and enters the outcome with β_a = .8. **B:** the outcome is generated without a, then a ~ Bernoulli(logistic(−1.2 + 1.8·[negated])) **[ours]**.
- Register confound outside the fitted model (stress): h with corr(h, z) = −.4 adds .6h to the contrary prefixes, with β_z = 0 **[ours]**.

**Measurements.** Description-based commonness e_d = z − δ_d·[negated] + N(0, .6), known SE, floored at −2 in the floor-compression stress cell; word-based commonness e_w = z − δ_m·[negated] + N(0, .5), known SE (sign convention above); arousal = .6 s + N(0, .8), reliability about .36; act type coded from descriptions with sensitivity and specificity .85; word-coded act type (stress): omission coded .15 more often for negated words **[ours]**. Valence extremity isn't an indicator here: within negative words it's a linear function of valence, so it can't be separated from the valence term.

**Analysis model (as planned for L2).** Latent z ~ N(0, 1) with e ~ N(c + λ_e z, known SE), λ_e > 0 (identified by the known SE, as in D1 v2.2); latent s ~ N(0, 1) with arousal ~ N(c_a + λ_a s, σ_a), its reliability λ_a²/(λ_a² + σ_a²) fixed at an assumed value (core: the true .36; stress: .25 and .6), and a free z–s correlation; categorical outcome by softmax over the six categories on z, s, v, with the contrary prefixes' z coefficients partially pooled, separate z coefficients for *non-* and *-less*, β_s, β_v and β_a shared across the negated categories (as in the generator), and observed act type (adjusted) or none (unadjusted). Stress: naive stakes (arousal entered as observed). Priors N(0, 1.5) on coefficients, HalfNormal(.5) on the pooling SD **[ours]**. PyMC, nutpie.

**Estimands.** The average predictive comparison of z on P(contrary prefix) (Gelman & Pardoe 2007, *Sociological Methodology* 37, 23–51, doi:10.1111/j.1467-9531.2007.00181.x): for each frame word, P(contrary | z + .5) − P(contrary | z − .5), holding s, v and act type at the word's values (adjusted) or integrating act type out (unadjusted), averaged over the frame's words. The same for s. Also the pooled β_z on the log-odds scale. **Truth:** the causal comparison in the generating model, same definition, from 400,000 simulated words: story A holds act type at the word's value; story B has no act type in the outcome. Under B the adjusted model conditions on a descendant of the outcome and isn't expected to recover the truth; D2 shows by how much.

**Grid.** Core: K = 300, ρ_zs ∈ {0, −.5, −.8} × β_z ∈ {0, −.4} × story {A, B}, each dataset fitted adjusted and unadjusted; K = 150 at ρ_zs = −.5. Stress, at K = 300, ρ_zs = −.5, β_z ∈ {0, −.4} unless noted: description bias δ_d = ±.3; word-based indicator with δ_m = ±.4; word-coded act type; register confound (β_z = 0); floor compression; assumed stakes reliability .25 and .6; naive stakes; K = 150 with *non-* at 1% (separation). 40 replicates per cell **[ours]**.

## Order of running

Code committed first; then a timing pilot (two replicates of one L1 design (b) cell and one L2 core cell, each model compiled once per cell and design and reused across replicates); replicate counts and workers are then set from the timings, and recorded here before the grid runs. If L2 needs more than an overnight local run, cloud sessions are a question for Brett.

## Reported, per estimand and cell

Coverage of 50% and 90% intervals, with Monte Carlo standard errors; bias and RMSE of the posterior mean; median 90% interval width; sign-error rate and exaggeration ratio among fits whose interval excludes 0, for non-null truths only (Gelman & Carlin 2014); the share of fits in each H2-style decision (90% interval wholly above the threshold, wholly below it, or neither) at placeholder thresholds θ = .10 (L1) and an average predictive comparison of .03 (L2), with .05 and .20 for L1 to show sensitivity **[ours]**; convergence (R̂ > 1.01, divergences), with failed fits shown, not dropped. Under the confound, coverage is judged against the association, and the rate of meaningful-support decisions is reported as false support for the causal link.

## Deliberately absent

Domain effects (the plan keeps them as varying intercepts only). Sizes, shares and effect values are placeholders; D2b reruns at the realized frame.
