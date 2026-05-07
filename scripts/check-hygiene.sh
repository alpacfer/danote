#!/usr/bin/env bash
# Soft hygiene checks. Warnings only — exits 0 even with warnings so it can be
# called liberally. Run before declaring broad changes done.
#
# What it checks:
#   1. Directories under backend/app/ and frontend/src/ that have >=5 source
#      files but no README.md.
#   2. References in markdown docs to agents/scripts/paths that don't exist
#      (catches "aspirational" guidance).
#
# What it intentionally does NOT check:
#   - Dead/orphan TS/TSX (needs a real tool like knip; grep gets too many
#     false positives).
#   - File size budgets — `make maintainability-check` already covers that.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

warns=0

echo "[hygiene] directories with >=5 source files and no README.md"
while IFS= read -r dir; do
  count=$(find "$dir" -maxdepth 1 -type f \
    \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' \) \
    -not -name '__init__.py' -not -name 'index.ts' 2>/dev/null \
    | wc -l | tr -d ' ')
  if [[ "$count" -ge 5 && ! -f "$dir/README.md" ]]; then
    echo "  [WARN] $dir ($count source files, no README)"
    warns=$((warns + 1))
  fi
done < <(find backend/app frontend/src -type d \
  -not -path '*/__pycache__*' \
  -not -path '*/node_modules/*' \
  -not -path '*/.venv/*' \
  -not -path '*/dist/*' \
  -not -path '*/build/*' 2>/dev/null)

echo "[hygiene] aspirational paths in docs (refs to .claude/agents/* that don't exist)"
while IFS= read -r ref; do
  # ref looks like: path/to/doc.md:NN:.claude/agents/foo
  doc=$(echo "$ref" | cut -d: -f1)
  agent_path=$(echo "$ref" | grep -oE '\.claude/agents/[a-zA-Z0-9_.-]+' | head -1)
  [[ -z "$agent_path" ]] && continue
  # Strip trailing punctuation
  agent_file="${agent_path%.md}.md"
  if [[ ! -f "$agent_file" && ! -f "$agent_path" ]]; then
    echo "  [WARN] $doc references missing $agent_path"
    warns=$((warns + 1))
  fi
done < <(grep -rn '\.claude/agents/' --include='*.md' \
  --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=worktrees \
  . 2>/dev/null)

echo "[hygiene] warnings=$warns"
exit 0
