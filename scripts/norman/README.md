# Extracting Norman (1967)
<!-- SUMMARY: Spec for transcribing the per-term tables of Norman (1967), ERIC ED014738: two independent passes (Tesseract; a vision model), reconciliation, a third pass on disagreements, range checks, provenance, and an audit; written before any extraction ran · status: spec 2026-10-09 · updated: 2026-10-09 -->

Source: Norman, W. T. (1967). *2800 personality trait descriptors: Normative operating characteristics for a university population.* University of Michigan, Department of Psychology, report 08310-1-T. ERIC ED014738, https://files.eric.ed.gov/fulltext/ED014738.pdf (full text authorized for distribution). Local copy: `data/raw/norman1967/` (gitignored; SHA-256 in `data/manifests/sources.csv`). Protocol from `analysis_plan.md`, "Existing human data" ("Extracting Norman's tables"). This is transcription, not judgment.

## What's transcribed

Appendices 1–14 (PDF pages 35–285, excluding the title page before each appendix): for each of about 2,800 terms, for men (left half of the page) and women (right half), the N, MEAN and S.D. of five tasks: 10-WR (social desirability, 1–9), DP-S (self), DP-A (a liked peer), DP-B (a peer the rater was indifferent to), DP-C (a disliked peer), each on 0–2 (Norman 1967, pp. 14–16). Also the ITEM NO. and the printed term. The correlation matrices aren't transcribed. Appendix 0 (pages 29–34, the alphabetical list with CAT and FORM) is transcribed for term spellings.

## Passes

1. **Render.** Each page at 300 dpi in greyscale with `pdftoppm`, cropped into a left and a right half with a small overlap.
2. **Pass A, Tesseract 5.5** on each half (`--psm 6`). A parser finds each block by its ITEM NO. line and takes the last three numbers of each task row as N, MEAN, S.D.
3. **Pass B, a vision model**, independently: `z-ai/glm-5.3-flash` through the OpenRouter Chat Completions API (the source is a public document, so the external route is allowed), given each half-page image and asked for strict JSON: item number, term, and for each of the five tasks N, MEAN, S.D. as printed. Temperature 0. The prompt is fixed in `extract.py`.
4. **Reconcile** by page, side, item number and task. A value is accepted when A and B agree exactly.
5. **Pass C on disagreements:** a second vision model (local `gemma3:12b` through Ollama) on the same half-page image; a value is accepted when two of the three passes agree. Values still unresolved are flagged and transcribed from the image by a Claude subagent, recorded as such.
6. **Range checks:** N an integer from 0 to 50 for each sex; MEAN within the scale (1–9 for 10-WR, 0–2 otherwise); S.D. from 0 to 4 (10-WR) or 0 to 1.5 (others); the five task Ns for one block can't exceed the block's largest N. Failures are flagged, not corrected silently.
7. **Audit:** a random sample of rows on which A and B agreed, oversampling the most extreme means and terms containing a negator, is checked against the page images by a Claude subagent, which reports only the number of errors found and the corrections, not commentary on the values. The sample size is 150 rows; if the error rate in the audit exceeds 1%, the whole file is re-audited.
8. **Terms** are matched to Appendix 0's spellings by item list and alphabetical order, with fuzzy matching only as a check; mismatches are flagged.

## Firewall

The extracted values aren't joined to morphology, and aren't inspected by the main session beyond counts and range-check summaries, until L1's frame is frozen (`analysis_plan.md`, "L1"). The pilot uses pages whose terms contain no negator.

## Outputs (gitignored, `data/raw/norman1967/`)

`passA.csv`, `passB.jsonl`, `passC.jsonl`, `reconciled.csv` (page, side, block, item number, printed term, matched term, task, N, MEAN, S.D., source of each value, flags), `audit.csv`, and `extraction_log.json` (versions, model IDs, prompt hash, timings). Whether derived values can be published depends on the report's terms of reuse, still to be settled; until then nothing extracted goes into git.

## Order of running

Spec and code committed first; then a pilot on two pages whose terms contain no negator, with A, B and C compared by hand on those pages only; then the full run; then the audit.
