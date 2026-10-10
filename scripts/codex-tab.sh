#!/bin/zsh
# Interactive Codex for this project (Brett, 2026-10-09: build and debug work moves to a Codex
# tab he drives; "Workspace-write, this project only"). Workspace-write sandbox (writes limited
# to the project, network off), approvals on request, so pushes and downloads ask first. Sets the
# same cache and compiler variables as scripts/codex-ws.sh so PyMC and nutpie compile inside the
# project. Unlike the scripted wrappers it keeps Brett's user config and session history.
# Usage: scripts/codex-tab.sh [codex arguments, e.g. a first prompt]   (see HANDOFF-TO-CODEX.md)
set -euo pipefail
PROJ="$(cd -- "$(dirname -- "$0")/.." && pwd -P)"
mkdir -p "$PROJ/.cache/pytensor" "$PROJ/.cache/numba" "$PROJ/.cache/mpl"
export PYTENSOR_FLAGS="base_compiledir=$PROJ/.cache/pytensor,cxx=$PROJ/scripts/d1/bin/clang++"
export NUMBA_CACHE_DIR="$PROJ/.cache/numba" MPLCONFIGDIR="$PROJ/.cache/mpl"
exec /opt/homebrew/bin/codex --sandbox workspace-write --ask-for-approval on-request --cd "$PROJ" "$@"
