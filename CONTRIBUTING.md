# Contributing to danote

Thanks for contributing! This guide standardizes development workflow and repository conventions.

## Quick start

```bash
cd <repo-root>
make setup
make lint
make test
```

To run the app locally:

```bash
make dev
```

## Repository conventions

- `frontend/`: React/Vite UI and frontend tests.
- `backend/`: FastAPI service, NLP integration, domain services, and DB layer.
- `docs/`: product, architecture, contracts, and process documentation.
- `scripts/`: reproducible helper scripts used by docs and CI.

### Backend placement rules

- `backend/app/api/routes/`: HTTP transport layer only.
- `backend/app/services/`: domain/application service logic.
- `backend/app/nlp/`: NLP adapter interfaces and implementations.
- `backend/app/db/`: migration and DB helper concerns.

### Testing conventions

- Unit tests: fast, deterministic, small dependency surface.
- Integration tests: may exercise startup + API composition.
- Regression tests: fixture/golden based behavior validation.

## Required local checks before PR

```bash
make lint
make test
make docs-smoke
```

## Pull request checklist

- [ ] Changes are scoped and documented.
- [ ] `make lint` passes.
- [ ] `make test` passes.
- [ ] `make docs-smoke` passes.
- [ ] Docs are updated when command/workflow behavior changes.


## AI agent workflow

- Read `AGENTS.md` first for deterministic command order and boundaries.
- Use `docs/agent-playbook.md` for architecture-oriented edit strategy.
- Run `make agent-verify` before finalizing significant backend changes.
