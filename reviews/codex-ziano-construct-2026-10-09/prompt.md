You are an independent methodological reviewer, in the project repository, read-only. Do not edit anything. Gelman-style lens, but disagree where it misleads.

Read `analysis_plan.md`: "The measurement problem", "Which rarity", "Commonness judges" (the human anchor bullet), "Model judges only" and its "Overall warrant", and "H2 details". Also `data/manifests/sources.csv` (the ziano2021 rows).

Verified today from Ziano et al.'s OSF files (final Qualtrics survey 2019-05-27 v3 and the raw export): the commonness item asks "To what extent are these traits common among the average Americans?" on 1 (Very uncommon) to 7 (Very common); the introduction says "a common characteristic is one that the average American would frequently display, whereas an uncommon characteristic is one that the average American would rarely display", with a comprehension quiz on that definition. 297 MTurk raters, between-subjects, each rated 40 of the 149 traits plus two instructed-response checks; about 80 ratings per trait; raw per-rater data, with seriousness and quiz fields for exclusions.

So the only human commonness anchor measures how often the average American is perceived to display a trait, not what share of people have it, whereas UWA's mechanism concerns π, the share of group members with the attribute, and the plan's latent is within-valence rarity (prevalence).

Draft response (main session's Gelman pass):
1. Correct the plan: the anchor measures perceived display frequency for the average American (US, MTurk, 2019). The earlier description ("mixes how many people have it with how often it's displayed") is replaced.
2. The model judges get two prompt constructs: Ziano's display-frequency wording (calibrated to the panel, since calibration requires the same construct) and a prevalence wording (the share of people who have the trait; uncalibrated, model-judged only). Both enter the multiverse as distinct indicators, with the gap between them reported per family as a diagnostic.
3. H2's human-only baseline and every human-anchored claim are restated as concerning perceived display frequency; linking it to π is an assumption (display frequency and prevalence covary but can come apart, e.g. traits most people show occasionally against traits a minority show often).
4. The model-judge prompts fix the population as the average American / people in the US for the calibrated construct; Ziano's attention checks and exclusions are applied as the authors did, and the raw ratings are modelled at the rater level (ordinal, rater effects).

Critique, briefly (at most about 300 words): is this right; what's missing; does the construct gap change anything else in the plan (UWA's group-specific π against a population-wide display frequency; strand B datasets from the UK and Ireland). Cite file and section. Mark memory claims "(memory)".
