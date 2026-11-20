#!/usr/bin/env bash
# Link ~/.claude/CLAUDE.md and ~/.claude/tools to this repo.
# An existing file or directory there is moved aside to <name>.bak-<timestamp>, never deleted.
set -euo pipefail

repo="$(cd "$(dirname "$0")" && pwd)"
dest="$HOME/.claude"
mkdir -p "$dest"

for name in CLAUDE.md tools; do
  target="$dest/$name"
  if [ -L "$target" ] && [ "$(readlink "$target")" = "$repo/$name" ]; then
    echo "ok      $target"
    continue
  fi
  if [ -e "$target" ] || [ -L "$target" ]; then
    backup="$target.bak-$(date +%Y%m%d%H%M%S)"
    mv "$target" "$backup"
    echo "moved   $target -> $backup"
  fi
  ln -s "$repo/$name" "$target"
  echo "linked  $target -> $repo/$name"
done
