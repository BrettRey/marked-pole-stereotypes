---
slug: marked-pole-stereotypes
kind: paper
title: 'The marked-pole hypothesis and the UWA model of stereotype negativity'
stage: development
external: none
blocked_on: []
updated: 2026-10-10
source:
- STATUS.md
- notes/project-brief.md
next_action: 'Implementation runs in Codex tabs Brett drives (2026-10-09; HANDOFF-TO-CODEX.md).
  Lane N fixes the Norman pass-X parser and the failed-row retry, pilots Apple''s Vision OCR in
  place of GLM (no OpenRouter credit), then reruns wave 1. Lane S is running the twelve-fit
  D1c variant-timing stage approved in Roughdraft on 2026-10-10, with unchanged code and
  the passing pilot budget. Launch: logs/d1c-timings-launch-20261010T112136Z.json.
  Overnight limits lifted: finish timing, commit/push and run the D1c grid as authorized
  on 2026-10-10; stop only for a required design change. Lane S continues under the handoff.
  The D2 grid finished 2026-10-09 (results/d2/SUMMARY.md):
  L2 calibrated in its core; L1''s theta_m under-covers; judge bias is the main threat. Waiting on Brett: the D1 verdict (after
  D1c), threshold benchmarks, the Part 8 merge, the Koch licence reply. D2b waits for L1''s frame.'
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
<!-- SUMMARY: Strand A done (replication matches UWA); D1 grid done (indicator verdict after D1c); longer D1c baseline pilot passed both replicates; twelve-fit variant timing running; overnight limits lifted, commits/push and subsequent D1c grid authorized; D2 grid done (results/d2/SUMMARY.md); plan settled through H2, H1, L1, L2, multiverse and model judges only; implementation handed to Codex tabs (HANDOFF-TO-CODEX.md); Norman extraction: parser bug to fix, GLM replaced by Apple's Vision OCR (no OpenRouter credit); no strand B outcome data opened · status: active · updated: 2026-10-10 -->

## State

Scaffolded 2026-10-07 from Brett's brief (`notes/project-brief.md`, verbatim). The UWA paper is in the portfolio `literature/` as `unkelbach_weitzel_alves_2026_why_most_stereotypes_are_negative.{pdf,md}` (24 pp.; CC BY-NC-ND 4.0), read in full 2026-10-07. A ChatGPT deep-research report on markedness and stereotype negativity (`~/Downloads/deep-research-report(37).md`, 2026-10-07) is unverified LLM output, not a source. Strand A has run (2026-10-07; see item 4). Ingram et al. 2016 datasets downloaded; no strand B outcome data downloaded or opened; analysis plan not yet fixed.

## Next action

1. **Strand A** was built from UWA's published design (Brett, 2026-10-07), since `uwa_replication.py` was never supplied. If that script or UWA's ResearchBox code turns up, check it against `scripts/simulation/strand_a.py`.
2. **Strand B:** verify each source in `notes/source-verification.md`; download what exists to `data/raw/`; record URL, access date, SHA-256 and licence in `data/manifests/sources.csv`. Stop and report any that can't be obtained.
3. ~~Read UWA in full~~ (done 2026-10-07). Studies 1–2 materials and the simulation code at researchbox.org/4585 still to check.
4. Strand A built from UWA's published design and run (2026-10-07): replication matches the paper's text anchors and Figure 6; fresh-sample, diversity, group-size and consensus-split results in `results/strandA/SUMMARY.md` (generated from the CSVs). Still open in strand A: the mapping onto observed consensus (needs real data). `analysis_plan.md` has proposed revisions: strand B as one generative model with latent rarity, and design simulation D1 on strand A's engine before any outcome data. D1's grid finished 2026-10-09 (`results/d1/SUMMARY_grid.md`). Engine settled 2026-10-09: PyMC for the joint model, the acceptometer's Stan model for the commonness module. Fix the plan before any outcome model.
5. Missing literature: `notes/literature-to-fetch.md` (scripted downloads blocked; fetch by hand).

## Blockers

- D1c pilot convergence blocker resolved: both approved longer-run replicates passed (maximum R-hat 1.00624 and 1.00671; zero divergences). Variant timing is running; the measured-register upstream component has a recorded R-hat failure. Brett authorized further sampler work, commits/push and the subsequent D1c grid on 2026-10-10. The wider design assessment and D1 indicator verdict remain open; required design changes must be raised with Brett.
- Strand B literature and data: scripted downloads hit bot checks; fetch by hand (`notes/literature-to-fetch.md`).
- ~~No trait-prevalence measure found yet~~ (2026-10-09: Ziano et al.'s commonness panel, 149 traits, is the human anchor for calibrated model judges; human judges cover extreme traits; see `analysis_plan.md`, "Commonness judges"). No second human coder: model judges only (Brett, 2026-10-09).
- Norman (1967) pass B (GLM) dropped: no OpenRouter credit (Brett, 2026-10-09). Lane N pilots Apple's Vision OCR in its place (`HANDOFF-TO-CODEX.md`).
