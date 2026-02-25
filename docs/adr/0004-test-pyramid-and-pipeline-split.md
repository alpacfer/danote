# 0004: Test pyramid and CI pipeline split

- Status: Accepted
- Date: 2026-02-25

## Context

All checks were previously in a single CI job, limiting parallelism and making runtime budgeting opaque.

## Decision

Define three layers:
1. **Fast**: lint + fast unit tests
2. **Medium**: selected backend integration/reliability tests
3. **Slow**: regression fixture tests (manual/scheduled)

Implement split workflows:
- `.github/workflows/quality.yml` for fast + medium checks
- `.github/workflows/regression-slow.yml` for slow fixture regressions

## Consequences

- Faster feedback for common PRs.
- Dedicated channel for deeper regression checks.
- Slight increase in CI configuration complexity.

## Alternatives considered

- Keep single monolithic pipeline (rejected: slower feedback and less clarity).
