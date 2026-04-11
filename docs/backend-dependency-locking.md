# Backend Dependency Locking

## Canonical files

- Input requirements:
  - `backend/requirements.txt`
  - `backend/requirements-dev.txt`
- Lock output:
  - `backend/requirements.lock.txt`

## Install behavior

Lock file for reproducible local/CI backend setup.

```bash
cd <repo-root>
make setup-backend
```

## Refresh workflow

When backend dependency inputs change:

```bash
cd <repo-root>
./scripts/sync-backend-lock.sh
```

If `pip-tools` missing:

```bash
python3 -m pip install pip-tools
```

## PR requirement

Dependency change must include updated `backend/requirements.lock.txt` same PR.