#!/usr/bin/env bash
set -euo pipefail
INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
echo "$CMD" | grep -qE '^git commit' || exit 0

cd "$CLAUDE_PROJECT_DIR" \
  && make lint && make test 2>&1 \
  || echo "⚠ pre-commit checks had issues (non-blocking)"

exit 0
