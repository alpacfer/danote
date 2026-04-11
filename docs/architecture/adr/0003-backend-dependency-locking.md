# 0003: Backend dependency lock workflow

- Status: Accepted
- Date: 2026-02-25

## Context

Backend reproducibility lagged frontend. Python lock semantics not standardized.

## Decision

Adopt `backend/requirements.lock.txt` as canonical install source.
Provide `scripts/sync-backend-lock.sh` for deterministic lock refresh via `pip-tools`.

## Consequences

- More reproducible backend envs.
- Safer dep upgrades via explicit lock update step.
- Contributors/agents must refresh lock when dep inputs change.

## Alternatives considered

- Continue with only `requirements-dev.txt` (rejected: weaker reproducibility).
- Switch fully to `uv lock` immediately (deferred: tooling migration later).