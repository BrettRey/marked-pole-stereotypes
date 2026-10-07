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
next_action: 'Strand A needs uwa_replication.py, which the brief says was attached but is not on disk
  (Brett to supply). Meanwhile, strand B: verify each data source in notes/source-verification.md and
  record it in data/manifests/sources.csv; draft analysis_plan.md; choose brms or PyMC.'
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
<!-- SUMMARY: Set up 2026-10-07 from Brett's brief; nothing has run; strand A waits on uwa_replication.py, strand B starts with source verification and the analysis plan · status: set up · updated: 2026-10-07 -->

## State

Scaffolded 2026-10-07 from Brett's brief (`notes/project-brief.md`, verbatim). The UWA paper is in the portfolio `literature/` as `unkelbach_weitzel_alves_2026_why_most_stereotypes_are_negative.{pdf,md}` (24 pp.; CC BY-NC-ND 4.0), not yet read for the project. No data downloaded, no code run, no plan written.

## Next action

1. **Strand A** waits on `uwa_replication.py`. The brief calls it attached, but it wasn't in the message, and a disk-wide search (Spotlight, `~/Downloads`, `~/pdf-inbox`) found nothing on 2026-10-07. Brett to supply it; it goes in `scripts/simulation/` with its origin recorded.
2. **Strand B:** verify each source in `notes/source-verification.md`; download what exists to `data/raw/`; record URL, access date, SHA-256 and licence in `data/manifests/sources.csv`. Stop and report any that can't be obtained.
3. Read UWA in full (design, Figure 6, Studies 1–2 materials) before writing `analysis_plan.md`.
4. Draft `analysis_plan.md`; pick brms or PyMC with a reason; commit the plan before any outcome model.

## Blockers

- `uwa_replication.py` (strand A only).
