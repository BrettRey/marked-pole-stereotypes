---
slug: marked-pole-stereotypes
kind: paper
title: 'The marked-pole hypothesis and the UWA model of stereotype negativity'
stage: development
external: none
blocked_on: []
updated: 2026-10-07
source:
- STATUS.md
- notes/project-brief.md
next_action: 'Strand A done (built from the paper, replication matches UWA). Next: design simulation
  D1 on strand A''s engine, with the brms/PyMC choice; fetch strand B literature and data by hand
  (notes/literature-to-fetch.md); then fix analysis_plan.md before any outcome model.'
claim:
  argues: >-
    Stereotype content concentrates on the marked pole of evaluative oppositions, because rarity
    drives both an attribute's diagnosticity for a group and its overt morphological coding;
    tested by extending the Unkelbach, Weitzel and Alves (2026) simulation and on open
    stereotype data.
  provenance: drafted-from-status
  claim_updated: 2026-10-07
---

# STATUS
<!-- SUMMARY: Strand A built from the paper and run 2026-10-07 (replication matches UWA); next is design simulation D1, then fixing the plan; strand B data and literature still to fetch · status: active · updated: 2026-10-07 -->

## State

Scaffolded 2026-10-07 from Brett's brief (`notes/project-brief.md`, verbatim). The UWA paper is in the portfolio `literature/` as `unkelbach_weitzel_alves_2026_why_most_stereotypes_are_negative.{pdf,md}` (24 pp.; CC BY-NC-ND 4.0), read in full 2026-10-07. A ChatGPT deep-research report on markedness and stereotype negativity (`~/Downloads/deep-research-report(37).md`, 2026-10-07) is unverified LLM output, not a source. Strand A has run (2026-10-07; see item 4). Ingram et al. 2016 datasets downloaded; no strand B outcome data downloaded or opened; analysis plan not yet fixed.

## Next action

1. **Strand A** was built from UWA's published design (Brett, 2026-10-07), since `uwa_replication.py` was never supplied. If that script or UWA's ResearchBox code turns up, check it against `scripts/simulation/strand_a.py`.
2. **Strand B:** verify each source in `notes/source-verification.md`; download what exists to `data/raw/`; record URL, access date, SHA-256 and licence in `data/manifests/sources.csv`. Stop and report any that can't be obtained.
3. ~~Read UWA in full~~ (done 2026-10-07). Studies 1–2 materials and the simulation code at researchbox.org/4585 still to check.
4. Strand A built from UWA's published design and run (2026-10-07): replication matches the paper's text anchors and Figure 6; fresh-sample, diversity, group-size and consensus-split results in `results/strandA/SUMMARY.md` (generated from the CSVs). Still open in strand A: the mapping onto observed consensus (needs real data). `analysis_plan.md` has proposed revisions: strand B as one generative model with latent rarity, and design simulation D1 on strand A's engine before any outcome data. Next: D1; pick brms or PyMC with a reason (latent variables across submodels bear on it); fix the plan before any outcome model.
5. Missing literature: `notes/literature-to-fetch.md` (scripted downloads blocked; fetch by hand).

## Blockers

- Strand B literature and data: scripted downloads hit bot checks; fetch by hand (`notes/literature-to-fetch.md`).
- No trait-prevalence measure found yet (bears on H2, L1, L2; D1 will show how much it matters).
