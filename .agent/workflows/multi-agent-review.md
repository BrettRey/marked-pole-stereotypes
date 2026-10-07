---
description: Spawn independent LLM agents for parallel advisory board reviews
---

# Multi-Agent Advisory Board Review

Use this workflow when the user wants diverse, independent feedback on a chapter or document. This leverages external LLM CLIs (`codex`, `gemini`, `claude`) to spawn truly independent agents that don't share my context.

## When to use

- User asks for "advisory board" or "board feedback" on a chapter
- User wants multiple independent perspectives on the same content
- User explicitly requests parallel agent reviews
- Task benefits from genuine variance (not my simulation of multiple voices)

## Available CLIs

Check availability:
```bash
which codex && codex --version  # OpenAI Codex CLI
which gemini && gemini --version  # Google Gemini CLI  
which claude && claude --version  # Anthropic Claude Code
```

## Token considerations

- **claude**: Most token-constrained; user often hits limits before 5-hour window
- **codex**: More generous limits
- **gemini**: Most generous limits; prefer for multiple agents

## Spawning agents

### Codex (non-interactive)
```bash
codex exec "You are [ADVISOR NAME], [DESCRIPTION]. Read [FILE] and provide feedback on: (1) [Q1] (2) [Q2] (3) [Q3]. Write your feedback to notes/board-feedback-[chapter]-[advisor].md" > /dev/null 2>&1 &
```

### Gemini (MUST pipe content — file reading doesn't work in YOLO mode)
```bash
# IMPORTANT: Gemini CLI in --yolo mode does NOT read files from prompts.
# You MUST pipe the content in. Use -o text for cleaner output.
# Use 2>/dev/null to suppress startup log noise.
cat [FILE] | gemini --yolo -o text "You are [ADVISOR NAME], [DESCRIPTION]. This is [CHAPTER NAME]. Provide feedback on: (1) [Q1] (2) [Q2] (3) [Q3]. Give 3-4 paragraphs." > notes/board-feedback-[chapter]-[advisor].md 2>/dev/null &
```

**Model diversity:** Using BOTH Codex and Gemini gives genuine variance — different training data, different biases, different strengths. Prefer a mix (e.g., 3 Codex + 3 Gemini) over all from one model.

### Claude (if using despite token limits)
```bash
claude -p "You are [ADVISOR NAME]..." [FILE] > notes/board-feedback-[chapter]-[advisor].md &
```

## Standard advisors (from notes/advisory-board.md)

### Theoretical Board
- **Ruth Millikan** — teleosemantics, proper function
- **Adele Goldberg** — construction grammar
- **Eleanor Rosch** — prototype theory
- **Michael Tomasello** — usage-based acquisition

### Packaging Board
- **Howard Becker** — writing, rhetoric, "don't attack the tribe"
- **Carl Zimmer** — science communication, accessibility
- **Errol Morris** — how to present opposing views

## Checking status

```bash
# List completed feedback files
ls -la notes/board-feedback-*.md

# Check running agents
ps aux | grep -E "codex|gemini|claude" | grep -v grep

# Count remaining
ps aux | grep -E "codex|gemini" | grep -v grep | wc -l
```

## Cleanup (kill stalled agents)

Gemini agents in particular can stall. If agents haven't completed after ~10 minutes:

```bash
# Kill all gemini processes (runs as node)
pkill -f "gemini" 

# If that doesn't work, force kill
killall -9 gemini 2>/dev/null

# Verify
ps aux | grep -E "codex|gemini" | grep -v grep || echo "All clear"
```

**Note:** `killall node` will kill ALL node processes, not just Gemini. Use `pkill -f "gemini"` first.

## Important context caveat

Independent agents review the file in isolation. They don't have:
- Context from earlier chapters
- Knowledge of book-level framing already established
- My accumulated conversation context

Filter their feedback for:
- **Chapter-level issues** — local prose, argument flow, missing evidence
- **Not book-level issues** — things already addressed upstream

## After collection

1. Read all feedback files
2. Synthesize across perspectives
3. Filter for chapter-specific vs. already-addressed criticism
4. Propose targeted revisions
