#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

if ! python3 -c "import piptools" >/dev/null 2>&1; then
  echo "[sync-backend-lock] pip-tools is not installed."
  echo "Install with: python3 -m pip install pip-tools"
  exit 1
fi

cd "$BACKEND_DIR"

cat > .requirements-lock.in <<'REQ'
-r requirements.txt
pytest==8.4.2
httpx==0.28.1
REQ

python3 -m piptools compile \
  --resolver=backtracking \
  --output-file requirements.lock.txt \
  .requirements-lock.in

rm -f .requirements-lock.in

echo "[sync-backend-lock] updated backend/requirements.lock.txt"
