#!/bin/zsh
# Read-only Codex with image attachments. Same restrictions as the portfolio's
# tools/codex/bin/codex-readonly (read-only sandbox, approvals never, user config
# ignored, ephemeral, scrubbed environment), plus `-i IMAGE` for each image given.
# Usage: codex-ro-images.sh DIRECTORY PROMPT_FILE IMAGE [IMAGE ...]   (answer on stdout)
set -euo pipefail
CODEX_EXECUTABLE="/opt/homebrew/bin/codex"
dir="$(cd -- "$1" && pwd -P)"; prompt_file="$2"; shift 2
image_args=()
for img in "$@"; do image_args+=(-i "$img"); done
exec /usr/bin/env -i PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin" LANG=C.UTF-8 LC_ALL=C.UTF-8 \
  "$CODEX_EXECUTABLE" --sandbox read-only --ask-for-approval never exec --ignore-user-config --strict-config \
  --ephemeral --skip-git-repo-check --cd "$dir" "${image_args[@]}" - < "$prompt_file"
