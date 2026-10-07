# D1: design simulation for strand B
<!-- SUMMARY: D1 spec, written before any D1 code ran: fake-data simulation of the strand B joint model (latent rarity), three scenarios, two indicator conditions plus f-only, two dataset sizes; decides whether a prevalence indicator is essential per coefficient and which engine to use · status: spec fixed 2026-10-07 · updated: 2026-10-07 -->

Fake-data simulation in the sense of Gelman et al. (2020, *Bayesian Workflow*, §4.1), for the joint model in `analysis_plan.md` ("Strand B as one generative model"). Simulated data is used only to evaluate the design. It is never analysed as evidence and never stands in for a dataset that should come from a source. Choices marked **[ours]** aren't in the plan or the brief.

## What D1 decides

1. For each coefficient, whether it is identified at all without an independent prevalence indicator, and how reliable that indicator must be.
2. What each dataset size can identify.
3. Whether an unmeasured factor shared by word frequency, marking and production can pass for rarity (scenario 2).
4. The engine (brms or PyMC), with a reason.

## Coefficients tracked

- Production: βρ (H2, rarity), βm (H1, marking beyond rarity), βf (accessibility), βv (valence).
- Marking: γρ, γv, γs (L1, L2).

## Generating model (scenarios 1 and 2)

Items *i* = 1..I are candidate trait words, and *g* = 1..G are groups. Everything is on standardized scales.

- Valence v*ᵢ* ~ N(0, 1), observed exactly **[ours: Warriner means are precise; measurement error ignored]**.
- Latent prevalence ρ*ᵢ* = κ v*ᵢ* + √(1−κ²) z*ᵢ*, κ = .5 (common traits tend to be positive) **[ours]**.
- Latent stakes s*ᵢ* = τ v*ᵢ* + √(1−τ²) ξ*ᵢ*, τ = −.3 (negative traits tend to carry higher stakes) **[ours]**.
- Formal negation m*ᵢ* ~ Bernoulli(logistic(γ₀ + γρ ρ + γv v + γs s)), with γρ = −.5, γv = −1.0, γs = −.3, and γ₀ set so P(m) ≈ .15 **[ours]**.
- Log word frequency f*ᵢ* = λρ ρ + λs s + λv v + λm m + ε, with λρ = .4, λs = .3, λv = .3, λm = −.3 and residual SD .7 **[ours]**. The λm path is form–frequency correspondence. It is exactly what makes word frequency circular as a rarity measure for L1 and L2, so the fitting model keeps it.
- Prevalence indicator, when present: e*ᵢ* = ρ + .2 v + ε_e (the .2 is desirability inflation, as in self-endorsement), with reliability r ∈ {.5, .8}, i.e. ε_e SD √((1−r)/r) **[ours]**.
- Stakes indicator (arousal): a*ᵢ* = s + ε_a, SD 1 (reliability .5) **[ours]**.
- Production: n_gi ~ NegBin(mean exp(α_g + η*ᵢ*), dispersion φ = 2), with η*ᵢ* = βρ ρ + βm m + βf f + βv v + u*ᵢ*, u*ᵢ* ~ N(0, .5). α_g is set so each group's expected total equals N_g **[ours]**.

**Scenario 1, recovery (the model is true):** βρ = −.3, βm = 0, βf = .3, βv = −.5.

**Scenario 2, register confound (βρ = 0, βm = 0):** an unmeasured item factor h*ᵢ* ~ N(0, 1), independent of valence, loads on frequency (−.5), marking (+.8 on the logit scale) and production (+.4), and is absent from the fitting model. The story is learned or Latinate register: words like *intolerant* and *irresponsible* are less frequent, more often prefixed, and plausibly more often produced when people are asked for "stereotypes". Its pattern mimics rarity (low frequency, more marking, more production). **Criterion:** false-exclusion rate of the 90% intervals for βρ and βm, f-only against e present. One thing is expected in advance: h confounds marking and production directly, so βm may stay biased even with a good prevalence indicator. If so, the fix is a register covariate (etymology), not a better prevalence measure.

## Scenario 3, mechanism check

A stylized UWA-type process generates production, and the joint model is fitted to the result. This tests whether the statistical model picks up a UWA-type rarity signature. It does **not** claim that participants behave this way: UWA's participants reported stereotypes they know society holds, not ones formed from their own sampling.

- Item prevalence π*ᵢ* = logistic(logit(.25) + ρ*ᵢ*), with ρ, v, s, m, f, e and a generated as above. Production doesn't depend on m: the true direct marking effect is 0.
- Each group has a finite society of 100 members, with attributes independent Bernoulli(π*ᵢ*). There are no true group differences, so any differences are the society's chance ones (the strand A shared-society setting).
- Each simulated participant samples 30 members of every group without replacement and computes each item's PPV for each group. For each group they give one response, item *i* with probability ∝ exp(5 · z(PPV_gi) + .3 · f*ᵢ*), where z standardizes PPV within the group: diagnosticity plus accessibility **[ours]**.
- **Oracle:** the same production model fitted with the true ρ as data.
- **Recovery criterion:** the joint model's posterior mean for βρ has the oracle's sign, and the oracle's posterior mean lies inside the joint model's 90% interval. For βm, the false-exclusion rate (truth 0).

## Fitting model (PyMC)

It mirrors the generating model, minus h:

- ρ*ᵢ* = κ v + √(1−κ²) z, and s*ᵢ* = τ v + √(1−τ²) ξ, with κ, τ ~ Uniform(−1, 1).
- f: Normal, all four loadings plus an intercept; λρ > 0 identifies the sign.
- m: Bernoulli-logit.
- a: loading on s fixed at 1.
- e (when present): loading on ρ fixed at 1, plus a valence bias term.
- Production: negative binomial with group intercepts α_g and item effects u*ᵢ*.
- Priors: N(0, 1) on coefficients; N(0, 2.5) on intercepts; group intercepts α_g ~ N(log(N_g/I), 2); HalfNormal(1) on SDs; HalfNormal(5) on φ **[ours]**.
- **Prior sensitivity:** f-only cells are refitted with N(0, 2.5) on the coefficients.
- Sampler: nutpie, 4 chains × 1,000 draws after 1,000 tuning, target accept .9. Each fit records R-hat, bulk ESS and divergences. A fit with R-hat > 1.01 or any divergence is flagged and reported, not dropped.

## Conditions

- Indicators: f only; f + e at r = .5; f + e at r = .8.
- Dataset sizes, from the counts UWA report (journal pp. 5–6) times an assumed coverage of .4, the share of responses that normalize to a single adjective in the denominator set **[ours; the normalization hasn't run]**:
  - small: G = 40, N_g = 18 (UWA Study 2: 1,783 responses over 40 groups);
  - large: G = 43, N_g = 134 (Nicolas et al. Study 1: about 14,400 attributes over 43 groups).
  - Nicolas et al.'s participants gave several attributes per group; that within-participant dependence is ignored here.
- Denominator set: I = 400 **[ours; the trait-word list isn't built]**.
- Reps: a pilot of 1 rep per cell first (treated as a run: committed before it ran). The rep count for the full grid is set from the pilot's timing and logged as post-pilot.

## Reported per coefficient and cell

- Coverage of 90% intervals, bias, interval width and posterior contraction (1 − posterior variance/prior variance).
- Where the truth is nonzero: sign-error rate and exaggeration ratio among intervals that exclude 0 (Gelman & Carlin 2014).
- Where the truth is 0: false-exclusion rate.
- Sampler diagnostics.
- **The table Brett decides from:** for each dataset size and indicator condition, which coefficients are identified. "Identified" means posterior contraction ≥ .5, coverage ≥ .8 and a prior-sensitivity shift < .5 posterior SD; otherwise "weak" or "not identified" **[ours; thresholds fixed here before running]**.

## Engine check (brms)

There is one brms attempt on one scenario-1 dataset (small, e at r = .8), using `mi()` latent variables with `subset()` and `mi(rho, idx = ...)` across item-level and count-level rows, and `constant()` priors for the fixed loadings, time-boxed to one hour. Reported: whether it expresses the shared latents, its sampling time and diagnostics, against PyMC on the same data. Either outcome supplies the plan's engine justification.

## Environment

- Project venv `.venv` (Python 3.14.8; pinned in `requirements-d1.txt`: PyMC 6.3.2, nutpie 0.16.11, pytensor 3.3.3, ArviZ 1.3.0).
- pytensor appends `-ld64` on macOS ≥ 15, which this toolchain (ld-27037) doesn't recognise. `scripts/d1/bin/clang++` drops that flag, and every D1 run sets `PYTENSOR_FLAGS=cxx=<repo>/scripts/d1/bin/clang++`.
- Seeds come from one `SeedSequence` (root 20261008) spawned per scenario, condition and rep. Logs go to `logs/d1-<timestamp>.json`, results to `results/d1/`, and `results/d1/SUMMARY.md` is generated from the CSVs.
