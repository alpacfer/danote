# Docs Index

Canonical docs are grouped by purpose under `docs/`. Durable references stay here; completed one-off implementation plans should be removed instead of archived indefinitely.

## Folder layout

- [`contracts/`](./contracts/api-contract.md): API-facing contracts, schema notes, and content policies
- [`behavior/`](./behavior/app-shell-behavior.md): product and section behavior docs
- [`architecture/`](./architecture/engineering-boundaries.md): engineering rules, dependency policy, and ADRs
- [`design/`](./design/visual-system.md): visual language, semantic tokens, typography, and surface hierarchy
- [`testing/`](./testing/test-plan.md): test strategy, CI coverage, and release checklists
- [`reference/`](./reference/configuration-reference.md): configuration, environment versions, and operational guidance
- [`deployment/`](./deployment/vps-private-beta.md): hosted deployment runbooks
- [`research/`](./research/typo-detection-strategy-research-2026-02-26.md): background research worth keeping

## API and contracts

- [API contract](./contracts/api-contract.md)
- [Typo v1 contract](./contracts/typo-v1-contract.md)
- [Typo benchmark schema v1](./contracts/typo-benchmark-schema-v1.md)
- [Word entry preprocessing policy](./contracts/word-entry-preprocessing-policy.md)

## Product behavior

- [App shell behavior](./behavior/app-shell-behavior.md)
- [Notes section behavior](./behavior/notes-section-behavior.md)
- [Playground section behavior](./behavior/playground-section-behavior.md) (retired/inaccessible)
- [Sidebar search behavior](./behavior/sidebar-search-behavior.md)
- [Wordbank section behavior](./behavior/wordbank-section-behavior.md)
- [Sentencebank section behavior](./behavior/sentencebank-section-behavior.md)
- [Developer section behavior](./behavior/developer-section-behavior.md)

## Architecture and engineering rules

- [Engineering boundaries](./architecture/engineering-boundaries.md)
- [Maintainability budgets](./architecture/maintainability-budgets.md)
- [Visual system](./design/visual-system.md)
- [Backend dependency locking](./architecture/backend-dependency-locking.md)
- [Configuration reference](./reference/configuration-reference.md)
- [Versions and environment locking](./reference/versions.md)
- [Render single-service deployment](./deployment/render-single-service.md)
- [VPS private beta deployment](./deployment/vps-private-beta.md)
- [Render + Vercel deployment](./deployment/render-vercel.md)
- [ADR index](./architecture/adr/README.md)

## Testing

- [Test plan](./testing/test-plan.md)
- [Test pyramid and CI](./testing/test-pyramid-and-ci.md)

## Research

- [Typo detection strategy research](./research/typo-detection-strategy-research-2026-02-26.md)

## Freshness index

Use this table to find the current source of truth quickly when behavior changes.

| Document | Audience | Primary source modules | Last verification checkpoint | Owner |
| --- | --- | --- | --- | --- |
| [App shell behavior](./behavior/app-shell-behavior.md) | Frontend engineers, maintainers | `frontend/src/App.tsx`, `frontend/src/app/layout/*`, `frontend/src/app/chrome/*`, `frontend/src/app/auth/*` | Fraunces wordmark aligned with the editorial typography system (2026-07-19) | Frontend |
| [Notes section behavior](./behavior/notes-section-behavior.md) | Frontend engineers, QA | Retired/hidden UI reference | Notes section hidden from shell navigation and command pages (2026-05-02) | Frontend |
| [Playground section behavior](./behavior/playground-section-behavior.md) | Frontend engineers, QA | Retired/inaccessible UI reference | DaCy retirement and Playground hide update (2026-05-01) | Frontend |
| [Sidebar search behavior](./behavior/sidebar-search-behavior.md) | Frontend engineers, product QA | `frontend/src/app/chrome/sidebar/*`, `frontend/src/app/hooks/sidebar/*`, `backend/app/services/use_cases/wordbank/collaborators/*`, `backend/app/bootstrap/runtime_search_warmup.py` | Search folio, natural section labels, and responsive language controls aligned with the field-notebook visual system (2026-07-19) | Shared |
| [Wordbank section behavior](./behavior/wordbank-section-behavior.md) | Frontend engineers, backend integrators | `frontend/src/app/sections/wordbank/*`, `backend/app/api/routes/wordbank.py` | Ruled paradigm tables expose verified, root-aware missing-form reveal actions (2026-07-19) | Shared |
| [Sentencebank section behavior](./behavior/sentencebank-section-behavior.md) | Frontend engineers, backend integrators | `frontend/src/app/sections/sentencebank/*`, `backend/app/api/routes/sentencebank.py` | Sidebar sentence preview accepts explicit Danish/English language mode routing (2026-05-26) | Shared |
| [Developer section behavior](./behavior/developer-section-behavior.md) | Frontend engineers, platform maintainers | `frontend/src/app/sections/developer/*`, `frontend/src/app/hooks/app/use-developer-settings.ts`, `backend/app/api/routes/developer.py`, `scripts/dev-app.py` | DTC search profiling reports backend/client timing split and fails clearly when cold-cache admin support is disabled (2026-05-31) | Shared |

Update the checkpoint column when behavior or owning modules change.

## PR checklist

- [ ] `docs/README.md` still reflects the current file set and categories.
- [ ] API route or schema changes updated `docs/contracts/api-contract.md`.
- [ ] Command, setup, or workflow changes updated root `README.md` and the relevant docs.
- [ ] Dependency or runtime changes updated `docs/reference/versions.md`.
- [ ] Behavior changes updated the relevant section behavior doc and freshness entry.
- [ ] No docs changed only when the PR includes an explicit "No documentation impact" note.
