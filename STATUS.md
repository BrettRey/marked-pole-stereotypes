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
  export checks, independent scheduling and both queues pass 42 tests.
  Cloud owns component 0 from 0401100; its upstream checkpoint at 942dfd8
  passed and was verified; its downstream export at e4b8310 also passed and
  has been collected. All eight components are verified complete; all
  downstream and upstream diagnostics pass, with zero divergences. Local
  components 1, 3 and 7 and HF components 2, 4, 5 and 6 are complete; the
  local queue and HF batch have ended. The combined trial/batch provider-time
  estimate is USD .159, not an invoice, within the USD 10 authorization.
  The first reporting-only assembly stopped on an incorrect shape check for
  the three register covariates; the correction was published at 32086c8.
  The saved components were then assembled without any model rerun.
  Report: results/d1c/complete-cut-20261010/REPORT.md. All eight components
  receive equal weight; 128,000 draws are retained per scalar contrast.
  Independent verification confirms the component arrays and summary
  arithmetic. Twelve assembly/collection tests pass. This is one artificial
  dataset and an eight-component outer approximation, not calibration.
  The 240-cell grid stays stopped. A new bounded comparison is now running from
  47e55ad: UWA joint cell 4 on the Mac, Nicolas joint cell 124 on its own HF
  machine, and Nicolas cut cell 130 across four HF machines. All five HF jobs
  were accepted and are RUNNING; Mac sampling has started. The eight cut
  components start after their shared upstream checkpoint is ready. There
  is no local serial queue. Five eight-hour HF timeouts cap new compute at
  USD 1.20 within the standing USD 10 budget. Monitor PID 77285 collects
  outputs and assembles paired summaries without refitting. Nineteen tests
  pass. The larger 16-configuration proposal awaits scope selection.
  Diagnostic and timing detail for the completed first cut remains in
  results/d1c/parallel-components-20261010/REPORT.md. Design-assessment
  reporting and budget tools are
  implemented in scripts/design_assessment; the reviewed requirement is in
  analysis_plan.md. Empirical-design calibration remains pending frozen
  vocabulary, existing source-study response structure, measurement assumptions and a justified
  replication/cost plan. No new calibration fits have been launched.
  Lexical source import and the 40-term pilot are complete: 14,082 candidate
  forms, 25 pilot forms with supported adjective meanings and six provisional
  prefix pairs. Report: notes/lexical-frame-pilot-report-2026-10-10.md; Brett
  completed Roughdraft review and all three comments are addressed. Both original model passes completed; the revised
  Claude pair screen timed out at its fixed 15-minute limit. Source and
  sense audits are complete; 17 tests pass. No frame freeze, full-vocabulary
  coding or commonness collection has occurred. Scope/target proposals and
  a workable bounded pair-screen protocol remain before any full pass.
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
<!-- SUMMARY: Strand A done (conditional forward map retained); D1 grid done (indicator verdict after D1c); longer D1c baseline pilot passed both replicates; twelve-fit timing complete (four R-hat failures, zero divergences); initial 240-cell sweep stopped at Brett’s request and remains stopped. All eight distributed components of cell 10/replicate 0 are complete, verified and assembled: upstream and every downstream fit passed with zero divergences. Original report-only shape-check error corrected without any refit; 12 assembly/collection tests pass. Full report: results/d1c/complete-cut-20261010/REPORT.md. One artificial dataset does not establish calibration; empirical-design inputs and replication budget remain unresolved. The first queues ended; their HF compute estimate is USD .159, not an invoice. New parallel baseline comparison launched from 47e55ad: one Mac joint fit, one HF joint fit and four HF machines for the eight Nicolas cut components. All five HF jobs are RUNNING; new compute ceiling USD 1.20; 19 tests pass. The larger 16-configuration proposal awaits scope selection. Lexical import and reviewed 40-form pilot complete (25 forms support eligible adjectives, six provisional prefix pairs); one revised pair recheck timed out; frame not frozen, no full coding or commonness collection. Design-assessment tools implemented; D1b preparatory only; Koch permission confirmed; D2 grid done; no new strand B outcome data opened · status: active · updated: 2026-10-10 -->

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
8. D1c initial grid: run `20261010T161109492336Z` remains stopped after 17.4 minutes and zero completed cells. The subsequent distributed cut for cell 10, replicate 0 is complete: cloud 0; local 1, 3 and 7; HF 2, 4, 5 and 6. Every component and the shared upstream fit passed parameter/contrast diagnostics, with zero divergences. The collector verified all eight at 23:03:37 UTC. The reporting-only assembler initially rejected the actual register-covariate array shape; the published correction at `32086c8` fixed the check and test fixture. It then replayed the original summary calculation from saved components without fitting anything. The completed report is `results/d1c/complete-cut-20261010/REPORT.md`, with four contrasts, equal component weights and 128,000 draws per contrast. Independent array/hash/arithmetic checks pass; maximum parameter R-hat is 1.00533. Twelve assembly/collection tests pass. The local queue and HF batch are finished. Combined HF trial/batch compute is estimated at USD .159 from provider duration, not an invoice; the original USD 10 authorization was not enlarged. This completes one artificial dataset, not D1c calibration or the full 240-cell grid. Eight selected upstream draws do not by themselves establish outer-integration accuracy. The reviewed design-assessment tools and input registry remain in `scripts/design_assessment/`; freeze the empirical vocabulary, source response structure, measurement assumptions and justified replication/cost plan before calibration. D1b remains preparatory.

9. Lexical frame: source import and the authorized 40-term pilot are complete. Anderson supplies 555 entries; Warriner supplies 13,915 rows/13,905 normalized forms; overlap is 378 and union 14,082. The source audit finds eligible adjective meanings under 25 pilot forms, excludes the supplied adjective meanings of four forms, and preserves two scope uncertainties plus nine forms with no attested adjective in the checked resources. Six provisional prefix pairs require interpretation/reading and target specification before collection. Both original model-family passes completed; the revised Claude pair screen timed out at 900 seconds, with no further retry. Brett reviewed `notes/lexical-frame-pilot-report-2026-10-10.md` in Roughdraft; the replies distinguish lexical category from function, identify uniform as a uni-/un- detector error, and separate the calibrated arm’s average-American wording from the description arm’s still-unsettled population/time targets. Full-vocabulary coding and commonness collection have not begun. Complete private audit tables and public aggregate accounting are linked from the report.

10. Parallel continuation: after Brett asked to continue and challenged serial scheduling, launched the bounded comparison in `scripts/d1c/PAIRED-BATCH.md` from published source `47e55ad`. UWA joint cell 4 runs on the Mac; Nicolas joint cell 124 runs on its own HF machine; Nicolas cut cell 130 uses four other HF machines, with components 0–1, 2–3, 4–5 and 6–7 assigned respectively. The shared upstream fit runs once on machine 0. All five HF jobs were accepted and report RUNNING; Mac sampling started. Both joints are independent of the upstream work. The five eight-hour timeouts cap new compute at USD 1.20; conservative historical-plus-current reservations total USD 3.36 within the USD 10 authorization. Nineteen checks pass. The durable monitor (PID 77285) collects checkpoints and builds `results/d1c/paired-batch-20261010/REPORT.md`. Reuse the completed UWA cut. No full-grid restart or larger batch was launched.

## Blockers

- D1c baseline pilot convergence blocker resolved: both approved longer-run replicates passed (maximum R-hat 1.00624 and 1.00671; zero divergences). Completed variant timing has four R-hat failures: UWA measured-register upstream/downstream and Nicolas measured-register upstream/joint. All eight contrast checks passed; all twelve fits had zero divergences. The initial grid was stopped by Brett because of its roughly 18-day projected cost; no cell completed. The eight components of one cut are complete and assembled, with all diagnostics passing (HF budget USD 10 total; estimated trial/batch compute USD .159); the full-grid resource decision remains open. One replicate per cell cannot establish calibration. The wider design assessment and D1 indicator verdict remain open; required design changes must be raised with Brett.
- Strand B literature and data: scripted downloads hit bot checks; fetch by hand (`notes/literature-to-fetch.md`).
- ~~No commonness measure found yet~~ (2026-10-09: Ziano et al.'s display-frequency panel, 149 traits, is a human anchor for calibrated model judges; see `analysis_plan.md`, "Commonness judges"). No new human judges: unsupported vocabulary remains a separately labelled model-judged population (Brett, 2026-10-09).
- Norman (1967) pass B (GLM) dropped: no OpenRouter credit (Brett, 2026-10-09). Lane N pilots Apple's Vision OCR in its place (`HANDOFF-TO-CODEX.md`).
