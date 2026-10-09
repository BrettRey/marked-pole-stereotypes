---
slug: marked-pole-stereotypes
kind: paper
title: 'The marked-pole hypothesis and the UWA model of stereotype negativity'
stage: development
external: none
blocked_on: []
updated: 2026-10-09
source:
- STATUS.md
- notes/project-brief.md
next_action: 'D1 grid running (2026-10-09): chunks 0 and 11-15 local, 1-10 on cloud branches
  d1-grid-chunk-01..10; when all 16 finish, merge the branch CSVs into results/d1/grid/ and run
  summarise_d1.py grid/. Analysis-plan walkthrough with Brett at Part 6 (L1/L2 proposed; pending
  his answers on the human workload and what counts against the marking claim), then Part 7
  (strand A consensus mapping) and Part 8 (unwritten sections). D1b, D1c and D2 fake-data checks
  before FIXED. Fetch Hofstee 1995 and Hampson et al. 1987 (notes/literature-to-fetch.md).'
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
<!-- SUMMARY: Strand A done (replication matches UWA); D1 grid running locally and on cloud branches; analysis plan settled through H2, H1, multiverse, commonness judges and engine, L1/L2 proposed; D1b, D1c, D2 before FIXED; no strand B outcome data opened · status: active · updated: 2026-10-09 -->

## State

Scaffolded 2026-10-07 from Brett's brief (`notes/project-brief.md`, verbatim). The UWA paper is in the portfolio `literature/` as `unkelbach_weitzel_alves_2026_why_most_stereotypes_are_negative.{pdf,md}` (24 pp.; CC BY-NC-ND 4.0), read in full 2026-10-07. A ChatGPT deep-research report on markedness and stereotype negativity (`~/Downloads/deep-research-report(37).md`, 2026-10-07) is unverified LLM output, not a source. Strand A has run (2026-10-07; see item 4). Ingram et al. 2016 datasets downloaded; no strand B outcome data downloaded or opened; analysis plan not yet fixed.

## Next action

1. **Strand A** was built from UWA's published design (Brett, 2026-10-07), since `uwa_replication.py` was never supplied. If that script or UWA's ResearchBox code turns up, check it against `scripts/simulation/strand_a.py`.
2. **Strand B:** verify each source in `notes/source-verification.md`; download what exists to `data/raw/`; record URL, access date, SHA-256 and licence in `data/manifests/sources.csv`. Stop and report any that can't be obtained.
3. ~~Read UWA in full~~ (done 2026-10-07). Studies 1–2 materials and the simulation code at researchbox.org/4585 still to check.
4. Strand A built from UWA's published design and run (2026-10-07): replication matches the paper's text anchors and Figure 6; fresh-sample, diversity, group-size and consensus-split results in `results/strandA/SUMMARY.md` (generated from the CSVs). Still open in strand A: the mapping onto observed consensus (needs real data). `analysis_plan.md` has proposed revisions: strand B as one generative model with latent rarity, and design simulation D1 on strand A's engine before any outcome data. D1 is running (see front matter). Engine settled 2026-10-09: PyMC for the joint model, the acceptometer's Stan model for the commonness module. Fix the plan before any outcome model.
5. Missing literature: `notes/literature-to-fetch.md` (scripted downloads blocked; fetch by hand).

## Blockers

- Strand B literature and data: scripted downloads hit bot checks; fetch by hand (`notes/literature-to-fetch.md`).
- ~~No trait-prevalence measure found yet~~ (2026-10-09: Ziano et al.'s commonness panel, 149 traits, is the human anchor for calibrated model judges; human judges cover extreme traits; see `analysis_plan.md`, "Commonness judges"). Needs a blind second coder's time (pending Brett).
