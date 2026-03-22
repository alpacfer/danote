# Documentation index (discoverability + freshness)

This index is the canonical entry point for repository documentation. It is organized by category and includes a freshness index for core behavior docs so reviewers can quickly assess documentation reliability.

## API / specs

- [API contract](./api-contract.md)
- [Typo v1 contract](./typo-v1-contract.md)
- [Typo benchmark schema v1](./typo-benchmark-schema-v1.md)
- [Word entry preprocessing policy](./word-entry-preprocessing-policy.md)

## Section behavior

- [App shell behavior](./app-shell-behavior.md)
- [Playground section behavior](./playground-section-behavior.md)
- [Sidebar search behavior](./sidebar-search-behavior.md)
- [Wordbank section behavior](./wordbank-section-behavior.md)
- [Sentencebank section behavior](./sentencebank-section-behavior.md)
- [Developer section behavior](./developer-section-behavior.md)

## Architecture / ADR

- [System description](./system_description.md)
- [Engineering boundaries](./engineering-boundaries.md)
- [Backend dependency locking](./backend-dependency-locking.md)
- [ADR index](./adr/README.md)
  - [ADR-0001: Use-case layer](./adr/0001-use-case-layer.md)
  - [ADR-0002: Versioned API schemas](./adr/0002-versioned-api-schemas.md)
  - [ADR-0003: Backend dependency locking](./adr/0003-backend-dependency-locking.md)
  - [ADR-0004: Test pyramid and pipeline split](./adr/0004-test-pyramid-and-pipeline-split.md)

## Audits / reports

- [Maintainability audit (2026-03-06)](./maintainability-audit-2026-03-06.md)
- [Maintainability audit (2026-03-05)](./maintainability-audit-2026-03-05.md)
- [Post-PR maintainability assessment](./post-pr-maintainability-assessment.md)
- [Repository maintainability review](./repository-maintainability-review.md)
- [Repository analysis issues](./repository-analysis-issues.md)
- [Implementation code review report](./reports/implementation-code-review.md)
- [Playground search wordflow report](./reports/playground-search-wordflow-report.md)
- [Benchmark assessment (2026-02-25)](./benchmark-assessment-2026-02-25.md)
- [Benchmark assessment (2026-02-26)](./benchmark-assessment-2026-02-26.md)
- [Lemma benchmark baseline](./lemma-benchmark-baseline.md)
- [Lemma benchmark report v0](./lemma-benchmark-report-v0.md)
- [Typo detection strategy research](./typo-detection-strategy-research-2026-02-26.md)

## Testing / release

- [Test plan](./test-plan.md)
- [Test pyramid and CI](./test-pyramid-and-ci.md)
- [Manual demo script](./manual-demo-script.md)
- [Release checklist prototype v0](./release-checklist-prototype-v0.md)
- [Typo v1 build checklist](./typo-v1-build-checklist.md)
- [Versions](./versions.md)
- [Agent playbook](./agent-playbook.md)

## Core behavior freshness index

| Document | Intended audience | Source modules | Last verification date/checkpoint | Owning area |
| --- | --- | --- | --- | --- |
| [App shell behavior](./app-shell-behavior.md) | Frontend engineers, maintainers | `frontend/src/App.tsx`, `frontend/src/app/layout/section-content.tsx`, `frontend/src/app/chrome/*` | Silent success settlement for unchanged Gemini verification notifications (2026-03-22) | Frontend |
| [Playground section behavior](./playground-section-behavior.md) | Frontend engineers, QA | `frontend/src/app/sections/playground-section.tsx`, `frontend/src/app/hooks/playground/*` | Checkpoint 18 baseline and docs smoke alignment (2026-03-06) | Frontend |
| [Sidebar search behavior](./sidebar-search-behavior.md) | Frontend engineers, product QA | `frontend/src/app/chrome/sidebar/*`, `frontend/src/app/hooks/sidebar/*` | Search-save blank-translation persistence replaces backend `409` gating for finalized empty translations (2026-03-22) | Frontend |
| [Wordbank section behavior](./wordbank-section-behavior.md) | Frontend engineers, backend integrators | `frontend/src/app/sections/wordbank/*`, `backend/app/api/routes/wordbank.py` | Word-card context menus can now ask Gemini for common alternative translations and replace the saved primary translation when the current one is not the best common fit (2026-03-22) | Shared |
| [Sentencebank section behavior](./sentencebank-section-behavior.md) | Frontend engineers, backend integrators | `frontend/src/app/sections/sentencebank/*`, `backend/app/api/routes/sentencebank.py` | Checkpoint 18 baseline and docs smoke alignment (2026-03-06) | Shared |
| [Developer section behavior](./developer-section-behavior.md) | Frontend engineers, platform maintainers | `frontend/src/app/sections/developer-section.tsx`, `frontend/src/app/hooks/app/use-developer-settings.ts`, `backend/app/api/routes/developer.py` | Checkpoint 18 baseline and docs smoke alignment (2026-03-06) | Shared |

> Freshness policy: update the verification column whenever behavior or source modules in scope change.

## Documentation parity checklist (PR review)

Use this checklist in every PR to enforce docs/code parity:

- [ ] I reviewed `docs/README.md` and confirmed links/categories still match current docs.
- [ ] For code/config/API/schema/workflow changes, I updated the relevant documentation in the same PR.
- [ ] For API route/schema changes, I updated `docs/api-contract.md`.
- [ ] For command/setup/workflow changes, I updated root `README.md` and relevant docs pages.
- [ ] For dependency/runtime/version changes, I updated `docs/versions.md`.
- [ ] I updated freshness metadata for impacted core behavior docs (audience, source modules, verification checkpoint, owning area).
- [ ] If no docs changed, the PR includes explicit "No documentation impact" justification.
