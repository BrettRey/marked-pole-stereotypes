# D2 grid: summary
<!-- SUMMARY: D2 fake-data grid for L1 and L2 finished 2026-10-09 22:15 (21,800 L1 and 3,180 L2 fits, exit 0); L2 calibrated in its core, L1's theta_m under-covers (0.81), theta_m_fp unusable, power low at placeholder effects, judge bias the main threat · status: done · updated: 2026-10-09 -->

Fake data only (`scripts/d2/README.md`): every size, share and effect is a placeholder, and none of these numbers estimates anything about real words. Grid run 2026-10-09, 14:55–22:15, logs `logs/d2-20261009-200622.json` (L1) and `logs/d2-20261009-221554.json` (L2). Per-cell tables: `l1_grid_summary.md`, `l2_grid_summary.md` (`summarise_d2.py`). Every number below comes from `d2_digest.md` (`digest_d2.py`), as a mean over the cells it names. Written by the main session (Claude Opus 5.5); the reading in the last section is its own and settles nothing.

## Convergence

L2 is clean: in the median cell no fit has an R-hat above 1.01 (worst cell 0.32 of fits), and no cell has more than 5% of fits with a divergence. In L1, about half of design (c)'s fits have a largest R-hat above 1.01, but the excess is small: median 1.010, 90th percentile 1.019, maximum 1.093, 0.2% above 1.05, and the 10th percentile of the smallest ESS is 258. Coverage is the same whether or not a fit crossed 1.01 (θ_m 0.791 both ways). The ordinal designs (b10, b30) had a divergence in 35% and 19% of fits; design (c) in none.

## L1 (pairs; model judges, design c, now primary)

| | Core cells | By number of pairs (40, 80, 160) |
|---|---|---|
| θ_m, 90% coverage | 0.81 | 0.79, 0.81, 0.84 |
| θ_m_fp, 90% coverage | 0.71 | 0.80, 0.70, 0.66 |

In the core, θ_m's 90% interval excludes 0 in 11% of fits when β = 0, 16% when β = 0.5 and 56% when β = 1. The frame-level θ_m_fp excludes 0 in 66% of fits at β = 0, and its coverage falls as pairs are added and collapses under the availability and δ scenarios (0.02–0.04). For comparison, the Dirichlet coder (design a) covers θ at 0.92 in the core and excludes 0 in 52% of fits at β = 1.

θ_m is sensitive to judge bias: coverage is 0.27 under δ−, 0.76 under δ+ and 0.75 under confounding; elsewhere it runs 0.81–0.89. The word-level contrast κ covers at 0.91 without bias and 0.40 and 0.43 with δ = +0.4 and −0.4.

## L2 (words; categorical model)

In the core (300 words), apc_z covers at 0.91 adjusted and 0.90 unadjusted, apc_s at 0.89 and 0.90, and bzC at 0.96 and 0.97. With β_z = 0, apc_z's interval excludes 0 in 10–12% of fits. With β_z = −0.4, it excludes 0 in 57–62% of fits, but only 31–35% clear the placeholder threshold of .03 in the predicted direction; with 150 words, 12–22% do.

Judge bias moves everything. Description bias δ_d = ±.3 leaves apc_z covering at 0.54–0.57, and a word-based indicator with bias δ_m = ±.4 at 0.27–0.31. With δ_m = +.4 and β_z = 0, 70% of fits exclude 0 and 45% clear the threshold in the predicted direction. The register confound (β_z = 0) gives 32% exclusions and coverage of 0.68. On the stakes side, the README's "naive stakes" case leaves apc_s covering at 0.35, and an assumed stakes reliability of .6 gives 0.72 (.25 gives 0.88).

## Reading (main session; for Brett, not settled)

1. θ_m works in the core but under-covers (0.81 for a nominal 0.90), less so with more pairs. θ_m_fp shouldn't carry inference.
2. Power is low at the placeholder effects: θ_m excludes 0 in about half the fits at β = 1 and in a sixth at β = 0.5, and L2 clears its placeholder threshold in about a third of fits at β_z = −0.4.
3. The main threat in both models is judge bias aligned with the outcome (δ in L1; description and word-level bias in L2), which produces confident wrong answers. That's the case for the plan's pre-specified bias bounds and for requiring agreement across them. D2b, at the realized frame, reports label probabilities and conditional bias by scenario (`scripts/d2/README.md`).
4. The threshold-examples note (lane S) and D2b should use these numbers; the benchmarks themselves are Brett's.
