You are an independent methodological reviewer for a pre-registered Bayesian analysis, in the project repository, read-only. Do not edit anything. Gelman-style lens (multiverse analysis, Steegen, Tuerlinckx, Gelman & Vanpaemel 2016; garden of forking paths; model expansion vs. separate fits), but disagree with it where it misleads.

Read `analysis_plan.md`, especially the new section "Multiverse (settled ...)" and "New rating study", and the sections it refers to ("Which rarity", "H2 details", "H1 details", "What the model can and can't identify"). Earlier reviews are in `reviews/` (h2, h1, prevalence).

Brett has decided: defensible analytic options are all run as a pre-specified multiverse rather than choosing one. The question is not whether to do a multiverse but how to make this one sound. Critique it:

1. Are the dimensions the right ones? Anything defensible missing, or anything included that isn't a defensible analytic option (and so should be fixed, not varied)?
2. Is "full factorial for the lexical models; one-at-a-time around a reference specification plus indicators x word sets x availability interactions for the joint model" a defensible economy? What would you change, given that each joint-model fit is expensive (minutes to tens of minutes)?
3. Reporting: how should results across specifications be summarized so the multiverse isn't itself a forking path (e.g. no post hoc emphasis), and how should the evidence criteria for H2 (meaningful support if the 90% interval lies wholly below -.10; against an effect that large if wholly above -.10; else inconclusive) be applied across a multiverse?
4. Gelman has also argued for expanding the model to include choices as uncertain components rather than running separate fits (memory). Where would model expansion be better than separate fits here?
5. The planned two-framing rating study (adjective vs behavioural description): does it identify what it claims to (the word-form/availability effect)? What design features does it need (e.g. counterbalancing, within- vs between-rater framing, how behavioural descriptions are written and checked, rater numbers per item)?

Rules: cite file and line or section for repository claims; mark literature claims from memory as "(memory)"; at most about 700 words; be concrete.
