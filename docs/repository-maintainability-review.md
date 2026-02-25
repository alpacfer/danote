# Repository Maintainability Review

Date: 2026-02-25

## Executive Summary

The repository is in **good shape for a prototype-to-product transition**:

- Code is generally compartmentalized into `frontend/`, `backend/`, `docs/`, and helper `scripts/`.
- Backend domain boundaries are reasonably clear (`api/`, `services/`, `nlp/`, `db/`).
- There is meaningful test coverage and regression fixture support.
- Documentation exists for architecture, contracts, and release/demo workflows.

Main weaknesses are not core functionality, but **developer workflow consistency** and **maintainability ergonomics** (environment reproducibility, style consistency, and automation quality gates).

## Current State Assessment

### 1) Tidiness and code organization

**What is good**
- Clear top-level repository structure with logical separation of responsibilities.
- Backend has pragmatic layering: route handlers, domain services, NLP adapter abstraction, and migration scripts.
- Frontend uses componentized UI structure with a dedicated `ui/` area and tests.

**What can be improved**
- Some generated/shared UI files carry conventions that clash with lint rules; this creates friction for routine maintenance.
- Several project conventions are implicit rather than codified (e.g., where to place new domain services, route schema patterns, test naming standards).

### 2) Compartmentalization and modularity

**What is good**
- NLP is abstracted behind an adapter contract, which is a strong extensibility decision.
- Typo engine logic is split into focused modules (`normalization`, `gating`, `ranking`, `decision`, `cache`).

**What can be improved**
- API route modules still contain a lot of orchestration details; introducing explicit application-service/use-case layer objects would make handlers thinner and easier to test in isolation.
- Shared schemas/types are mostly local to each route file; extracting stable API DTO modules would reduce drift and simplify versioning.

### 3) Documentation quality

**What is good**
- Repo includes product, API contract, system description, test plans, release checklists, and benchmark docs.
- README-level setup/run instructions are present for both frontend and backend.

**What can be improved**
- Some docs have historically diverged from actual commands/import behavior; docs validation should be automated.
- Contributor onboarding docs could be more opinionated: “first 30 minutes” workflow, expected tooling versions, and common failure recovery.

### 4) Upgradeability and adaptability

**What is good**
- Dependency lockfile exists on frontend.
- Backend uses migration files and startup migration application, enabling schema evolution.
- Contracts and fixture-based regression artifacts are present.

**What can be improved**
- Python environment reproducibility is weaker than frontend (no lockfile equivalent committed for backend).
- Automated compatibility matrix (Python/Node versions, key library ranges, known good combinations) is only partially encoded in docs.
- CI could more explicitly guard upgrade breakage with split fast/slow pipelines.

## Recommendations (Non-functional)

### Priority A — immediate workflow quality

1. **Add one-command reproducible dev setup**
   - Introduce a root `Makefile` or `justfile` with targets like:
     - `setup-backend`, `setup-frontend`, `test`, `lint`, `dev`
   - Goal: reduce command drift between docs and execution.

2. **Strengthen CI gates for docs-command drift**
   - Add a lightweight CI job that executes documented smoke commands (or script wrappers used by docs).
   - Goal: prevent broken onboarding instructions.

3. **Codify repository conventions**
   - Add `CONTRIBUTING.md` with:
     - folder/module placement rules,
     - code style expectations,
     - naming and testing conventions,
     - PR checklist.

### Priority B — maintainability and extensibility

4. **Introduce explicit backend application-service layer**
   - Move request orchestration from route handlers to dedicated services/use-cases.
   - Keep routes as transport adapters only.
   - Benefit: better testability and easier adaptation to CLI/background job entry points.

5. **Extract API schemas into versioned modules**
   - Centralize Pydantic request/response models by API domain and version.
   - Benefit: easier contract evolution and lower risk of duplicate model drift.

6. **Unify quality tooling configs**
   - Add backend formatter/linter/type-checker standardization (e.g., `ruff` + `mypy` or agreed equivalent) with single command entry points.
   - Benefit: predictable code health and easier upgrades.

### Priority C — long-term developer experience

7. **Backend dependency locking strategy**
   - Add a lock/constraints workflow for Python dependencies (`pip-tools`, `uv lock`, or equivalent policy).
   - Benefit: reproducible environments and safer upgrades.

8. **Adopt architecture decision records (ADRs)**
   - Add `docs/adr/` and record key decisions (NLP adapter abstraction, typo-engine design, migration strategy, API versioning approach).
   - Benefit: easier adaptation by new contributors and future maintainers.

9. **Define test pyramid + pipeline split**
   - Explicitly categorize fast unit tests, integration tests, and regression fixture tests.
   - Map each category to CI stages with expected runtime budget.
   - Benefit: faster feedback without sacrificing confidence.

## Suggested 30-day improvement roadmap

- **Week 1:** `CONTRIBUTING.md`, root task runner (`Makefile`/`justfile`), and doc-command validation scripts.
- **Week 2:** Backend lint/type-check standardization and CI integration.
- **Week 3:** Route-to-use-case extraction for one API path as a pattern template.
- **Week 4:** Python lock/constraints strategy and first ADRs.

## Overall scorecard (non-functional)

- **Code tidiness:** 7.5/10
- **Compartmentalization:** 8/10
- **Documentation breadth:** 8/10
- **Upgrade readiness:** 6.5/10
- **Adaptability/extensibility:** 7.5/10

**Bottom line:** strong structure and promising architecture choices; biggest gains now come from workflow rigor and formalized engineering conventions.
