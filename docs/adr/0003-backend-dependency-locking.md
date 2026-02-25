# 0003: Backend dependency lock workflow

- Status: Accepted
- Date: 2026-02-25

## Context

Backend reproducibility lagged behind frontend because Python lock semantics were not standardized.

## Decision

Adopt `backend/requirements.lock.txt` as the canonical install source for backend setup.
Provide `scripts/sync-backend-lock.sh` for deterministic lock refresh using `pip-tools`.

## Consequences

- More reproducible backend environments.
- Safer dependency upgrades via explicit lock update step.
- Requires contributors/agents to refresh lock when dependency inputs change.

## Alternatives considered

- Continue with only `requirements-dev.txt` (rejected: weaker reproducibility).
- Switch fully to `uv lock` immediately (deferred: tooling migration can come later).
