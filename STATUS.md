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
  place of GLM (no OpenRouter credit), then reruns wave 1. Lane S completed all twelve
  D1c component timings: eight parameter passes, four R-hat failures, eight contrast
  passes and zero divergences. Summary: results/d1c/TIMING-SUMMARY-2026-10-10.md.
  Brett stopped the local grid on 2026-10-10 at 16:28 UTC after the roughly
  18-day estimate. Run 20261010T161109492336Z ended after 17.4 minutes with zero
  completed cells; the parent and all three workers are confirmed stopped.
  Preserve the interrupted record; the full grid stays stopped. Brett authorized
  component recovery and one Claude-cloud benchmark: upstream preparation and
  downstream component 0 of original cell 10, replicate 0. Recovery and cloud
  export checks, independent scheduling and cleanup pass 31 tests. Claude cloud
  owns component 0 from published 0401100; its upstream checkpoint at 942dfd8
  passed diagnostics and was checksum-verified. Brett then authorized concurrent
  local work and one HF trial within USD 10 total. Local component 1 is sampling
  at nice 10, PID 14963, source 827b5b9. HF component 2 is running in job
  6aca739c095c578089314dc3, source 89f299a, after cancelling a malformed queued
  setup submission before any model execution. The HF job has a 24-hour/.72
  compute ceiling; setup and persistent upstream export are checksum-verified.
  No automatic retry. Components
  3–7 remain unassigned. Follow the three component records, verify exported
  outputs, and compare runtime/memory/cost before broader assignment. Each
  stops at its component boundary. D1c calibration remains incomplete.
  Brett chose reporting estimated size, uncertainty
  and changes across assumptions, with substantive benchmarks unset. Both lane-S
  reporting drafts now follow that direction; the analyst handles later plan
  integration. D1b has a preparatory design note but no executable specification or pilot.
  The D2 grid finished 2026-10-09 (results/d2/SUMMARY.md):
  L2 calibrated in its core; L1''s theta_m under-covers; judge bias is the main threat. Waiting on Brett: the D1 verdict (after
  D1c). Koch data permission is confirmed by Alex Koch''s 2026-10-09 email,
  supplied by Brett on 2026-10-10; cite the paper and OSF project. Data retrieval
  and provenance remain to be completed. D2b waits for L1''s frame.'
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
<!-- SUMMARY: Strand A done (conditional forward map retained); D1 grid done (indicator verdict after D1c); longer D1c baseline pilot passed both replicates; twelve-fit timing complete (four R-hat failures, zero divergences), initial full-cell local sweep stopped at Brett’s request after 17.4 minutes, zero cells completed, all workers stopped; full grid remains stopped, Claude-cloud component 0 in progress, local component 1 sampling, HF component 2 running within USD 10 budget, all using verified exported upstream draws; recovery/scheduling/export checks pass 31 tests; D1c calibration remains incomplete; Brett chose effect size, uncertainty and sensitivity reporting with substantive benchmarks unset, incorporated into both drafts; D1b design note prepared; Koch data permission confirmed by email, with citation requested; D2 grid done (results/d2/SUMMARY.md); plan settled through H2, H1, L1, L2, multiverse and model judges only; implementation handed to Codex tabs (HANDOFF-TO-CODEX.md); Norman extraction: parser bug to fix, GLM replaced by Apple's Vision OCR (no OpenRouter credit); no strand B outcome data opened · status: active · updated: 2026-10-10 -->

## State

Scaffolded 2026-10-07 from Brett's brief (`notes/project-brief.md`, verbatim). The UWA paper is in the portfolio `literature/` as `unkelbach_weitzel_alves_2026_why_most_stereotypes_are_negative.{pdf,md}` (24 pp.; CC BY-NC-ND 4.0), read in full 2026-10-07. A ChatGPT deep-research report on markedness and stereotype negativity (`~/Downloads/deep-research-report(37).md`, 2026-10-07) is unverified LLM output, not a source. Strand A has run (2026-10-07; see item 4). Ingram et al. 2016 datasets downloaded; no strand B outcome data downloaded or opened; analysis plan not yet fixed.

## Next action

1. **Strand A** was built from UWA's published design (Brett, 2026-10-07), since `uwa_replication.py` was never supplied. If that script or UWA's ResearchBox code turns up, check it against `scripts/simulation/strand_a.py`.
2. **Strand B:** verify each source in `notes/source-verification.md`; download what exists to `data/raw/`; record URL, access date, SHA-256 and licence in `data/manifests/sources.csv`. Stop and report any that can't be obtained.
3. ~~Read UWA in full~~ (done 2026-10-07). Studies 1–2 materials and the simulation code at researchbox.org/4585 still to check.
4. Strand A built from UWA's published design and run (2026-10-07): replication matches the paper's text anchors and Figure 6; fresh-sample, diversity, group-size and consensus-split results in `results/strandA/SUMMARY.md` (generated from the CSVs). Brett dropped inverse calibration from observed consensus and retained the conditional forward map on 2026-10-09 (`analysis_plan.md`, Hypotheses). `analysis_plan.md` has proposed revisions: strand B as one generative model with latent rarity, and design simulation D1 on strand A's engine before any outcome data. D1's grid finished 2026-10-09 (`results/d1/SUMMARY_grid.md`). Engine settled 2026-10-09: PyMC for the joint model, the acceptometer's Stan model for the commonness module. Fix the plan before any outcome model.
5. Missing literature: `notes/literature-to-fetch.md` (scripted downloads blocked; fetch by hand).
6. Lane S drafts: `notes/threshold-examples-draft-2026-10-10.md` and `notes/plan-part8-draft-2026-10-10.md` now follow Brett's direction to report estimated size, uncertainty and changes across assumptions, with substantive benchmarks unset and no benchmark-selection checklist. The analyst handles later integration and reconciliation of older threshold language in the plan. `notes/d1b-design-draft-2026-10-10.md` maps identification and implementation requirements. The plan itself is unchanged. D1b still needs its numerical specification, code, pilot and grid.
7. Koch et al. (2024): Alex Koch's email of 2026-10-09, supplied by Brett on 2026-10-10, gives permission for research use and publication of derived summaries; his follow-up requests citation. Cite the paper (doi:10.1037/pspa0000383) and OSF project (https://osf.io/eadcm/). Record this as explicit author permission, not an inferred CC BY licence. The permission blocker is cleared; no Koch data have been downloaded or opened in this session. Record file-level provenance when retrieving them and preserve the existing analysis-plan and outcome-data gates.
8. D1c initial grid: run `20261010T161109492336Z` was stopped at Brett’s explicit request after 17.4 minutes and zero completed cells. The full local grid stays stopped. One cloud benchmark is running from published source commit `0401100`, session `session_01QyT922V6vtqQgFdfab6ps8`, branch `claude/d1c-cloud-benchmark-qjwn7f`. The upstream checkpoint passed (R-hat 1.00363, minimum ESS 1236.4, zero divergences), was exported at `942dfd8`, and its checksum and latent arrays were verified. Downstream component 0 is pending. Brett additionally authorized local component 1 (PID 14963, nice 10, source `827b5b9`) and HF component 2 (job `6aca739c095c578089314dc3`, source `89f299a`). HF has one attempt, a 24-hour/.72 compute ceiling and a persistent private output bucket within the USD 10 total budget. Its exact package/source checks passed; the exported upstream archive was retrieved and checksum-verified, and the container confirms 32 GB RAM (`logs/d1c-hf-startup-verification-20261010.json`). An initial malformed HF setup command was cancelled while queued, before any model fit. Components 3–7 are unassigned; these partial results are not a full cut or calibration. Launch records: `logs/d1c-cloud-launch-20261010.json`, `logs/d1c-local-component-launch-20261010.json`, and `logs/d1c-hf-job-20261010.json`. D1b remains at preparatory-note stage.

## Blockers

- D1c baseline pilot convergence blocker resolved: both approved longer-run replicates passed (maximum R-hat 1.00624 and 1.00671; zero divergences). Completed variant timing has four R-hat failures: UWA measured-register upstream/downstream and Nicolas measured-register upstream/joint. All eight contrast checks passed; all twelve fits had zero divergences. The initial grid was stopped by Brett because of its roughly 18-day projected cost; no cell completed. Three distinct components are assigned across Claude cloud, the Mac and HF (HF budget USD 10 total); broader runs still need a new agreed resource scope. One replicate per cell cannot establish calibration. The wider design assessment and D1 indicator verdict remain open; required design changes must be raised with Brett.
- Strand B literature and data: scripted downloads hit bot checks; fetch by hand (`notes/literature-to-fetch.md`).
- ~~No commonness measure found yet~~ (2026-10-09: Ziano et al.'s display-frequency panel, 149 traits, is a human anchor for calibrated model judges; see `analysis_plan.md`, "Commonness judges"). No new human judges: unsupported vocabulary remains a separately labelled model-judged population (Brett, 2026-10-09).
- Norman (1967) pass B (GLM) dropped: no OpenRouter credit (Brett, 2026-10-09). Lane N pilots Apple's Vision OCR in its place (`HANDOFF-TO-CODEX.md`).
