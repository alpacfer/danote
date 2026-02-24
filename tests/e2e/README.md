# E2E Regression

Current e2e regression is script-based:

```bash
cd /home/alejandro/Documents/github/danote/danote
./scripts/e2e-regression.sh
```

It validates:

- backend startup and health reachability
- canonical analyze flow (`Jeg kan godt lide bogen`)
- add-word flow (`kat`)
- backend restart persistence (`kat` remains known)

For manual browser e2e flow, use `docs/manual-demo-script.md`.
