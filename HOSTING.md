# Hosting danote

This is a step-by-step guide for putting your danote instance online so other
people can sign up. Most people will land on **VPS + Docker + Caddy** because
it is the cheapest, simplest, and plays well with SQLite.

> ⚠️ This release ships **Phase 1** of the multi-user model: sign-in with
> email/password or Google works, each account stores its own four API keys
> encrypted at rest, and the app is gated behind an "Set up your API keys"
> screen. Two deferred follow-ups are tracked separately:
>
> 1. **Per-request key resolution** — until this lands, outbound calls to
>    Gemini / DeepL / Azure still use the server-side env keys you set below.
>    Users save their own keys in the UI but the backend doesn't consume them
>    yet. Visible behaviour: sign-in + gating work perfectly; billing for
>    outbound API usage still hits the host's keys.
> 2. **Per-user data isolation** — until this lands, all signed-in users share
>    the same wordbank / sentencebank. Run a private deployment (allowlist
>    your own email) if that is a problem for now.

---

## 1. Pick a host

| Option | Cost | Pros | Cons |
|---|---|---|---|
| **VPS + Docker + Caddy** (Hetzner CX22, DigitalOcean) | ~$4–6/mo | Cheapest; persistent SQLite via Docker volume; one box for everything | You own the box (apt updates, backups) |
| **Fly.io** | ~$5/mo | Persistent volumes built in; great DX; global anycast | Vendor-specific config (`fly.toml`); usage-based pricing can surprise |
| **Vercel (frontend) + Render (backend)** | Free → $7+/mo | Familiar PaaS flow | SQLite is awkward on Render free (ephemeral disk); two deploys to keep in sync |

The rest of this guide uses **VPS + Docker + Caddy**. The Fly.io and split
options are sketched in §13.

---

## 2. Prerequisites

- A domain name (e.g. `danote.yourdomain.com`).
- DNS hosting where you can add an A record (Cloudflare is free and ideal).
- A free [Clerk](https://clerk.com) account for authentication.
- A Google AI Studio account for a Gemini key.
- Optional but used by some features: DeepL Pro, Azure Translator, Azure TTS.
- A credit card for the VPS provider (Hetzner / DigitalOcean / etc.).

---

## 3. Create a Clerk application

1. Go to <https://dashboard.clerk.com> and create a new application.
2. Under **User & Authentication → Email, Phone, Username** enable Email +
   Password.
3. Under **User & Authentication → Social Connections** enable Google.
4. Open **API Keys**. Copy:
   - The **Publishable key** (`pk_live_…` or `pk_test_…`) →
     `VITE_CLERK_PUBLISHABLE_KEY`.
   - The **JWKS URL** (under the "Frontend API" section, the
     `…/.well-known/jwks.json` URL) → `DANOTE_CLERK_JWKS_URL`.
   - The **Frontend API URL** (e.g. `https://clerk.yourdomain.com` or the
     Clerk-hosted equivalent) → `DANOTE_CLERK_ISSUER`.

Optional but recommended for a private beta: in **User & Authentication →
Restrictions** add an allowlist of approved email addresses. Or use the
backend's allowlist (§7) to do the same.

---

## 4. Get your external API keys

You set these as the host. (In Phase 1.5 each user will provide their own,
and these become only a fallback.)

| Provider | Where to get it |
|---|---|
| Gemini | <https://aistudio.google.com/app/apikey> |
| DeepL Pro | <https://www.deepl.com/your-account/keys> |
| Azure Translator | Azure portal → create a Translator resource → Keys & Endpoint |
| Azure Speech | Azure portal → create a Speech resource → Keys & Endpoint |

---

## 5. Provision the VPS

Any cheap Linux VPS works. Example using Hetzner Cloud (Ubuntu 22.04, CX22):

```bash
# On your laptop, after creating the server:
ssh root@<server-ip>

# Update + minimal hardening
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

# Install Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker danote

# Switch to the unprivileged user from now on
su - danote
```

---

## 6. Clone the repo

```bash
cd ~
git clone https://github.com/<your-fork>/danote.git
cd danote
```

---

## 7. Write your `.env`

The repo ships a root `.env.example`. Copy it:

```bash
cp .env.example .env
```

Then edit `.env`. The keys that matter for hosting:

```ini
# Frontend
VITE_CLERK_PUBLISHABLE_KEY=pk_live_xxx
VITE_BACKEND_URL=

# Auth
DANOTE_AUTH_ENABLED=1
DANOTE_CLERK_JWKS_URL=https://your-clerk-frontend-api/.well-known/jwks.json
DANOTE_CLERK_ISSUER=https://your-clerk-frontend-api
# Optional: keep deployment private during beta
DANOTE_AUTH_ALLOWED_EMAILS=
DANOTE_AUTH_ALLOWED_EMAIL_DOMAINS=

# Encryption of stored user API keys.
# Generate ONCE: `openssl rand -base64 32`. DO NOT lose it — rotating
# this secret invalidates every stored user key.
DANOTE_KEY_ENCRYPTION_SECRET=<paste-base64-32-bytes-here>

# CORS — only the public hostnames the frontend will load from.
DANOTE_CORS_ORIGINS=https://danote.example.com

# Outbound API keys (Phase 1 fallback while per-request key resolution
# is implemented). Sign up for each provider in §4.
DANOTE_GEMINI_API_KEY=...
DANOTE_TRANSLATION_DEEPL_API_KEY=...
DANOTE_TRANSLATION_AZURE_API_KEY=...
DANOTE_TRANSLATION_AZURE_REGION=...
DANOTE_TTS_AZURE_API_KEY=...
DANOTE_TTS_AZURE_REGION=...
```

Generate the master encryption key:

```bash
openssl rand -base64 32
```

Paste that value into `DANOTE_KEY_ENCRYPTION_SECRET`. **Save a copy in your
password manager.** If you lose it, every user has to re-enter their API keys.

---

## 8. Point DNS at the box

In Cloudflare (or whichever DNS provider), add an **A record**:

```
Name:    danote (or @ for apex)
Value:   <your-VPS-public-IP>
Proxy:   off (grey cloud) — Caddy handles TLS directly
```

Wait a minute, confirm with `dig danote.example.com` from your laptop.

Edit `Caddyfile` and replace `danote.example.com` with your real domain.

---

## 9. Build and start

```bash
docker compose up -d --build
docker compose logs -f app
```

You should see migrations apply (including `027_users_and_api_keys.sql`) and
the line `Uvicorn running on http://0.0.0.0:8000`. Caddy will negotiate a
Let's Encrypt cert within ~30 seconds.

Sanity check:

```bash
curl -sS https://danote.example.com/api/health | jq .
```

Should return `{"status":"ok",...}`.

---

## 10. First-run smoke test

1. Open `https://danote.example.com` in a browser.
2. Click **Create account**, complete the Clerk signup flow (email + password
   or Google).
3. You should land on the **Configure your API keys** screen. Paste keys for
   Gemini, DeepL, Azure Translation, Azure TTS. Hit Save on each.
4. When all four are marked "Set", the app loads.
5. Open the **Account** page from the sidebar (or press `Alt + A`). Verify
   all four keys are listed and your email/profile shows in the user button.
6. Click into Wordbank, add a Danish word, confirm translations come back.

---

## 11. Backups

SQLite lives in the `danote-data` Docker volume. The simplest backup is a
nightly cron job that copies the WAL-consistent snapshot off-box:

```bash
# /etc/cron.daily/danote-backup
#!/bin/bash
set -e
DEST=/backups/danote-$(date -u +%Y%m%dT%H%M%SZ).sqlite3.gz
docker compose -f /home/danote/danote/docker-compose.yml exec -T app \
  sqlite3 /data/danote.sqlite3 ".backup '/tmp/snapshot.sqlite3'"
docker cp danote-app:/tmp/snapshot.sqlite3 - | gzip > "$DEST"
# Optionally: rclone copy "$DEST" b2:my-bucket/
find /backups -name 'danote-*.sqlite3.gz' -mtime +30 -delete
```

---

## 12. Updating

```bash
cd ~/danote
git pull
docker compose up -d --build
```

Migrations apply automatically on container start. Roll back by checking out
the previous commit and rebuilding.

---

## 13. Alternative hosts

### Fly.io

```bash
fly launch --no-deploy
# Create a 1GB volume for SQLite:
fly volumes create danote_data --size 1
# Set secrets (DO NOT bake the encryption secret into the image):
fly secrets set DANOTE_KEY_ENCRYPTION_SECRET="$(openssl rand -base64 32)" \
  DANOTE_CLERK_JWKS_URL=... DANOTE_CLERK_ISSUER=... \
  DANOTE_GEMINI_API_KEY=... \
  VITE_CLERK_PUBLISHABLE_KEY=pk_live_...
fly deploy
```

Mount the volume to `/data` in `fly.toml`:

```toml
[mounts]
  source = "danote_data"
  destination = "/data"
```

### Vercel (frontend) + Render (backend)

Works but more moving parts:

- Build the SPA on Vercel from `frontend/` with `VITE_CLERK_PUBLISHABLE_KEY`
  and `VITE_BACKEND_URL` (set to the Render URL).
- Deploy the backend on Render as a Docker service. SQLite on Render free is
  ephemeral — pay for a persistent disk add-on, or migrate to Postgres in
  Phase 2.
- Set `DANOTE_CORS_ORIGINS=https://your-vercel-app.vercel.app` on Render.

---

## 14. Troubleshooting

**`401 unauthorized` on every API call after sign-in.**
- `DANOTE_CLERK_JWKS_URL` does not match the Clerk frontend you signed in
  against. Double-check both `JWKS_URL` and `ISSUER`.
- Server clock drift > 60s. Run `timedatectl status` and `ntpdate` if needed.

**`auth_jwks_unavailable`.**
- The container can't reach Clerk. Check outbound HTTPS, DNS inside the
  container: `docker compose exec app curl -I https://api.clerk.com`.

**`key_encryption_secret_missing` in logs.**
- `DANOTE_KEY_ENCRYPTION_SECRET` not set. Existing keys can't be decrypted
  without it. Users will see all four providers as "Not set" until they
  re-enter.

**SPA loads but `/api/*` is 404.**
- `DANOTE_SERVE_FRONTEND=1` is correct in the image, but check the container
  isn't shadowing the API router. The mount happens **after** the API router
  registration in `app_factory.py` — verify your fork didn't reorder it.

**Caddy can't get a cert.**
- DNS isn't propagated yet, or Cloudflare proxy is on (orange cloud). Turn
  the cloud grey for the first issuance, then turn it back on.

---

## 15. What to expect next

Phase 1.5 (per-request key resolution) will switch outbound calls to use the
key stored on the calling user's account. After that, the host-level
`DANOTE_GEMINI_API_KEY` etc. become optional fallbacks rather than the
working keys.

Phase 2 (data isolation) will add `owner_user_id` to every data table and
update the wordbank / sentencebank queries to filter by it, so each user
sees their own data. Until then, run a private deployment if you don't want
shared content.
