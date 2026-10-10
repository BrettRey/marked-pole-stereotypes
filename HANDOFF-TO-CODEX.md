# Handoff to Codex
<!-- SUMMARY: Implementation moves from the Claude session to Codex tabs Brett drives (2026-10-09): two lanes, N (Norman extraction, blocked on a pass-X parser bug and OpenRouter credit) and S (D1c, D1b, threshold examples, Part 8 draft); rules, environment, state at handoff · status: active · updated: 2026-10-09 -->

From 2026-10-09 (Brett: "make it so"), build, test, debug and extraction work in this project runs in Codex tabs that Brett drives directly. The Claude session no longer dispatches Codex jobs. It keeps the D2 grid until that ends (about midnight), stays the only writer of `STATUS.md`, and does design reviews when Brett asks.

## Start

1. Launch from the project folder with `scripts/codex-tab.sh`. It gives what Brett approved ("Workspace-write, this project only"): writes limited to this project, network off, approvals on request, so pushes ask him first. It also sets the compile caches (below). `--yolo` would drop all of that.
2. Read `AGENTS.md`, this file, `analysis_plan.md`, the last 30 entries of `DECISIONS.md`, and your lane's README.
3. Brett's first message names your lane. One tab can do lane N, then lane S; two tabs run them in parallel.

## Lanes

| Lane | Writes | Never touches |
|---|---|---|
| N: Norman extraction | `scripts/norman/`, `data/raw/norman1967/` (gitignored), `logs/norman-*` | `scripts/d1c/`, `scripts/d1b/`, `notes/` drafts |
| S: simulations and drafts | `scripts/d1c/`, `scripts/d1b/` (new), `results/d1c/`, `results/d1b/`, `logs/d1c-*`, `logs/d1b-*`, `notes/*-draft-*.md` | `scripts/norman/`, `data/raw/norman1967/` |
| Both | append to `DECISIONS.md` | `analysis_plan.md`, `STATUS.md`, `results/d2/`, `logs/d2-*` (the D2 grid is still writing them) |

## Rules (Brett's; they bind both lanes)

- **The repo is public.** Before every commit run `git status --porcelain` and name what becomes public. Commit explicit paths only: `git add <new files> && git commit -m "..." -- <paths>`. Never `git add -A`, `git add .` or `git commit -a`, and never leave files staged (the other tab may commit). Never commit `data/raw/`, `private/`, PDFs or caches.
- **Spec and code are committed and pushed before any run, pilots included.** Changes after a run go in a dated README section ("After pilot 1 (2026-10-09)"), never as silent edits.
- **No stand-in data.** If a source can't be had, stop that strand and report it. Simulated data checks designs only and is labelled as such.
- **Design questions.** Reason as Gelman would: fake-data simulation first, multilevel models with partial pooling, posterior predictive checks, effect sizes with intervals, no significance-hunting. Where several analytic options are defensible, pre-specify them all as a multiverse instead of asking Brett to pick. Ask Brett only about resources, ethics, scope, values or authorization, and give one recommendation. For a second opinion from another model family, Brett can ask the Claude session.
- **`analysis_plan.md`**: settled sections change only with Brett's agreement. New plan text goes to `notes/` as a draft for him to merge.
- **`DECISIONS.md`**: append only, in the file's form `YYYY-MM-DD — Decision. Reason.` Never rewrite an entry.
- **Sources.** Facts, numbers, word senses and citations come from a source you've read, with a page, never from memory. When you need Brett to fetch something, give the full reference with its DOI link and say whether you can fetch it yourself.
- **Data boundary.** Nothing under review, blinded or restricted goes to an external model. Norman (1967) is a public ERIC document, so passes B and X may send it out.
- **Norman firewall.** Until L1's frame is frozen, no one looks at extracted Norman values: print counts and range-check summaries only, and never join values to morphology. The one exception is the pilot pages 40 and 41 (no negated terms; gold in `data/raw/norman1967/gold_pilot_claude.json`), which may be read value by value for debugging. If other values are seen, log it in `DECISIONS.md` in full: which items, which scales, which tests it touches.
- **Scripted Codex runs at reasoning effort "none"** unless told otherwise: the wrappers ignore user config, and all 20 transcripts in `reviews/` say so in their headers. For a scripted review, set the effort explicitly (config key `model_reasoning_effort`, passed with `-c`) and check that the header shows it. Pass X is the exception (see lane N).
- **Scripted Codex output is published.** A scripted review or job gets `reviews/<name>-<date>/` with `prompt.md`, `output_raw.txt`, `output.md` and a `manifest.yaml` like the existing ones; commit them, not the `.started`/`.finished` markers.
- **Long runs** go detached (`nohup ... > logs/<name>-stdout.txt 2>&1 &`) with one progress line per unit; check them with `tail`.

## Environment

| What | Setting |
|---|---|
| Python for D1, D1c, D2 | `.venv/bin/python` |
| PyMC and nutpie compilation | `PYTENSOR_FLAGS="base_compiledir=$PWD/.cache/pytensor,cxx=$PWD/scripts/d1/bin/clang++"` (the shim drops pytensor's `-ld64`, which current clang rejects), `NUMBA_CACHE_DIR=$PWD/.cache/numba`, `MPLCONFIGDIR=$PWD/.cache/mpl`. The launcher sets all three. |
| Known failure | a D1c test run aborted in llvmlite (`LLVMPY_DisposeString`, macOS crash report 2026-10-09 20:59); not diagnosed |
| Extraction | `uv run --quiet --no-project --with pillow==11.3.0 python scripts/norman/extract.py {pages, pilot, run --first F --count C --workers W, passC, disputes, reconcile}` |
| Scripted Codex vision | `scripts/codex-ro-images.sh DIR PROMPT_FILE IMAGE...` (read-only sandbox, scrubbed environment) |
| Pass B | OpenRouter `z-ai/glm-5.3-flash`, key from the Keychain service `ox-alpha`; returns HTTP 402 until Brett adds credit |

## Lane N: Norman extraction

Spec: `scripts/norman/README.md`. Wave 1 (the first 60 table pages, 120 half-pages) was stopped by the Claude session at 21:15 on 2026-10-09.

| Pass | Rows ok | Rows failed | Cause |
|---|---|---|---|
| B (GLM) | 26 | 94 | HTTP 402 (no OpenRouter credit); one broken pipe |
| X (Codex) | 0 | 99 | parser, `no answer` |

1. **Fix pass X.** `pass_x` (`extract.py:273`) keeps only stdout and wants a line reading `codex`; stderr is thrown away, so the cause is invisible. Run `scripts/codex-ro-images.sh "$PWD" data/raw/norman1967/prompt_x.md data/raw/norman1967/img/p040_M.png` by hand with stdout and stderr captured separately. The likely cause is that `codex exec` (v0.160.0) writes its transcript to stderr and only the final message to stdout, in which case 99 transcriptions were made and discarded. `codex exec -o FILE` (`--output-last-message`) gives the answer independent of the format. Keep stderr and the token count in `meta`. Test on pages 40 and 41 against the gold file (pilot 2 scored 212 of 239 rows exactly right). Keep the wrapper's settings fixed across waves so pass X stays one instrument: gpt-6.1-sol, and the transcript header reports reasoning effort "none" because the wrapper ignores user config. Record them in the extraction log.
2. **Make failures retryable.** `load_jsonl` counts every row as done, failed or not. Change `run_passes` so rows with `blocks: null` aren't done; keep them in the file as the record of attempts, and have readers take the last non-null row per page and side.
3. **Rerun wave 1, pass X:** `run --first 0 --count 60 --workers 4`. Pass B stays blocked.
4. **Waves 2 onwards** over the remaining table pages (`extract.py pages`), once wave 1's X is clean.
5. **Then** X2 (a zoomed Codex re-read of unresolved rows, per the README), the third-family audit (scripted, counts only), Appendix 0 term matching, and `reconcile`.

Without pass B, the only cross-family pair is X with Tesseract, and Tesseract was exactly right on 97 of 239 pilot rows, so most rows would stay unresolved. Don't change the acceptance rule; report the counts to Brett.

## Lane S: simulations and drafts

1. **D1c** (`scripts/d1c/README.md`, `d1c.py`). The Claude session's scripted debug job (`reviews/codex-debug-d1c-2026-10-09/`) was stopped at 21:23 before its final message, and its working-tree changes are committed as found ("D1c: unfinished Codex debug run"). Its transcript shows it confirmed that the revised contrasts and multinomial likelihood match the originals numerically (`logs/d1c-equivalence-20261009.json`) and was testing checkpointing after an interrupted multiprocessing run. Read the end of its `output_raw.txt` first. Get `.venv/bin/python scripts/d1c/d1c.py pilot` running end to end (R-hat at most 1.01, few divergences, estimates near truth in the baseline cell). Record any design change in a README section "After pilot 1 (2026-10-09)", time each fitted variant, commit, push, then run the grid as the README specifies (2 workers while D2 is running, 3 after). Summarise as the README pre-registers. Move the cache that `d1c.py` writes to `logs/d1c-cache/` (now gitignored) into `.cache/`. Brett's verdict on D1 (whether the frequency-only indicator is excluded) waits for D1c.
2. **D1b**, the fake-data check of the multi-indicator design: `analysis_plan.md`, "Proposed revisions", item 4. It must state its identifying restrictions algebraically and report conclusions across pre-specified bias, transport and feedback assumptions. Spec in `scripts/d1b/README.md`; commit; pilot; grid.
3. **Threshold examples** for Brett. He sets an evaluative benchmark for each estimand by judgement from concrete probability examples (`DECISIONS.md`, 2026-10-09 "Thresholds"; `reviews/codex-thresholds-2026-10-09/`). For each estimand in the plan, show what posteriors and exceedance curves look like near a few candidate benchmarks, on the estimand's own scale. Draft in `notes/threshold-examples-draft-YYYY-MM-DD.md`.
4. **Part 8**, the plan's unwritten sections (the "To write" paragraphs under Data and exclusions, Variables, Models, What would count against each hypothesis, and Seeds and environment). Draft in `notes/plan-part8-draft-YYYY-MM-DD.md` from settled text only (the plan's "Proposed revisions" and `DECISIONS.md`); mark anything new **PROPOSED**. Brett merges.
5. **D2b** is blocked until L1's frame is frozen (`scripts/d2/README.md`, "D2b additions"). Don't start it.

## Waiting on Brett

| Item | Why |
|---|---|
| OpenRouter credit | pass B; without it lane N mostly fails its acceptance rule |
| Verdict on the D1 frequency-only indicator | after D1c |
| Threshold benchmarks | after the examples note |
| Part 8 merge | after the draft |
| Licence for Koch et al.'s data | authors emailed 2026-10-09; nothing from that dataset is used before they reply |

## Running at handoff

| Process | Owner | Writes | Ends |
|---|---|---|---|
| D2 grid (shell PID 77845, Python 77847) | Claude session | `results/d2/`, `logs/d2-*` | about midnight; the Claude session commits the results and summarises them |
| Codex jobs for `info-rate-context` | another project | elsewhere | ignore |
