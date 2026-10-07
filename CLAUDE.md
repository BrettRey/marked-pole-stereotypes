# CLAUDE.md
<!-- SUMMARY: Agent guidance for Marked-pole stereotypes; deliberately short, points at the portfolio rules rather than copying them · status: active · updated: 2026-09-02 -->

Guidance for Claude Code, Codex, and other agents working in this repository.

## Project

Academic paper: **Marked-pole stereotypes**, by Brett Reynolds.

## This file is deliberately short

House style, writing style, terminology, citation practice, dispatch
invocations, and submission process live in the portfolio rules. They are
not copied here: a copy cannot learn that its source changed, so anything
duplicated into this file goes stale.

| What you need | Where it actually lives |
|---|---|
| LaTeX house style: terms, mentions, dashes, citations | `../../.claude/rules/latex-house-style.md` |
| Writing style, AI tics, paragraph discipline | `../../.claude/rules/writing-style.md` |
| CGEL terminology: category vs function, non-count, predicator | `../../.claude/rules/cgel-conventions.md` |
| Source grounding (LAW) | `../../.claude/rules/source-grounding.md` |
| Bibliography workflow | `../../.claude/rules/bibliography-workflow.md` |
| Multi-model dispatch invocations | `../../.claude/rules/multi-model-dispatch.md` |
| Portfolio-wide commitments, with checks | `../../canon/` |
| The values behind the rules | `../../constitution.md` |

Paths assume a paper at `papers/<slug>/`; adjust the depth if this project sits
elsewhere. In a Claude Code session opened anywhere inside the portfolio, the
root `CLAUDE.md` and its rules load automatically and you don't need to read
these by hand.

## Build

XeLaTeX, not pdfLaTeX (font requirements). Avoid LuaLaTeX: it runs words
together in the PDF text layer, breaking copy-paste and accessibility.

```bash
make              # full build: marked-pole-stereotypes.pdf
make quick        # single pass
make clean        # clean artifacts
```

The manuscript is `marked-pole-stereotypes.tex` and builds `marked-pole-stereotypes.pdf`; don't rename it
`main.tex` (canon: meaningful-file-names-not-main). Set `PDF_BASENAME` when a venue
wants a specific upload name, e.g. `PDF_BASENAME = Reynolds-Short-Title`.

Never hardcode a TeX Live path in `\setmainfont`. Write the font filenames and
let kpathsea resolve them; a `Path=/usr/local/texlive/<year>/...` line makes the
document silently unbuildable at the next upgrade, and you find out when you go
to send it.

## Layout

```
marked-pole-stereotypes/
├── marked-pole-stereotypes.tex         # the manuscript
├── references.bib            # symlink to the central bibliography
├── references-local.bib      # project-specific entries; /push-bib merges these
├── .canon-stamp              # what this paper has been reconciled against
├── .house-style/             # preamble + style-rules snapshot
├── Makefile
├── CLAUDE.md / AGENTS.md / GEMINI.md   # this file, kept in sync by a hook
└── submission/               # venue decision, checklist, assurance record
```

## Gates before anything goes out

Detail is in the portfolio rules; the order is:

1. `submission/venue-decision-YYYY-MM-DD.md` from the PM template, before any
   target-specific work.
2. `submission/pre-submission-checklist-YYYY-MM-DD.md`.
3. `submission/paper-assurance-YYYY-MM-DD.md` via
   `Project-Management/tools/paper_assurance.py`, reporting `CURRENT` plus
   `gate: PASS`.

A cover letter or a portal copy-paste sheet is not a substitute for any of these.

## Canon

`.canon-stamp` records which portfolio-wide commitments this paper has been
checked against. To see whether it has fallen behind:

```bash
python3 ../../Project-Management/tools/canon_drift.py --project papers/marked-pole-stereotypes
```

Or `/canon-drift`. Where a commitment doesn't apply to this paper, dismiss it in
`.canon-stamp` under `acknowledged:` with a reason, rather than letting it
resurface every sweep.

## Log decisions as you go

Non-trivial decisions (structural, terminological, what to cut, how to frame an
argument) go in `DECISIONS.md` when they're made, not at shutdown:
`YYYY-MM-DD — Decision. Reason.`

If a decision binds more than this paper, it belongs in the canon: run `/canon`.
