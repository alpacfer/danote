# Render + Vercel deployment

Danote's first hosted setup uses a Vercel static frontend and one Render Docker
web service for the FastAPI backend. Keep the Render backend scaled to one
instance while SQLite is the production database.

## Backend on Render

- Service type: Web Service
- Runtime: Docker
- Dockerfile: repo-root `Dockerfile`
- Health check path: `/api/health`
- Start command: use the Docker `CMD`
- Persistent disk mount: `/data`

Required backend environment:

```bash
DANOTE_ENV=production
DANOTE_AUTH_ENABLED=1
DANOTE_AUTH_PROVIDER=clerk
DANOTE_CLERK_ISSUER=https://<your-clerk-instance>
DANOTE_CLERK_JWKS_URL=https://<your-clerk-instance>/.well-known/jwks.json
DANOTE_ALLOWED_EMAILS=person@example.com,friend@example.com
DANOTE_DB_PATH=/data/danote.sqlite3
DANOTE_SEARCH_GEMINI_CACHE_PATH=/data/cache/en_gemini.sqlite
DANOTE_GEMINI_CHANGES_LOG_PATH=/data/gemini-applied-changes.jsonl
DANOTE_CORS_ORIGINS=https://<your-vercel-app>.vercel.app
```

Add the existing provider secrets in Render only: Gemini, DeepL or Azure
Translator, and Azure Speech.

## Frontend on Vercel

- Root directory: `frontend`
- Install command: `npm install`
- Build command: `npm run build`
- Output directory: `dist`

Required frontend environment:

```bash
VITE_BACKEND_URL=https://<your-render-service>.onrender.com
VITE_CLERK_PUBLISHABLE_KEY=<your-clerk-publishable-key>
```

## Smoke check

1. Open the Vercel URL and sign in with an allowlisted account.
2. Confirm the app reaches `GET /api/health`.
3. Add one word and one sentence.
4. Restart the Render service.
5. Refresh the Vercel app and confirm the word and sentence still exist.
