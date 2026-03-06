## Summary

-

## Validation

- [ ] `make lint`
- [ ] `make maintainability-check`
- [ ] `make test`
- [ ] `make docs-smoke`
- [ ] If backend orchestration changed: `cd backend && PYTHONPATH=. pytest -q tests/test_use_cases_unit.py`

## Maintainability triggers

- [ ] If I touched a file >450 lines and added non-trivial logic, I included a split/refactor in this PR.
- [ ] I kept route handlers thin and preserved layering (`routes -> schemas -> use_cases -> domain services`).
