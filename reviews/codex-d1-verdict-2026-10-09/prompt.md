You are an independent methodological reviewer, in the project repository, read-only. Do not edit anything. Gelman-style lens, but disagree where it misleads.

Read `results/d1/SUMMARY_grid.md` (D1 complete: 340 fits), `scripts/d1/README.md` (spec; scenario 2 is the register confound: an unmeasured item factor h loading on frequency −.5, marking +.8 and production +.4, with βρ = βm = 0), `scripts/d1/d1.py` (`build_joint`), and in `analysis_plan.md`: "D1", "H1 details" (register measures), "Strand B as one generative model" (two-layer frequency), "H2 details".

Facts from the summary: frequency-only fits never converge in any scenario or size; with a prevalence indicator, scenario 1 recovers everything at the large size; in scenario 2, with an indicator, the 90% intervals for b_z exclude zero in 40–65% of large-size fits (posterior mean about +.09, truth 0, i.e. away from H2's predicted negative sign) and for b_m in 45% (mean about +.13, truth 0); scenario 3 large with the r = .5 indicator didn't converge.

Draft reading (main session's Gelman pass):
1. Verdict for Brett: a prevalence indicator is essential for every coefficient; the frequency-only arm leaves the confirmatory analyses and is reported as a documented failure. Provisional on D1c (new frequency model, categorical likelihood).
2. The scenario 2 bias arises because frequency is an indicator of the rarity latent: h moves frequency, so the latent absorbs h, which also moves production. Fixes, all to be simulated in D1c: measured register covariates (etymology, register, familiarity) in the frequency, marking and production equations, at several reliabilities; and a specification in which frequency enters only as accessibility (and as an outcome of rarity through the usage-rate layer) without informing the latent, as a multiverse alternative.
3. The bias's direction in this scenario is against H2 and toward a positive marking coefficient (H1), so it can't be called conservative in general; other loadings would flip it.
4. Scenario 3's non-convergence at large size with the weaker indicator is reported, not hidden.

Critique, briefly (at most about 300 words): is the verdict right and correctly hedged; is the mechanism of the scenario 2 bias right; are the fixes right; anything missing. Cite file and section. Mark memory claims "(memory)".
