---
slug: marked-pole-stereotypes
kind: paper
title: 'The marked-pole hypothesis and the UWA model of stereotype negativity'
stage: development
external: none
blocked_on: []
updated: 2026-10-11
source:
- STATUS.md
- notes/project-brief.md
next_action: >-
  Review notes/next-stage-decisions-2026-10-11.md: joint/cut reporting,
  a reduced HF simulation proposal and directional falsifiers. Complete the
  two already-authorized recovery fits; the 240-cell grid stays stopped.
  Six-pair lexical review is complete; full coding and commonness collection
  await the frame/model/budget specification. Resume Norman's parser and
  Vision pilot next, preserving its values firewall. Run state lives in reports
  and logs; DECISIONS records scientific and scope decisions only.
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
<!-- SUMMARY: Strand A complete; analysis plan not FIXED. D1c's 240-cell grid stays stopped; the 16-configuration baseline has 14 complete and two authorized recovery fits running. Current run state: results/d1c/baseline-recovery-20261011/REPORT.md. Joint/cut differences require paired reporting and replicated assessment. Six-pair lexical review complete: 11 answers, one timeout, five pairs retain candidate alignments, no exact complement established. Full vocabulary and commonness collection unlaunched. Reduced HF design, falsifier wording and lexical budget are proposed in notes/next-stage-decisions-2026-10-11.md. Norman parser/Vision work remains next. Draws stay local; summaries and hashes are public · status: active · updated: 2026-10-11 -->

## State

Scaffolded 2026-10-07 from Brett's brief (`notes/project-brief.md`, verbatim). The UWA paper is in the portfolio `literature/` as `unkelbach_weitzel_alves_2026_why_most_stereotypes_are_negative.{pdf,md}` (24 pp.; CC BY-NC-ND 4.0), read in full 2026-10-07. A ChatGPT deep-research report on markedness and stereotype negativity (`~/Downloads/deep-research-report(37).md`, 2026-10-07) is unverified LLM output, not a source. Strand A has run (2026-10-07; see item 4). Ingram et al. 2016 datasets downloaded; no strand B outcome data downloaded or opened; analysis plan not yet fixed.

## Next action

1. Review the [next-stage decisions](notes/next-stage-decisions-2026-10-11.md) and [completed six-pair review](notes/lexical-six-pair-report-2026-10-11.md).
2. Collect the two already-authorized HF recovery fits; see the [live report](results/d1c/baseline-recovery-20261011/REPORT.md). No full-grid restart.
3. Resume Norman's pass-X parser repair and Vision pilot on pages 40–41 under the existing [handoff](HANDOFF-TO-CODEX.md), before further simulation expansion.
4. Before full lexical coding, fix the source coverage, discovery audit, model/version and allowance budget. Before commonness collection, also settle pair weighting and release targets/descriptions.
5. Integrate agreed plan amendments before FIXED. Empirical-design calibration waits for the frozen frame and actual source response structure.

## Prior task records

The dated records below are retained for traceability; current run details belong in their linked reports and logs.


1. **Strand A** was built from UWA's published design (Brett, 2026-10-07), since `uwa_replication.py` was never supplied. If that script or UWA's ResearchBox code turns up, check it against `scripts/simulation/strand_a.py`.
2. **Strand B:** verify each source in `notes/source-verification.md`; download what exists to `data/raw/`; record URL, access date, SHA-256 and licence in `data/manifests/sources.csv`. Stop and report any that can't be obtained.
3. ~~Read UWA in full~~ (done 2026-10-07). Studies 1–2 materials and the simulation code at researchbox.org/4585 still to check.
4. Strand A built from UWA's published design and run (2026-10-07): replication matches the paper's text anchors and Figure 6; fresh-sample, diversity, group-size and consensus-split results in `results/strandA/SUMMARY.md` (generated from the CSVs). Brett dropped inverse calibration from observed consensus and retained the conditional forward map on 2026-10-09 (`analysis_plan.md`, Hypotheses). `analysis_plan.md` has proposed revisions: strand B as one generative model with latent rarity, and design simulation D1 on strand A's engine before any outcome data. D1's grid finished 2026-10-09 (`results/d1/SUMMARY_grid.md`). Engine settled 2026-10-09: PyMC for the joint model, the acceptometer's Stan model for the commonness module. Fix the plan before any outcome model.
5. Missing literature: `notes/literature-to-fetch.md` (scripted downloads blocked; fetch by hand).
6. Lane S drafts: `notes/threshold-examples-draft-2026-10-10.md` and `notes/plan-part8-draft-2026-10-10.md` now follow Brett's direction to report estimated size, uncertainty and changes across assumptions, with substantive benchmarks unset and no benchmark-selection checklist. The analyst handles later integration and reconciliation of older threshold language in the plan. `notes/d1b-design-draft-2026-10-10.md` maps identification and implementation requirements. The plan itself is unchanged. D1b still needs its numerical specification, code, pilot and grid.
7. Koch et al. (2024): Alex Koch's email of 2026-10-09, supplied by Brett on 2026-10-10, gives permission for research use and publication of derived summaries; his follow-up requests citation. Cite the paper (doi:10.1037/pspa0000383) and OSF project (https://osf.io/eadcm/). Record this as explicit author permission, not an inferred CC BY licence. The permission blocker is cleared; no Koch data have been downloaded or opened in this session. Record file-level provenance when retrieving them and preserve the existing analysis-plan and outcome-data gates.
8. D1c initial grid: run `20261010T161109492336Z` remains stopped after 17.4 minutes and zero completed cells. The subsequent distributed cut for cell 10, replicate 0 is complete: cloud 0; local 1, 3 and 7; HF 2, 4, 5 and 6. Every component and the shared upstream fit passed parameter/contrast diagnostics, with zero divergences. The collector verified all eight at 23:03:37 UTC. The reporting-only assembler initially rejected the actual register-covariate array shape; the published correction at `32086c8` fixed the check and test fixture. It then replayed the original summary calculation from saved components without fitting anything. The completed report is `results/d1c/complete-cut-20261010/REPORT.md`, with four contrasts, equal component weights and 128,000 draws per contrast. Independent array/hash/arithmetic checks pass; maximum parameter R-hat is 1.00533. Twelve assembly/collection tests pass. The local queue and HF batch are finished. Combined HF trial/batch compute is estimated at USD .159 from provider duration, not an invoice; the original USD 10 authorization was not enlarged. This completes one artificial dataset, not D1c calibration or the full 240-cell grid. Eight selected upstream draws do not by themselves establish outer-integration accuracy. The reviewed design-assessment tools and input registry remain in `scripts/design_assessment/`; freeze the empirical vocabulary, source response structure, measurement assumptions and justified replication/cost plan before calibration. D1b remains preparatory.

9. Lexical frame: the 40-form pilot and bounded six-pair review are complete. The [six-pair report](notes/lexical-six-pair-report-2026-10-11.md) traces all sixteen saved alignments: twelve retained with restrictions, three unresolved and one rejected, within six dependent pairs. Eleven model calls returned; one timed out, without retry. Five pairs retain source-supported candidates; no exact complement is established. The forty-form mapping separates lexical identity, interpretation, target and presentation. Full coding, descriptions and commonness collection have not begun. The [adopted protocol](notes/lexical-protocol-decisions-2026-10-11.md) fixes US residents of all ages in 2026 and separate characteristic/state targets. Broader supplementary dictionary coverage, missed-pair detection, pair weighting and model/allowance costs remain in the full-frame specification.

10. Parallel continuation: the bounded comparison from `47e55ad` is complete. UWA joint cell 4 finished on the Mac; Nicolas joint cell 124 and the eight-component cut for cell 130 finished on five HF machines. All diagnostics pass; all provider jobs, the Mac worker and original monitor ended. The report is `results/d1c/paired-batch-20261010/REPORT.md`; observed HF compute estimate USD .321, not an invoice. The completed UWA cut is reused. These are registered engineering comparisons, not replicated calibration.

11. Baseline expansion: Brett authorized the fixed 16-cell factorial and total HF spending of USD 15. The batch from `94eb4e4` ended with 14 configurations complete; all 78 component/joint diagnostics pass, zero divergences, maximum R-hat 1.0081061. All saved component hashes and reported summary arithmetic check out. Host `joint-0` failed at 01:46:51 UTC on 2026-10-11 with a bucket-write `OSError [Errno 5]`; the controller stopped cells 0 and 12 before either had a complete checkpoint. Preserve `results/d1c/baseline-batch-20261010/REPORT.md` and the partial exports/provider log under `results/d1c/baseline-recovery-20261011/original-failure/`. Observed extension compute USD 1.7975; with earlier jobs, USD 2.2775 before recovery, not an invoice. A diagnosed infrastructure recovery is published at `36b9af1`: only cells 0 and 12 run again, once each, on separate HF machines. Both jobs are RUNNING; the scientific code, data, seeds, sampler and original module signatures are unchanged. Export I/O retries no longer kill a live sampler. Thirty-eight tests pass. Maximum recovery cost USD .72; conservative total reservation USD 13.80 under USD 15. Receipt: `logs/d1c-baseline-recovery-launch-20261011.json`; monitor PID 4435; current combined report: `results/d1c/baseline-recovery-20261011/REPORT.md`. No completed fit or diagnostic failure is repeated. The full grid remains stopped.

## Blockers

- D1c baseline pilot convergence blocker resolved: both approved longer-run replicates passed (maximum R-hat 1.00624 and 1.00671; zero divergences). Completed variant timing has four R-hat failures: UWA measured-register upstream/downstream and Nicolas measured-register upstream/joint. All eight contrast checks passed; all twelve fits had zero divergences. The initial grid was stopped by Brett because of its roughly 18-day projected cost; no cell completed. The eight components of one cut are complete and assembled, with all diagnostics passing (HF budget USD 10 total; estimated trial/batch compute USD .159); the full-grid resource decision remains open. One replicate per cell cannot establish calibration. The wider design assessment and D1 indicator verdict remain open; required design changes must be raised with Brett.
- Strand B literature and data: scripted downloads hit bot checks; fetch by hand (`notes/literature-to-fetch.md`).
- ~~No commonness measure found yet~~ (2026-10-09: Ziano et al.'s display-frequency panel, 149 traits, is a human anchor for calibrated model judges; see `analysis_plan.md`, "Commonness judges"). No new human judges: unsupported vocabulary remains a separately labelled model-judged population (Brett, 2026-10-09).
- Norman (1967) pass B (GLM) dropped: no OpenRouter credit (Brett, 2026-10-09). Lane N pilots Apple's Vision OCR in its place (`HANDOFF-TO-CODEX.md`).
