#!/usr/bin/env bash
set -euo pipefail
INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
if [[ "$FILE" == *".env" || "$FILE" == *".env.local" || "$FILE" == *".env."* ]]; then
  echo "Blocked: direct edit of $FILE — manage via env config, not Claude edits" >&2
  exit 2
fi
exit 0
