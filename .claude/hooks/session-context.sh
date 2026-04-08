#!/usr/bin/env bash
cat << 'EOF'
=== Context restored after compaction ===
Stack: FastAPI + SQLite backend | React 19 + Vite + TypeScript + Tailwind + shadcn/ui frontend
Verification sequence: make lint → make maintainability-check → make test → make docs-smoke
Architecture: routes → schemas → use-cases → domain services → NLP adapters → DB
Docs sync rule (mandatory): any code/API/schema/workflow change must include docs update in same PR
Single backend test:  cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/test_X.py
Single frontend test: cd frontend && npx vitest run src/path/to/file.test.ts
EOF
