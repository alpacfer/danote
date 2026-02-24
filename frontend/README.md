# Frontend

React + TypeScript + Vite UI for Danote.

## Run

```bash
cd frontend
npm install
# optional when backend is not default
# export VITE_BACKEND_URL=http://127.0.0.1:8000
npm run dev -- --host 127.0.0.1 --port 4173
```

## Test

```bash
cd frontend
npm run test
```

## Build

```bash
cd frontend
npm run build
```

## Key UX Behaviors (Current Prototype)

- Backend connection badge (`connected`, `degraded`, `offline`).
- Debounced auto-analysis for finalized tokens.
- Stale response protection (latest request wins).
- Detected words table with status and match source.
- Add-to-wordbank action for `new` tokens with Sonner feedback.
