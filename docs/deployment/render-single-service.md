# Render single-service deployment

This is the easiest hosted path for danote. Render runs the repo-root Docker
image as one web service. The image serves both the React app and FastAPI API,
so there is no separate Vercel project and no custom domain required.

Use the Render URL directly, for example:

```text
https://danote-private-beta.onrender.com
```

## What this gives you

- Public HTTPS URL from Render.
- One Docker web service.
- Persistent SQLite on a Render disk mounted at `/data`.
- Clerk users and sign-in.
- Per-user encrypted API keys.

Use a paid Render web service with a persistent disk. Free/ephemeral storage is
not enough because the SQLite database must survive deploys and restarts.

## 1. Push the repo to GitHub

Render deploys from a GitHub repository. Push the current branch after the
hosting changes are committed.

## 2. Create the Render service

In Render:

1. Click **New +** → **Web Service**.
2. Connect the GitHub repo.
3. Select **Docker** runtime.
4. Use the repo root as the root directory.
5. Use the repo-root `Dockerfile`.
6. Leave the start command empty so Render uses the Docker `CMD`.
7. Set health check path to `/api/health`.
8. Use one instance only while SQLite is the production database.

## 3. Add a persistent disk

Add a Render persistent disk:

```text
Mount path: /data
Size: 1 GB minimum
```

The Docker image already stores the main SQLite database at
`/data/danote.sqlite3`, the Gemini change log at
`/data/gemini-applied-changes.jsonl`, and the English-search Gemini cache at
`/data/cache/en_gemini.sqlite`.

The English search dictionary is generated into the Docker image from the
tracked `backend/resources/dictionaries/english_wiki.jsonl` file during build.
If English searches only show Danish direct matches after a deploy, redeploy the
current Dockerfile and check the Render build logs for `build_english_sqlite.py`.

## 4. Configure Clerk

In Clerk:

1. Create a production/private-beta app.
2. Enable email/password.
3. Enable Google sign-in if desired.
4. Copy the publishable key.
5. Copy the issuer/front-end API URL.
6. Copy the JWKS URL.

You can use either Clerk's allowlist or danote's `DANOTE_ALLOWED_EMAILS` for
private beta access. Using both is fine.

## 5. Add Render environment variables

Set these on the Render service:

```bash
DANOTE_ENV=production
DANOTE_AUTH_ENABLED=1
DANOTE_AUTH_PROVIDER=clerk

VITE_CLERK_PUBLISHABLE_KEY=<clerk-publishable-key>
VITE_BACKEND_URL=

DANOTE_CLERK_ISSUER=<clerk-issuer-url>
DANOTE_CLERK_JWKS_URL=<clerk-jwks-url>
DANOTE_ALLOWED_EMAILS=you@example.com
DANOTE_ALLOWED_EMAIL_DOMAINS=

DANOTE_KEY_ENCRYPTION_SECRET=<base64-32-byte-secret>
DANOTE_CORS_ORIGINS=https://<your-render-service>.onrender.com
DANOTE_DB_PATH=/data/danote.sqlite3
DANOTE_GEMINI_CHANGES_LOG_PATH=/data/gemini-applied-changes.jsonl
DANOTE_SEARCH_GEMINI_CACHE_PATH=/data/cache/en_gemini.sqlite

DANOTE_TRANSLATION_PROVIDER=deepl
DANOTE_GEMINI_API_KEY=<gemini-key>
DANOTE_TRANSLATION_DEEPL_API_KEY=<deepl-key>
DANOTE_TRANSLATION_AZURE_API_KEY=<azure-translator-key>
DANOTE_TRANSLATION_AZURE_REGION=<azure-region>
DANOTE_TTS_AZURE_API_KEY=<azure-speech-key>
DANOTE_TTS_AZURE_REGION=<azure-region>
```

Generate `DANOTE_KEY_ENCRYPTION_SECRET` once:

```bash
openssl rand -base64 32
```

Save it in a password manager. If it is lost or rotated, users must re-enter
their stored API keys.

Keep `VITE_BACKEND_URL` empty because the frontend and backend are served from
the same Render origin.

## 6. Deploy

Click **Deploy Web Service**.

After the first deploy, open:

```text
https://<your-render-service>.onrender.com/api/health
```

The response should be JSON with `status` set to `ok` or a clearly explainable
degraded state.

## 7. First-user smoke test

1. Open the Render URL.
2. Sign in with an allowlisted email.
3. Confirm the API key setup gate appears.
4. Save Gemini, DeepL, Azure Translation, and Azure TTS keys.
5. Add one Danish word.
6. Add one sentence.
7. In Render, restart the service.
8. Refresh the app and confirm the word and sentence are still present.

If the data disappears after restart, the disk is missing or not mounted at
`/data`.

## 8. Current limitations

- Keep the service at one instance while using SQLite.
- Use Render's paid persistent disk; ephemeral filesystem deploys will lose
  user data.
- The first rollout should remain private beta until a two-user hosted smoke
  confirms the endpoint-level owner-isolation coverage in `ROADMAP.md` holds in
  the deployed environment.

## Troubleshooting

**The app boots but sign-in API calls return `401`.**
Check `DANOTE_CLERK_ISSUER` and `DANOTE_CLERK_JWKS_URL` against the same Clerk
app used by `VITE_CLERK_PUBLISHABLE_KEY`.

**The browser blocks API calls.**
Set `DANOTE_CORS_ORIGINS` to the exact Render URL.

**The app loses data after deploy or restart.**
Confirm the persistent disk is attached and mounted at `/data`.

**Render says the service is not listening on the expected port.**
Redeploy the current Dockerfile. The container command reads Render's `PORT`
environment variable and falls back to `8000` locally.
