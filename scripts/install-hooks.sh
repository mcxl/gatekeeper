#!/bin/sh
# Install repo-managed git hooks into .git/hooks/.
# Run once per fresh checkout. Idempotent.

set -e
REPO_ROOT=$(git rev-parse --show-toplevel)
HOOK_SRC="$REPO_ROOT/scripts/hooks"
HOOK_DST="$REPO_ROOT/.git/hooks"

if [ ! -d "$HOOK_SRC" ]; then
  echo "no hooks directory at $HOOK_SRC; nothing to install"
  exit 0
fi

for f in "$HOOK_SRC"/*; do
  name=$(basename "$f")
  cp "$f" "$HOOK_DST/$name"
  chmod +x "$HOOK_DST/$name"
  echo "installed: $name"
done
