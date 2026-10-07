# Strand A: simulation
<!-- SUMMARY: Strand A design spec, written before the code ran: UWA's simulation rebuilt from the paper, plus fresh-sample, negativity-diversity, group-size and consensus-split extensions · status: spec fixed 2026-10-07 · updated: 2026-10-07 -->

Built from the published design in Unkelbach, Weitzel & Alves (2026), "Simulation Design" (p. 12), "Outcome Variables" (p. 13) and Figure 6 (p. 14), journal pagination, not from `uwa_replication.py`, which the brief mentions but which was never supplied (Brett, 2026-10-07: "build it from the paper now"). If that script or UWA's own code (researchbox.org/4585) turns up, it becomes a second implementation to check against.

This spec was written before any of it ran. Choices marked **[ours]** aren't in the paper or the brief.

## Core design (UWA)

- K = 10 equally likely groups, 100 individuals each; group 1 is the target.
- 100 binary attributes, 50 positive and 50 negative, each present with a fixed base rate independent of group: πpos/πneg ∈ {.50/.50, .60/.40, .70/.30, .80/.20, .90/.10}.
- 1,000 runs per condition.

**Counts, not individuals [ours].** Attributes are independent of group and of each other, so the number of group-*g* members with attribute *A* is Binomial(n_g, π_A), independently across groups and attributes. Drawing those counts directly is equivalent in distribution to drawing every individual. This stops holding if attributes are made correlated (e.g. a three-valued A6); revisit then.

## Outcomes (UWA)

With a = target-group members with A, b = others with A, n₁ = target size, n₀ = N − n₁:

1. **Share negative among the top-5 PPV attributes.** PPV = a/(a + b), ranked over all attributes.
2. **Likelihood ratios** for the five highest-PPV positive attributes and the five highest-PPV negative attributes, by rank, with Jeffreys smoothing. The paper's wording fits two definitions; both are computed in the first run, and the one that matches Figure 6 is kept and recorded in `DECISIONS.md`:
   - LR₁ = [(a + .5)/(n₁ + 1)] / [(b + .5)/(n₀ + 1)], i.e. p(A|G₁)/p(A|¬G₁), equal to posterior odds over prior odds;
   - LR₂ = [(a + .5)/(a + b + 1)] / (n₁/N), i.e. PPV over the prior p(G₁).
3. **Mean p(A|G₁)** = a/n₁ across the overall top-5 PPV attributes.

**Ties [ours].** Broken at random. UWA's R code may break them by index order, so the replication is rerun once with positives-first and once with negatives-first index order, to confirm the outcomes move only within Monte Carlo noise.

## Acceptance check against the paper

Primary, from the paper's text:

- T1. The share negative among the top 5 rises monotonically as πneg falls and "approached 100%" (≥ .95 at πneg = .10).
- T2. At .50/.50, positive and negative "did not differ anymore" (share negative within MC error of .50).
- T3. The mean LR of the top-5 positive attributes stays "comparatively close to 1" and changes "only modestly" across conditions.
- T4. At .50/.50, mean p(A|G₁) is "about 60%".
- T5. Mean p(A|G₁) is under .50 once πneg drops below .35 (so under .50 at πneg = .30, above it at .40).

Secondary: values read from Figure 6 by eye (`results/strandA/figure6_read_by_eye.csv`, approximate), tolerance ±.05 for shares and proportions and ±.08 for LRs. A near miss on an eyeballed value doesn't override a text anchor.

## Extensions

**Fresh-sample check (brief, step 2).** In each run, after selecting the top-5 attributes, draw an independent sample from the same population and recompute those attributes' PPV, p(A|G₁) and LR₁. Expected with no true differences: PPV at p(G₁) (= 1/K only for equal groups), p(A|G₁) at π_A, LR at 1.

**Negativity diversity (brief, step 3).** 50 positive and 100 negative attributes; same base-rate pairs and outcomes.

**A5: unequal group sizes (plan).** Total N fixed at 1,000 with K = 10 **[ours: total fixed, target share varied]**. Target size n₁ ∈ {20, 50, 100, 200, 300, 500}; the rest split as evenly as integers allow. Outcomes as above, plus the fresh-sample PPV against p(G₁). How to read it: UWA claim the mechanism needs no assumption about minority status or group size. If small target groups show stronger negativity (plausible, since p̂(A|G₁) is noisier), that's a modulation, not a refutation.

**Consensus split (brief, step 4).** All parameters **[ours]**:

- A world has true rates θ_gA = π_A, except that the target group differs on k = 5 attributes: logit θ₁A = logit π_A + δ.
- δ ∈ {0, .25, .5, 1, 2}.
- **The valence of the differing attributes is a factor:** all negative, all positive, or drawn at random from all attributes. It matters because of the PPV ceiling: a true difference on a frequent positive attribute can't reach the top 5 until it's large, so content agreement should rise faster when the differing attributes are negative. Stated here in advance so the result isn't a choice made after seeing it.
- **Two versions of what perceivers sample from** (added before any run, after a reviewer noted that the first version builds the predicted result in):
  - *Independent:* each of P = 20 perceivers draws its own n individuals per group straight from the world's rates θ. No two perceivers share a society. With δ = 0 their chance patterns are unrelated, so low content agreement is close to guaranteed, and it can't count as confirming the brief's prediction.
  - *Shared society:* each world first realizes one finite society of M members per group (M ∈ {100, 1000}). Each perceiver then samples n members per group from that society, without replacement. Chance differences realized in the society are real differences that every perceiver can see, which is UWA's picture of "real social ecologies". This is the version that tests the prediction.
  - Shared-society counts are drawn as per-attribute hypergeometrics given the society's counts. That ignores the weak dependence across attributes that comes from sampling the same members (its covariance is proportional to the finite-population covariance between independent attributes). The approximation is checked against an exact individual-level simulation on one cell, and the comparison is reported.
- n ∈ {10, 30, 100} members per group per perceiver (n ≤ M).
- Base-rate pairs: all five. 300 worlds per cell.
- Shared version only: each perceiver's agreement with the society's own full-information top 5 (Jaccard), which separates "perceivers agree because the society has realized differences" from "perceivers agree with the generating process".
- Content agreement: mean pairwise Jaccard of top-5 sets across perceivers. Chance baseline for random 5-of-100 sets: expected overlap .25, Jaccard about .026 (computed exactly in the script). Also reported: the share of each perceiver's top 5 that are truly differing attributes.
- Valence agreement: mean top-5 negative share, its SD across perceivers, and the proportion of perceivers whose top 5 is majority negative (≥ 3 of 5).
- Mapping these onto observed stereotype consensus waits for real data and the fixed plan.

## Reproducibility

- One `SeedSequence` (root seed 20261007) spawned per condition.
- Each run writes `logs/strandA-<timestamp>.json`: Python and package versions, platform, git SHA, seeds, arguments.
- Results go to `results/strandA/` as CSV. No figures until the dataviz guidance and `/check-chart-style` have been applied.

Run: `python3 scripts/simulation/strand_a.py <replicate|ties|fresh|diversity|groupsize|consensus|consensus_check|all>`.
