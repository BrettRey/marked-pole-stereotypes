# D2: fake-data check of the lexical models (L1, L2)
<!-- SUMMARY: D2 spec, written before any D2 code ran: fake-data simulation of L1's pair-level comparison model and L2's word-level marking model, at placeholder sizes until the frame is frozen; reports calibration, Type S/M and false-support rates under systematic bias · status: spec draft 2026-10-09 · updated: 2026-10-09 -->

Fake-data simulation in the sense of Gelman et al. (2020, *Bayesian Workflow*, §4.1), for L1 and L2 in `analysis_plan.md` ("L1", "L2", "D2"). Simulated data is used only to evaluate the design. It is never analysed as evidence and never stands in for a dataset that should come from a source. Every number marked **[ours]** is a placeholder chosen for plausibility, not taken from a source. Sizes are placeholders until the frame is frozen; D2 is then rerun at the realized sizes (D2b).

## What D2 decides

1. Whether L1's primary design (one blind human comparison per pair, a second blind judge on a subset) is informative at plausible frame sizes, and how that compares with model judges alone. This bears on whether the blind coder's comparisons are worth their time.
2. How far a bias that tracks the negated pole (description bias in the primary design, morphological bias in the word-based one) produces false support, and the size at which it does (the tipping point).
3. Whether L2's rarity coefficient is identified next to stakes when the two are correlated among negative words, and what adjusting for act type does under the two causal stories.
4. Whether the planned estimands and priors are calibrated (interval coverage), and what the sign-error and exaggeration rates are.

## D2-L1: which pole carries the negator

**Units.** Pairs *i* = 1..N in the frozen frame: a positive pole P and a negative pole Q, one of them negated.

**Generating model.**

- Pole prevalences on the logit scale: ρ_Q ~ N(−1.5, 1); relative prevalence r = ρ_P − ρ_Q ~ N(1.0, 1.2), so positive poles are usually the more common (positivity prevalence) **[ours]**.
- Which pole is negated: Y = 1 if the positive pole is negated. Y ~ Bernoulli(logistic(α − β·r_std + β_x·x)), r_std = (r − 1.0)/1.2. β is the rarity-to-marking link. α is set per cell so the frame's share of Y = 1 pairs equals s_off.
- Sizing (computed before any D2 code, by simulation of this model with an ideal judge): β = .5, 1, 2 give a standardized latent difference (below) of about .34, .62 and 1.0. Even at β = 1, the positive pole is the rarer one in only about 40–50% of Y = 1 pairs, so the test is the contrast between pair types, never "the negated pole is usually rarer".
- Confound outside the fitted model (stress): x = −.5 r_std + √.75 ξ, a salience variable (a named negative behaviour invites a negated positive) that pushes Y = 1 where the positive pole is rarer, with β = 0 and β_x = 1 **[ours]**.
- Valence orientation: the poles' valence difference Δv ~ N(1.5, .6), observed with error N(0, .3); where the observed difference has the wrong sign, P and Q swap in the analysis (Y and the response coding both flip) **[ours]**.
- Selection (stress): a pool of 6N pairs; P(eligible) = logistic(−.5 + .8 ρ̃ − .5 Y), with ρ̃ the standardized prevalence of the negated pole (familiar words pass eligibility more often; negated positives are less familiar) **[ours]**. N pairs are drawn from the eligible ones.
- Shared roots (stress): 15% of pairs share their root pole, its prevalence and its wording effects with another pair **[ours]**.

**Judgments.** Each comparison shows one wording set (a description of P and one of Q; two sets per pair). The judge's latent is

d = r + ω_w + b_j + η_i(models only) + φ_ij(models only) − δ(2Y − 1) + ε,

with ω_w ~ N(0, .5) the wording-set effect, b_j the judge's tilt toward positive poles, ε ~ Logistic(0, s_j), and δ a bias that tracks the negated pole (a description of the negated concept that reads as more extreme; in the word-based specification, morphological bias). Responses: P more common if d > .4, Q more common if d < −.4, otherwise about equal; "can't say" with probability .05 at random (stress: .05 for Y = 0 and .20 for Y = 1) **[ours]**.

- Blind coder: every pair once, wording set at random; b = .3, s = .6 **[ours]**.
- Second blind judge: every Y = 1 pair plus random Y = 0 pairs up to 30, with the other wording set; b = .1, s = .7 **[ours]**.
- Model judges: three families, both wording sets; shared pair error η ~ N(0, .4), family error φ ~ N(0, .25), b = .5, s = .3; stress: an extra availability bias a_m(2Y − 1), a_m = .3 **[ours]**.

**Analysis model (as planned for L1).** Ordered logit on the three response categories, "can't say" dropped: latent = γY_obs + judge offset (the coder's fixed at 0) + u_i (+ u_iw when one pair-wording is judged more than once), u ~ N(0, σ_u), u_iw ~ N(0, σ_uw), two ordered cutpoints. Priors: γ ~ N(0, 1.5); offsets ~ N(0, 1); σ_u, σ_uw ~ HalfNormal(1); cutpoints N(0, 2), ordered **[ours]**. PyMC, nutpie, four chains, 1000 draws after 1000 tuning steps.

**Estimand.** The standardized latent difference Δ = −γ / √(σ_u² + σ_uw² + π²/3): how much lower the judged relative prevalence of the positive pole is in pairs where it's negated, in within-pair-type SD units. Positive under the rarity account. It's comparable across judge designs, which the conditional log odds ratio γ isn't (its scale depends on which random effects are in the model). γ is reported too. **Truth:** Δ computed from a large simulated population (400,000 pairs) of the cell's generating model, judged by an ideal blind coder (wording and noise, no δ, no availability bias), for the frame population; under selection, the pool's value is reported beside it.

**Designs fitted to each dataset.** (a) Humans: coder plus second judge. (b) Model judges only. (c) Humans plus model judges.

**Grid.** Core: N ∈ {40, 80, 160} × s_off ∈ {.1, .2, .3} × β ∈ {0, .5, 1}, 30 replicates per cell. Stress, at N = 80 and s_off = .2, with β ∈ {0, 1}: δ = +.4; δ = −.4; confound (β = 0 only, β_x = 1); selection; shared roots; informative "can't say"; model availability bias. Seeds fixed per cell and replicate.

**Word-based specification (secondary).** At N = 80 and s_off = .2: each pole also gets a commonness rating from its word, e = ρ + δ_m·[negated] + N(0, .5) (known SE), δ_m ∈ {−.4, 0, .4}; the slope of Y on the rating difference is fitted (logistic, with the valence difference) and its tipping point recorded.

## D2-L2: which negative concepts get negated forms

**Units.** Negative person-descriptive words *k* = 1..K.

**Generating model.**

- Within-valence prevalence z ~ N(0, 1) (higher = more common); stakes s = ρ_zs z + √(1 − ρ_zs²) ξ, ρ_zs ∈ {0, −.5, −.8} (rarer negative traits carry higher stakes); valence within negatives v = −.4 s + √.84 ζ **[ours]**.
- Outcome, three categories: simple (reference), prefixed (contrary prefixes and *non-*), *-less*. η_prefix = α_p + β_z z + β_s s − .3 v + β_a a; η_less = α_l + .5 β_z z + β_s s + β_a a. β_z ∈ {0, −.4} (rarer, more often negated, under the rarity account), β_s = −.5 (the L2 conjecture: high stakes, simple forms), shares about .70, .25 and .05 **[ours]**.
- Act type, two causal stories. **A:** act type a ~ Bernoulli(.4) comes first and enters the outcome with β_a = .8. **B:** the outcome is generated without a, then a ~ Bernoulli(logistic(−1.2 + 1.8·[negated])), so negation produces omission meaning **[ours]**.
- Register confound outside the fitted model (stress): h with corr(h, z) = −.4 adds .6h to η_prefix, with β_z = 0 **[ours]**.

**Measurements.** Description-based commonness e_d = z + δ_d·[negated] + N(0, .6), known SE; word-based commonness e_w = z + δ_m·[negated] + N(0, .5), known SE; arousal = .6 s + N(0, .8); valence extremity = .5 s + .3 v + N(0, .8); act type coded from descriptions with sensitivity and specificity .85; word-coded act type (stress): omission coded .15 more often for negated words **[ours]**. Core cells set δ_d = δ_m = 0; stress cells set δ_d = .3 (description indicator) and δ_m = .4 (word-based indicator).

**Analysis model (as planned for L2).** Latent z ~ N(0, 1) with e ~ N(c + λ_e z, known SE), λ_e > 0; latent s with the two stakes indicators (loadings positive, residual SDs free) and a free correlation with z; categorical outcome by softmax on z, s, v, with observed act type (adjusted) or without (unadjusted). Priors N(0, 1.5) on coefficients **[ours]**. PyMC, nutpie.

**Estimands.** The average predictive comparison of z and of s on P(prefixed) per SD (Gelman & Pardoe 2007, *Sociological Methodology* 37, 23–51, doi:10.1111/j.1467-9531.2007.00181.x), computed from the posterior predictive, and β_z on the log-odds scale. **Truth:** the causal average predictive comparison in the generating model (story A: act type held at its distribution; story B: act type absent from the outcome), computed from a large simulated population.

**Grid.** Core: K = 300, ρ_zs ∈ {0, −.5, −.8} × β_z ∈ {0, −.4} × story {A, B}, each dataset fitted adjusted and unadjusted; K = 150 at ρ_zs = −.5. Stress, at K = 300 and ρ_zs = −.5, β_z ∈ {0, −.4}: description bias; word-based indicator with morphological bias; word-coded act type; register confound (β_z = 0 only). 20 replicates per cell.

## Reported, per estimand and cell

Coverage of 50% and 90% intervals; bias and RMSE of the posterior mean; median 90% interval width; sign-error rate (Type S) and exaggeration ratio (Type M) among fits whose interval excludes 0, for non-null truths only (Gelman & Carlin 2014); the share of fits in each H2-style decision (90% interval wholly above the threshold, wholly below it, or neither), at the placeholder thresholds Δ = .3 (L1) and an average predictive comparison of .05 (L2), plus .2 and .5 for L1 to show sensitivity **[ours]**; convergence (R̂ > 1.01, divergences), with failed fits shown, not dropped.

## What's deliberately absent

Floor compression of absolute commonness ratings matters for the word-based specification only, and enters there through the rating noise; the primary L1 design uses comparisons. Domain effects aren't simulated (the plan keeps them as varying intercepts only). Sizes, shares and effect values are placeholders; D2b reruns at the realized frame.
