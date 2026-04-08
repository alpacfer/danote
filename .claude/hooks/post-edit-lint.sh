#!/usr/bin/env bash
set -euo pipefail
INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
[[ -z "$FILE" ]] && exit 0

if [[ "$FILE" == *.py ]]; then
  cd "$CLAUDE_PROJECT_DIR/backend" \
    && .venv/bin/ruff check "$FILE" 2>&1 \
    || echo "⚠ ruff: issues in $FILE (non-blocking)"
fi

if [[ "$FILE" == *.ts || "$FILE" == *.tsx ]]; then
  cd "$CLAUDE_PROJECT_DIR" \
    && make -s maintainability-check 2>&1 \
    || echo "⚠ maintainability budget exceeded (non-blocking)"
fi

exit 0
