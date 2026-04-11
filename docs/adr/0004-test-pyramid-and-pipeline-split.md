# 0004: Test pyramid and CI pipeline split

- Status: Accepted
- Date: 2026-02-25

## Context

All checks single CI job before. No parallelism. Runtime budgets opaque.

## Decision

Three layers:
1. **Fast**: lint + fast unit tests
2. **Medium**: selected backend integration/reliability tests
3. **Slow**: regression fixture tests (manual/scheduled)

Split workflows:
- `.github/workflows/quality.yml` for fast + medium checks
- `.github/workflows/regression-slow.yml` for slow fixture regressions

## Consequences

- Faster feedback for common PRs.
- Dedicated channel for deeper regression checks.
- Slight CI config complexity increase.

## Alternatives considered

- Single monolithic pipeline (rejected: slow feedback, less clarity).