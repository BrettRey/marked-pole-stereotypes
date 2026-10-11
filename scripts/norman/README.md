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

## After pilot 1 (2026-10-09)

Pilot 1 failed before any comparison: one vision reply came back empty because the model spent its token budget on reasoning (about 6,300 tokens at default settings), and a 300 dpi PNG upload broke the connection. Changes: the vision passes get greyscale JPEGs at 200 dpi (same crops), the vision request sets low reasoning effort (a test call returned in 6 seconds with about 1,100 output tokens), and an empty reply counts as a failure and is retried. Tesseract still reads the 300 dpi PNGs. Pilot outputs were cleared and the pilot rerun.

## After pilot 2 (2026-10-09)

Scored against a gold transcription of the four pilot half-pages (240 rows, by a Claude subagent working from the 300 dpi images; it cost about 300,000 tokens, so it isn't repeated at scale): rows exactly right, Codex (gpt-6.1-sol through the read-only wrapper with the image attached) 212 of 239, GLM-5.3-flash at low reasoning 163, at default reasoning 148, Tesseract (column-wise, revised) 97. Agreement between two different model families was almost always correct (Codex with Tesseract 88 of 88; Codex with GLM 152 of 153; GLM with Tesseract 89 of 90), agreement between two settings of the same model less so (116 of 121). The local gemma3 pass was dropped (garbage values, minutes per page). New procedure: passes A (Tesseract), B (GLM, low reasoning) and X (Codex, about 10,600 tokens per half-page) on every half-page; a value is accepted when two families agree (X=B, X=A, or A=B); unresolved rows get a second, zoomed Codex read (X2), accepted when it matches A, B or X; anything else is flagged. Codex replaces the Claude subagent for adjudication, at Brett's request to move work off Claude. The audit is redesigned so that it uses a third model family on zoomed block crops, compared by script, with the main session seeing counts only. The full run goes in waves.

## Order of running

Spec and code committed first; then a pilot on two pages whose terms contain no negator, with A, B and C compared by hand on those pages only; then the full run; then the audit.


## Pass-X repair and Vision pilot specification (2026-10-11; prospective)

Brett approved resuming this bounded handoff after the simulation and lexical
protocol decisions. Keep the existing pages 40–41 gold and the values firewall.
No new commonness judgments or human ratings are introduced.

Pass X now writes its final answer using `--output-last-message`, retains stdout
and stderr separately, records tokens and checks the model/effort header. Freeze
the existing instrument explicitly as `gpt-6.1-sol`, effort `none`, with the same
prompt and 300-dpi images; Codex CLI is 0.161.0 (the old handoff used 0.160.0).
Record this software change. Empty/malformed answers, process failures, header
mismatches and invalid block schemas remain failed attempts. One call per selected
failed/missing half-page per invocation, no internal retries, 900-second timeout.
Keep attempt records append-only and select the last non-null result; later failed
attempts cannot hide an earlier success. Raw transcriptions and attempt streams
stay under the excluded source-data directory, following the Norman-specific
firewall and redistribution rule rather than the generic review-publication rule.

Pass V uses local Apple Vision via `pyobjc-framework-Vision==12.2.2`, accurate
recognition, `en-US`, language correction off; Pillow stays at 11.3.0. The
preflight machine is macOS 26.6.2. It independently locates headers and recognizes
values with Vision, using the existing per-column crop geometry. Unlike historical
pass A, it makes no dropped-decimal or scale-based digit repairs. Shared crop
geometry remains a possible source of correlated errors; agreement is checked
against the gold rather than assumed correct.

Run X and V only on the four pilot halves; reuse existing A and B. The scorer
reports exact three-number rows among the 239 fully readable gold rows (one of
240 is excluded), and correctness of V=X, V=A, X=A and B=X agreements. Compare
V=X with the existing benchmark of one wrong row among 153 B=X agreements,
considering both errors and the number of agreements. A small agreement subset
is not evidence of comparable reliability. If the existing acceptance requirement
is not met, report that before any wave; do not automatically tune and repeat.

If accepted, run the first 60 table pages with four X workers and one local V
worker, selecting passes X,V only. Reuse completed records; no OpenRouter key
lookup, new B calls or local Gemma calls. Retain the historical B results for
reconciliation. Add X=V and A=V to cross-engine agreement, keep unresolved and
range-failing rows explicit, and require non-null numbers before counting agreement.
Outside pages 40–41, public reports contain counts, timings, hashes and range
summaries only. No extracted values are joined to morphology. Later waves and
the third-engine audit remain separate work after wave 1 is checked.

Commands (spec and code must be published first):

```sh
uv run --quiet --no-project --with pillow==11.3.0 --with pyobjc-framework-Vision==12.2.2 python scripts/norman/extract.py pilot --pages 40,41 --passes X,V
uv run --quiet --no-project --with pillow==11.3.0 --with pyobjc-framework-Vision==12.2.2 python scripts/norman/score_pilot.py
# Only after the pilot meets the existing acceptance requirement:
uv run --quiet --no-project --with pillow==11.3.0 --with pyobjc-framework-Vision==12.2.2 python scripts/norman/extract.py run --first 0 --count 60 --workers 4 --passes X,V
```

The 11 regression tests exercise stream parsing, final-message priority, schema
and instrument failures, append-only failure recovery, selected-pass isolation,
and incomplete-value reconciliation. These are software fixtures, not research
observations. See `logs/norman-repair-tests-20261011.txt`.

### Pilot 3 setup correction (2026-10-11)

The first published attempt (8dc05b4) returned no transcriptions: four X calls
were rejected before inference because the API does not accept an explicitly
requested reasoning effort `none` for gpt-6.1-sol. The historical wrapper had
omitted that parameter; its CLI header's `none` was not evidence of a resolved
provider effort. Restore the omission, keep the model explicit and record both
requested effort (unset) and reported header (none). This restores the original
request semantics rather than silently choosing a new effort. Keep all four
failures and make one corrected attempt per pilot half-page.

V's first four attempts failed because its fractional pixel coordinates reached
a Pillow crop-stack size that requires integers. Round engine coordinates to
pixels before the shared crop geometry; add a regression fixture for that API
boundary and retain private tracebacks for any subsequent V failure. No V values
were scored, and no model-quality acceptance decision was made. Publish these
setup corrections and 12 passing tests before rerunning the same four halves.


## After pilot 3 (2026-10-11): X repaired, V not accepted

The corrected attempt completed all four X and four V calls in 82.6 seconds.
X supplied a schema-valid answer for every half-page and reproduced 218 of 239
fully readable gold rows exactly (224 complete rows). All four transcript
headers identify gpt-6.1-sol and display effort `none`; the request omits effort,
so no resolved provider effort is inferred from that header. The four calls
used 40,831 reported tokens. This single check does not establish improvement
over the older 212/239 result. No command-execution markers were found.

V detected 39 blocks across the four halves, but the column parser yielded
zero complete numeric rows. V=X and V=A therefore have zero comparable rows.
This does not meet the existing acceptance requirement and says nothing about
Vision's general OCR accuracy. The present Vision/parser combination is not
a replacement for B. Wave 1 remains unlaunched; no further tuning or broader
page run follows automatically. A redesigned numeric parser or a different
second engine would require a separately agreed next step.

With the current pilot X output, X=A agrees on 119 rows, all correct. The
saved B output agrees with X on 159 rows, of which 158 are correct. A's numeric
transcriptions were reused; its item-ID alignment uses current X, as the
existing reconciliation rule specifies. Its current 123/239 exact-row count
is not a new independent Tesseract run or a direct replication of the earlier
97/239 score. B reproduces 163/239 rows exactly. Missing gold values exclude
one of 240 rows; no rows are excluded for engine failure.

The counts-only report is `logs/norman-pilot3-scores-20261011.json`, with source
commit and input hashes. Runtime/environment and attempt counts are in
`logs/norman-extract-20261011-085730.json`. Source values, incomplete blocks and
all attempts stay in `data/raw/norman1967/`. The setup-failure record is retained
separately. Other pages' extracted values remain uninspected and unjoined.
