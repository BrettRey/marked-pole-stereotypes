# Analysis plan
<!-- SUMMARY: SKELETON ONLY (2026-10-07): headings from the brief, nothing decided; becomes the plan of record when filled in and committed with status FIXED, before any outcome model is fitted · status: skeleton · updated: 2026-10-07 -->

**Status: skeleton.** Nothing below is decided. The plan of record is the commit that fills these sections and changes the status line to **FIXED**, made before any outcome model is fitted (brief, ground rules). Anything done with outcome data before that commit is post hoc and goes in `DECISIONS.md` as such.

## Hypotheses

- H1: P(attribute produced as a stereotype) rises with markedness (affixal negation; marked member of an antonym pair), controlling for valence and log frequency.
- H2: within valence, rarer attributes are more often stereotypic.
- Strand A predictions (from the brief): fresh-sample PPV at chance (1/K) with no true differences; high valence agreement and low content agreement across perceivers with no true differences, content agreement rising with true differences.

## Data and exclusions

To write: each dataset (once verified), the unit of analysis, the denominator set of candidate adjectives, lemma normalization and what it loses, exclusions.

## Variables

To write: outcome coding; markedness (affixal negation detection, antonym-pair markedness); valence (Warriner); log frequency; the valence–markedness collinearity and how it's estimated and reported; the informative off-diagonal cases (marked positives, unmarked negatives).

## Models

To write: engine (brms or PyMC) and why; likelihood; group, participant and item effects as the data allow; priors; posterior predictive checks; the effect sizes to report, with intervals.

## What would count against each hypothesis

To write, before fitting: for H1, H2 and each strand A prediction.

## Seeds and environment

To write: seeds, package versions, how runs are logged in `logs/`.
