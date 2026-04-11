# Docs Index

Canonical docs are grouped by purpose under `docs/`. Short, dated design notes that explain one-off feature decisions live under [`docs/superpowers/`](./superpowers/README.md).

## Folder layout

- [`contracts/`](./contracts/api-contract.md): API-facing contracts, schema notes, and content policies
- [`behavior/`](./behavior/app-shell-behavior.md): product and section behavior docs
- [`architecture/`](./architecture/engineering-boundaries.md): engineering rules, dependency policy, and ADRs
- [`testing/`](./testing/test-plan.md): test strategy, CI coverage, and release checklists
- [`reference/`](./reference/configuration-reference.md): configuration, environment versions, and operational guidance
- [`research/`](./research/typo-detection-strategy-research-2026-02-26.md): background research worth keeping
- [`superpowers/`](./superpowers/README.md): compact feature-specific design notes

## API and contracts

- [API contract](./contracts/api-contract.md)
- [Typo v1 contract](./contracts/typo-v1-contract.md)
- [Typo benchmark schema v1](./contracts/typo-benchmark-schema-v1.md)
- [Word entry preprocessing policy](./contracts/word-entry-preprocessing-policy.md)

## Product behavior

- [App shell behavior](./behavior/app-shell-behavior.md)
- [Notes section behavior](./behavior/notes-section-behavior.md)
- [Playground section behavior](./behavior/playground-section-behavior.md)
- [Sidebar search behavior](./behavior/sidebar-search-behavior.md)
- [Wordbank section behavior](./behavior/wordbank-section-behavior.md)
- [Sentencebank section behavior](./behavior/sentencebank-section-behavior.md)
- [Developer section behavior](./behavior/developer-section-behavior.md)

## Architecture and engineering rules

- [Engineering boundaries](./architecture/engineering-boundaries.md)
- [Maintainability budgets](./architecture/maintainability-budgets.md)
- [Backend dependency locking](./architecture/backend-dependency-locking.md)
- [Configuration reference](./reference/configuration-reference.md)
- [Versions and environment locking](./reference/versions.md)
- [ADR index](./architecture/adr/README.md)

## Testing

- [Test plan](./testing/test-plan.md)
- [Test pyramid and CI](./testing/test-pyramid-and-ci.md)
- [Typo v1 build checklist](./testing/typo-v1-build-checklist.md)

## Research and design notes

- [Typo detection strategy research](./research/typo-detection-strategy-research-2026-02-26.md)
- [Token efficiency](./reference/token-efficiency.md)
- [Superpowers feature specs](./superpowers/README.md)

## Freshness index

Use this table to find the current source of truth quickly when behavior changes.

| Document | Audience | Primary source modules | Last verification checkpoint | Owner |
| --- | --- | --- | --- | --- |
| [App shell behavior](./behavior/app-shell-behavior.md) | Frontend engineers, maintainers | `frontend/src/App.tsx`, `frontend/src/app/layout/section-content.tsx`, `frontend/src/app/chrome/*` | Queued verification is spinner-only and does not add unread counts (2026-03-22) | Frontend |
| [Notes section behavior](./behavior/notes-section-behavior.md) | Frontend engineers, QA | `frontend/src/app/sections/notes-section.tsx`, `frontend/src/app/hooks/use-notes-persistence.ts`, `frontend/src/components/notes-editor.tsx` | Checkpoint 18 baseline and docs smoke alignment (2026-03-06) | Frontend |
| [Playground section behavior](./behavior/playground-section-behavior.md) | Frontend engineers, QA | `frontend/src/app/sections/playground-section.tsx`, `frontend/src/app/hooks/playground/*` | Checkpoint 18 baseline and docs smoke alignment (2026-03-06) | Frontend |
| [Sidebar search behavior](./behavior/sidebar-search-behavior.md) | Frontend engineers, product QA | `frontend/src/app/chrome/sidebar/*`, `frontend/src/app/hooks/sidebar/*` | Search-save blank-translation persistence replaces backend `409` gating for finalized empty translations (2026-03-22) | Frontend |
| [Wordbank section behavior](./behavior/wordbank-section-behavior.md) | Frontend engineers, backend integrators | `frontend/src/app/sections/wordbank/*`, `backend/app/api/routes/wordbank.py` | Queued verification no longer creates unread Wordbank markers; only review or error states do (2026-03-22) | Shared |
| [Sentencebank section behavior](./behavior/sentencebank-section-behavior.md) | Frontend engineers, backend integrators | `frontend/src/app/sections/sentencebank/*`, `backend/app/api/routes/sentencebank.py` | Checkpoint 18 baseline and docs smoke alignment (2026-03-06) | Shared |
| [Developer section behavior](./behavior/developer-section-behavior.md) | Frontend engineers, platform maintainers | `frontend/src/app/sections/developer-section.tsx`, `frontend/src/app/hooks/app/use-developer-settings.ts`, `backend/app/api/routes/developer.py` | Checkpoint 18 baseline and docs smoke alignment (2026-03-06) | Shared |

Update the checkpoint column when behavior or owning modules change.

## PR checklist

- [ ] `docs/README.md` still reflects the current file set and categories.
- [ ] API route or schema changes updated `docs/contracts/api-contract.md`.
- [ ] Command, setup, or workflow changes updated root `README.md` and the relevant docs.
- [ ] Dependency or runtime changes updated `docs/reference/versions.md`.
- [ ] Behavior changes updated the relevant section behavior doc and freshness entry.
- [ ] No docs changed only when the PR includes an explicit "No documentation impact" note.
