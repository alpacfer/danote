# VPS private beta deployment guide

Use this guide when you are ready to put danote on a single VPS with Docker,
Caddy, Clerk auth, and persistent SQLite. It assumes the local Docker smoke has
already passed.

## What you need before starting

- A domain or subdomain, for example `danote.example.com`.
- DNS access for that domain.
- A VPS running Ubuntu 22.04 or newer.
- A Clerk application for production/private beta sign-in.
- Provider keys for Gemini, DeepL, Azure Translator, and Azure Speech.
- One or more beta user email addresses for `DANOTE_ALLOWED_EMAILS`.

## 1. Prepare Clerk

In Clerk, create or open the production app:

1. Enable email/password sign-in.
2. Enable Google sign-in if desired.
3. Copy the publishable key into `VITE_CLERK_PUBLISHABLE_KEY`.
4. Copy the issuer/front-end API URL into `DANOTE_CLERK_ISSUER`.
5. Copy the JWKS URL into `DANOTE_CLERK_JWKS_URL`.
6. Add a private beta allowlist in Clerk, or use `DANOTE_ALLOWED_EMAILS` in
   danote's backend env.

## 2. Provision the VPS

SSH to the new server as root, then run:

```bash
apt update && apt -y upgrade
adduser danote --gecos "" --disabled-password
usermod -aG sudo danote
mkdir -p /home/danote/.ssh
cp ~/.ssh/authorized_keys /home/danote/.ssh/
chown -R danote: /home/danote/.ssh
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw --force enable

curl -fsSL https://get.docker.com | sh
usermod -aG docker danote
su - danote
```

Clone the repository:

```bash
git clone https://github.com/<your-fork-or-origin>/danote.git
cd danote
```

## 3. Configure DNS and Caddy

In your DNS provider, create an A record:

```text
Name:  danote
Value: <your-vps-public-ip>
Proxy: off for first certificate issuance if using Cloudflare
```

Then edit `Caddyfile` and replace `danote.example.com` with your real domain.

## 4. Create the VPS `.env`

```bash
cp .env.example .env
openssl rand -base64 32
```

Paste the generated value into `DANOTE_KEY_ENCRYPTION_SECRET` and save the
same value in your password manager. Losing it invalidates stored user API
keys.

Set these production values in `.env`:

```bash
DANOTE_ENV=production
VITE_CLERK_PUBLISHABLE_KEY=pk_live_...
VITE_BACKEND_URL=

DANOTE_AUTH_ENABLED=1
DANOTE_AUTH_PROVIDER=clerk
DANOTE_CLERK_ISSUER=https://<your-clerk-instance>
DANOTE_CLERK_JWKS_URL=https://<your-clerk-instance>/.well-known/jwks.json
DANOTE_ALLOWED_EMAILS=you@example.com
DANOTE_ALLOWED_EMAIL_DOMAINS=
DANOTE_KEY_ENCRYPTION_SECRET=<generated-base64-secret>
DANOTE_CORS_ORIGINS=https://<your-domain>

DANOTE_TRANSLATION_PROVIDER=deepl
DANOTE_GEMINI_API_KEY=<gemini-key>
DANOTE_TRANSLATION_DEEPL_API_KEY=<deepl-key>
DANOTE_TRANSLATION_AZURE_API_KEY=<azure-translator-key>
DANOTE_TRANSLATION_AZURE_REGION=<azure-region>
DANOTE_TTS_AZURE_API_KEY=<azure-speech-key>
DANOTE_TTS_AZURE_REGION=<azure-region>
```

Keep `VITE_BACKEND_URL` empty for this Docker/Caddy setup because the built
SPA and API are served from the same origin.

## 5. Run preflight checks

Run the regular and strict checks:

```bash
make hosting-check
HOSTING_CHECK_STRICT=1 make hosting-check
```

Strict mode should pass only after Clerk, Caddy, CORS, auth, and provider keys
are configured.

## 6. Start production

```bash
docker compose up -d --build
docker compose logs -f app
```

Check health from your laptop:

```bash
curl -sS https://<your-domain>/api/health
```

The response should include `"status":"ok"` or a clearly explainable degraded
status.

## 7. First user smoke test

1. Open `https://<your-domain>`.
2. Sign in with an allowlisted email.
3. Confirm the API key setup gate appears.
4. Save Gemini, DeepL, Azure Translation, and Azure TTS keys.
5. Add one Danish word in Wordbank.
6. Add one sentence in Sentencebank.
7. Restart the app:

```bash
docker compose restart app
```

8. Refresh the app and confirm the word and sentence are still present.

## 8. Backups

Create `/etc/cron.daily/danote-backup` as root:

```bash
#!/bin/bash
set -euo pipefail
DEST=/backups/danote-$(date -u +%Y%m%dT%H%M%SZ).sqlite3.gz
mkdir -p /backups
docker compose -f /home/danote/danote/docker-compose.yml exec -T app \
  sqlite3 /data/danote.sqlite3 ".backup '/tmp/snapshot.sqlite3'"
docker cp danote-app:/tmp/snapshot.sqlite3 - | gzip > "$DEST"
find /backups -name 'danote-*.sqlite3.gz' -mtime +30 -delete
```

Then:

```bash
chmod +x /etc/cron.daily/danote-backup
/etc/cron.daily/danote-backup
ls -lh /backups
```

## 9. Updating

```bash
cd /home/danote/danote
git pull
make hosting-check
HOSTING_CHECK_STRICT=1 make hosting-check
docker compose up -d --build
curl -sS https://<your-domain>/api/health
```

## Current local status

As of the latest local smoke, the production Docker image builds, Compose
starts, `/api/health` passes on `127.0.0.1:8000`, and the SPA root returns
HTML. The remaining work is operator-owned: domain, DNS, Clerk production
values, VPS provisioning, and private-beta account allowlisting.
