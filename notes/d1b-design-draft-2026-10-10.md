# D1b: restrictions to specify before implementation
<!-- SUMMARY: Preparatory D1b design note: algebraic non-identification, construct separation, required recovery targets and simulation dimensions; not a registered executable spec and no fits launched · status: draft · updated: 2026-10-10 -->

This note prepares the next lane-S task. It does not change D1c or the
settled analysis plan. The requirements come from `analysis_plan.md`,
“Which rarity”, “Display frequency is not prevalence”, “Commonness judges”
and “Multiverse”, and the existing prevalence-indicator review. The
implementation choices below are **PROPOSED**. A numerical specification
and code still need to be committed and pushed before a D1b pilot.

## The ambiguity the simulation must preserve

For indicators measuring one construct, write the measurement mean as

\[
E_{ij}=\alpha_j+\lambda_j Z_i+\mathbf b_j^\top\mathbf X_i
+\epsilon_{ij},
\]

where Z is the common latent and X contains measured familiarity, valence
and morphology. For any vector t, the transformation

\[
Z_i'=Z_i+\mathbf t^\top\mathbf X_i,
\qquad
\mathbf b_j'=\mathbf b_j-\lambda_j\mathbf t
\]

leaves every measurement mean unchanged. If the conditional mean model for
Z contains X, its coefficients transform by adding t too. Differing
indicator-specific biases therefore do not identify their shared component.
Known item-level sampling errors leave this ambiguity intact.

Fixing the latent's location and scale resolves the usual factor-scale
indeterminacy. It does not, by itself, establish that the resulting factor
is actual prevalence or that a shared familiarity effect is measurement
bias. Fixing a latent–familiarity relationship or an instrument's bias can
restrict the trade-off, but that restriction must be reported as an
assumption. A prior supplies information only through its assumptions.

An analogous problem arises with shared residual error. If all instruments
contain the same item component in proportion to their loadings,
λ_j(Z_i + U_i), observations alone cannot separate Z_i from U_i without
restrictions on their distributions or additional information. Smaller
sampling standard errors can make the sum precise without resolving its
decomposition.

**PROPOSED executable check:** verify these mean-preserving transformations
numerically before any fits. In a model that fixes a prior or independence
restriction, show separately how the likelihood and the prior change. Do
not present prior-driven separation as identification by the measurements.

## Keep source constructs explicit

The algebra above concerns indicators of the same construct under a stated
measurement model. It does not justify treating display frequency,
acquaintance applicability, comparative self-endorsement and person
prevalence as interchangeable. Actual prevalence requires a population,
timeframe, trait sense and threshold. Those definitions cannot be supplied
by calling a latent variable “prevalence”.

**PROPOSED first implementation:** distinguish a generating person-prevalence
latent Z from a source-specific perceived-display latent D. Human-style
ordinal ratings and model display judgments measure D through distinct
instrument equations. Person-prevalence model judgments have a separate
equation and shared-bias assumptions. Endorsement remains auxiliary unless
an explicit bridge is being evaluated; it is never silently added as
another prevalence indicator.

A display bridge such as D = a + bZ + U is an assumption to vary, not an
identification result. The simulation must compute truths for the D-based
association and the Z-based association separately. A fit can recover one
and miss the other. Population-to-group and source-population-to-target
transport restrictions must also appear explicitly, rather than being
absorbed into an unexplained error variance.

## What must be frozen in the executable specification

| Element | Required statement before the pilot |
|---|---|
| Factor location, scale and orientation | Reference population, constraints and which loadings are fixed or estimated |
| Shared bias | Fixed values or externally justified prior restrictions for the unidentifiable common component, separately from estimable relative instrument discrepancies |
| Systematic-error floor | Whether it is known, assigned an identifying prior or varied across sensitivity fits; its distinction from rater sampling error |
| Instrument scales | Ordinal thresholds, rater and family variation, loading restrictions, and the overlap connecting instruments |
| Coverage and selection | Artificial vocabulary size, anchors, selection mechanism, unsupported region and the corresponding target populations |
| Transport | Parameters or restrictions linking source constructs, populations and measurement relationships |
| Feedback | Exact factors included in joint inference and in each cut; shared parameters and conditional normalization |
| Downstream contrasts | Commonness endpoints, fixed competitors, averaging distributions and distinct truths for display and prevalence |
| Reporting | Fixed cell order, intervals, Monte Carlo error, diagnostics, failures, retries and the limits of any finite cut approximation |

The design must compare the available indicators on a common vocabulary
before expanding the target population. A disconnected overlap graph, or
an unsupported item class, must not gain an apparently anchored scale
merely through partial pooling. Out-of-support performance needs its own
report, even when the fitted hierarchical model returns narrow intervals.

## Conditions required by the settled plan

The condition set needs a favourable reference case and stress cases for
shared availability bias; instrument-specific and shared morphological bias
in both directions; selected anchors; weak overlap; failed loading or
threshold invariance; floor or midpoint compression; display–prevalence
divergence; and failed population transport. Null and substantive design
magnitudes are needed, without interpreting the latter as Brett's reporting
benchmarks.

**PROPOSED economy:** distinguish diagnostic experiments that isolate each
failure from the crossed sensitivity design used for conclusions. Choose
the final crossed design prospectively from its interaction coverage and
timing, as the plan requires. Do not choose cells because their fitted
estimates look favourable. Numerical dimensions, replication counts and
computational budgets remain to be specified.

## Downstream compatibility and feedback

D1b must remain compatible with D1c's categorical production likelihood,
eligible vocabulary and outside category. A convenient Gaussian or
independent-count outcome cannot stand in for that check. Pure measurement
experiments can be cheaper, but their conclusions stop at measurement
recovery. H2 needs its actual predictive comparison, not recovery of b_z
alone; L1 and the word-level comparisons need their own targets.

For a cut with upstream latent and measurement parameters L, θ_E and
downstream parameters θ_D, the specification must give

\[
q(L,\theta_E,\theta_D)
=p(L,\theta_E\mid E)\,
p(\theta_D\mid Y,M,C,L),
\]

or a clearly stated alternative partition. The downstream factor is
normalized separately for each upstream draw. If parameters are shared,
the partition must say which module determines them. Equal-weight mixing
of conditional posterior draws approximates this cut; weighting by
downstream evidence restores feedback and changes the target.

The commonness module's eventual engine is the acceptometer's Stan model,
with its construct-specific assumptions checked. **PROPOSED implementation
check:** demonstrate that whatever simplified simulation interface is used
matches the registered measurement factors and preserves posterior-draw
dependence. A reduced Gaussian calculation can test the algebra, but
cannot validate ordinal response behaviour or the full Stan-to-PyMC path.

## What a completed D1b report must distinguish

Report latent recovery and interval calibration, source-construct recovery,
downstream contrast recovery, and success under each identifying assumption
separately. Include misleading precision, sign errors, conditional absolute
bias and false meaningful-support probabilities by generating scenario.
Coverage and other rates carry Monte Carlo uncertainty. Failed diagnostics
and exceptions remain in the record.

A well-mixed posterior under a false anchor can be precisely wrong.
Successful internal prediction of selected anchors doesn't establish
transport beyond them. Agreement among model families doesn't exclude
shared bias. These are reasons to display the assumption-specific results,
not reasons to discard a specification after seeing its estimates.

## Next implementation step

Turn this requirement map into `scripts/d1b/README.md` with numerical
choices marked **[ours]**, the algebraic restrictions stated for each fit,
and a fixed pilot and reporting order. Implement and check the invariances
and data-generating truths before the first model fit. Keep `analysis_plan.md`
unchanged; the analyst handles later integration of empirical-plan text. This note
is preparation, not a completed D1b specification or a launched pilot.
