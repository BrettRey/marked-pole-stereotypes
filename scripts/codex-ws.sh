#!/bin/zsh
# Codex with a workspace-write sandbox, limited to this project (Brett, 2026-10-09:
# "Workspace-write, this project only"). Same scrubbing as the portfolio's
# tools/codex/bin/codex-readonly (approvals never, user config ignored, ephemeral,
# clean environment); the sandbox lets Codex write only inside the project, and its
# default keeps the network off. Caches are redirected into the project's .cache/.
# The parent reviews `git diff` before anything is committed or pushed.
# Usage: codex-ws.sh PROMPT_FILE   (run from anywhere; answer on stdout)
set -euo pipefail
CODEX_EXECUTABLE="/opt/homebrew/bin/codex"
PROJ="$(cd -- "$(dirname -- "$0")/.." && pwd -P)"
mkdir -p "$PROJ/.cache/pytensor" "$PROJ/.cache/numba" "$PROJ/.cache/mpl"
exec /usr/bin/env -i PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin" LANG=C.UTF-8 LC_ALL=C.UTF-8 \
  PYTENSOR_FLAGS="base_compiledir=$PROJ/.cache/pytensor,cxx=$PROJ/scripts/d1/bin/clang++" \
  NUMBA_CACHE_DIR="$PROJ/.cache/numba" MPLCONFIGDIR="$PROJ/.cache/mpl" \
  "$CODEX_EXECUTABLE" --sandbox workspace-write --ask-for-approval never exec --ignore-user-config --strict-config \
  --ephemeral --skip-git-repo-check --cd "$PROJ" - < "$1"
