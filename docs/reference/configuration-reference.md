# Configuration reference

Canonical env var reference for backend runtime config.
Values loaded from: process env → `<repo-root>/.env.local` → hardcoded defaults in `backend/app/core/config.py`.

## Source precedence

`load_settings()` resolves with this precedence:

1. Env var exported in current shell/process.
2. Matching key in `<repo-root>/.env.local`.
3. Built-in default from `config.py`.

Notes:

- `.env.local` optional; absent = process env + defaults only.
- Env files use dotenv syntax, not shell syntax: `KEY=value`, optional
  matching quotes around values, blank lines and `#` comments. They are parsed
  without executing shell code.
- Replace angle-bracket placeholders such as `<paste-value-here>` before
  startup.
- Boolean flags: `0`, `false`, `no` (case-insensitive) = disabled; any other non-empty = enabled.
- `DANOTE_CORS_ORIGINS` comma-separated; empty/whitespace falls back to default local origins.
- Filesystem path values may be absolute or relative; relative paths resolve from the repo root.

## App/core

| Variable | Default | Accepted values | Interactions / fallbacks |
| --- | --- | --- | --- |
| `DANOTE_ENV` | `development` | Any string (for example `development`, `test`, `production`) | No special fallback behavior beyond standard precedence. |
| `DANOTE_APP_NAME` | `danote-backend` | Any non-empty string | App metadata/logging only. |
| `DANOTE_HOST` | `127.0.0.1` | Host/IP string | Paired with `DANOTE_PORT` for local bind. |
| `DANOTE_PORT` | `8000` | Integer string parseable by Python `int()` | Invalid integer raises at startup. |
| `DANOTE_CORS_ORIGINS` | `http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:4173,http://localhost:4173` (effective fallback) | Comma-separated origins | Empty/only commas/spaces falls back to default local origins tuple. `run-project.sh` appends the selected frontend origin when this is set. |

## Auth

| Variable | Default | Accepted values | Interactions / fallbacks |
| --- | --- | --- | --- |
| `DANOTE_AUTH_ENABLED` | `0` | Boolean-like (`1/0`, `true/false`, `yes/no`) | Disabled keeps local development on the seeded `local-dev` user. Enabled requires Clerk bearer tokens on app data routes. |
| `DANOTE_AUTH_PROVIDER` | `clerk` | `clerk` | Other values fail protected requests. |
| `DANOTE_CLERK_ISSUER` | unset (`None`) | Clerk issuer URL | Used as the JWT issuer check when auth is enabled. |
| `DANOTE_CLERK_JWKS_URL` | unset (`None`) | Clerk JWKS URL | Used to verify Clerk JWTs when `DANOTE_CLERK_PUBLIC_KEY` is not set. |
| `DANOTE_CLERK_PUBLIC_KEY` | unset (`None`) | PEM public key string | Optional networkless Clerk JWT verification path. |
| `DANOTE_ALLOWED_EMAILS` | unset (`()`) | Comma-separated email addresses | If set, authenticated users must match an email or allowed domain. |
| `DANOTE_ALLOWED_EMAIL_DOMAINS` | unset (`()`) | Comma-separated domains | If set, authenticated users must match an email or allowed domain. |
| `DANOTE_KEY_ENCRYPTION_SECRET` | unset (`None`) | Base64-encoded 32-byte secret | Required for hosted auth/key storage. Used to encrypt stored per-user API keys; rotating it invalidates existing stored keys. |

Guest sessions are accepted as bearer tokens when auth is enabled. They are
created by `POST /api/guest/sessions`, use host-level language-service keys,
and do not require API-key storage.

## Database

| Variable | Default | Accepted values | Interactions / fallbacks |
| --- | --- | --- | --- |
| `DANOTE_DB_PATH` | `backend/data/danote.sqlite3` | Any filesystem path | Relative paths resolve from repo root; parent dir must be writable at runtime. |

## NLP

| Variable | Default | Accepted values | Interactions / fallbacks |
| --- | --- | --- | --- |
| `DANOTE_NLP_MODEL` | `retired-dacy-disabled` | Future adapter/model identifier | The previous DaCy/spaCy/Lemmy stack is retired and not installed or loaded. |
| `DANOTE_NLP_ENABLED` | `0` | Boolean-like (`1/0`, `true/false`, `yes/no`) | `/api/analyze` remains unavailable unless a future NLP adapter is added and enabled. |

## Typo pipeline

| Variable | Default | Accepted values | Interactions / fallbacks |
| --- | --- | --- | --- |
| `DANOTE_TYPO_ENABLED` | `1` | Boolean-like (`1/0`, `true/false`, `yes/no`) | Controls typo services globally. |
| `DANOTE_TYPO_DICTIONARY_PATH` | unset (`None`) | Any filesystem path | Optional override dictionary path for typo logic. |

## Translation

| Variable | Default | Accepted values | Interactions / fallbacks |
| --- | --- | --- | --- |
| `DANOTE_TRANSLATION_ENABLED` | `1` | Boolean-like (`1/0`, `true/false`, `yes/no`) | Disables translation when falsey. |
| `DANOTE_TRANSLATION_PROVIDER` | `deepl` | Provider key string (`deepl`, `azure`, or provider impl alias) | Must match registered provider impl. |
| `DANOTE_TRANSLATION_DEEPL_API_KEY` | unset (`None`) | DeepL API key string | Required for DeepL in authenticated modes. |
| `DANOTE_TRANSLATION_DEEPL_ENDPOINT` | unset (`None`) | URL string | Optional endpoint override; provider defaults used when omitted. |
| `DANOTE_TRANSLATION_AZURE_API_KEY` | unset (`None`) | Azure Translator key string | Required when `DANOTE_TRANSLATION_PROVIDER=azure`. |
| `DANOTE_TRANSLATION_AZURE_REGION` | unset (`None`) | Azure region string | Required for most Azure Translator deployments. |
| `DANOTE_TRANSLATION_AZURE_ENDPOINT` | unset (`None`) | URL string | Optional custom endpoint override. |
| `DANOTE_TRANSLATION_AZURE_API_VERSION` | `3.0` | API version string | Used by Azure translation client requests. |

## TTS

| Variable | Default | Accepted values | Interactions / fallbacks |
| --- | --- | --- | --- |
| `DANOTE_TTS_ENABLED` | `1` | Boolean-like (`1/0`, `true/false`, `yes/no`) | Disables TTS when falsey. |
| `DANOTE_TTS_PROVIDER` | `azure` | Provider key string (`azure` or provider impl alias) | Must match registered TTS provider impl. |
| `DANOTE_TTS_AZURE_API_KEY` | unset (`None`) | Azure Speech key string | Required for Azure TTS. |
| `DANOTE_TTS_AZURE_REGION` | unset (`None`) | Azure region string | Required for Azure TTS unless endpoint-only setup. |
| `DANOTE_TTS_AZURE_ENDPOINT` | unset (`None`) | URL string | Optional endpoint override for Azure Speech. |
| `DANOTE_TTS_AZURE_VOICE_NAME` | `da-DK-ChristelNeural` | Voice name string recognized by provider | Defaults to Danish neural voice. |

## COR lookup

| Variable | Default | Accepted values | Interactions / fallbacks |
| --- | --- | --- | --- |
| `DANOTE_COR_LOOKUP_ENABLED` | `1` | Boolean-like (`1/0`, `true/false`, `yes/no`) | Disables COR lookup when falsey. |
| `DANOTE_COR_LOOKUP_TIMEOUT_SECONDS` | `4.0` | Float string parseable by Python `float()` | Invalid float raises at startup. |
| `DANOTE_COR_LOCAL_DB_PATH` | `backend/resources/dictionaries/cor.sqlite` | Any filesystem path | Relative paths resolve from repo root; must point to built COR SQLite file. |

## Word verification + Gemini aliases

| Variable | Default | Accepted values | Interactions / fallbacks |
| --- | --- | --- | --- |
| `DANOTE_WORD_VERIFICATION_ENABLED` | `1` | Boolean-like (`1/0`, `true/false`, `yes/no`) | Disables Gemini-based word verification when falsey. |
| `DANOTE_WORDBANK_BACKGROUND_JOB_WORKERS` | `4` | Integer string parseable by Python `int()` | Max concurrent wordbank background jobs in backend dispatcher. Values below `1` clamped to `1`. |
| `DANOTE_WORD_VERIFICATION_GEMINI_API_KEY` | fallback chain | Gemini API key string | Resolution: `DANOTE_WORD_VERIFICATION_GEMINI_API_KEY` → `DANOTE_GEMINI_API_KEY` → unset. |
| `DANOTE_WORD_VERIFICATION_GEMINI_MODEL` | `gemini-3.1-flash-lite` (via alias fallback) | Gemini model name string | Resolution: `DANOTE_WORD_VERIFICATION_GEMINI_MODEL` → `DANOTE_GEMINI_MODEL` → built-in default. |
| `DANOTE_GEMINI_API_KEY` | fallback chain | Gemini API key string | Resolution: `DANOTE_GEMINI_API_KEY` → `DANOTE_WORD_VERIFICATION_GEMINI_API_KEY` → unset. Alias for shared Gemini credentials. |
| `DANOTE_GEMINI_MODEL` | `gemini-3.1-flash-lite` (via alias fallback) | Gemini model name string | Resolution: `DANOTE_GEMINI_MODEL` → `DANOTE_WORD_VERIFICATION_GEMINI_MODEL` → built-in default. Alias for shared Gemini model config. |
| `DANOTE_GEMINI_CHANGES_LOG_PATH` | `backend/data/gemini-applied-changes.jsonl` | Any filesystem path | Relative paths resolve from repo root; audit log location for Gemini "apply changes" actions. |

## Search latency controls

| Variable | Default | Accepted values | Interactions / fallbacks |
| --- | --- | --- | --- |
| `DANOTE_SEARCH_GEMINI_CACHE` | `1` | Boolean-like (`1/0`, `true/false`, `yes/no`) | Enables persistent SQLite caching for deterministic English-search Gemini calls. |
| `DANOTE_SEARCH_GEMINI_CACHE_PATH` | `backend/resources/cache/en_gemini.sqlite` | Any filesystem path | Relative paths resolve from repo root; generated SQLite files are gitignored. |
| `DANOTE_SEARCH_PARALLEL` | `1` | Boolean-like (`1/0`, `true/false`, `yes/no`) | Enables thread-pool fan-out for independent English POS translations and batch COR filters. |
| `DANOTE_SEARCH_COR_BATCH` | `1` | Boolean-like (`1/0`, `true/false`, `yes/no`) | Enables the sidebar's single-request COR batch flow. The backend endpoint remains available for compatibility. |
| `DANOTE_SEARCH_BATCHED_GEMINI` | `1` | Boolean-like (`1/0`, `true/false`, `yes/no`) | Enables prompt batching for English translation and COR sense filtering. Set to `0` to compare against the legacy per-choice Gemini calls. |
| `DANOTE_SEARCH_ADMIN_ENABLED` | `0` | Boolean-like (`1/0`, `true/false`, `yes/no`) | Enables `POST /api/admin/clear-search-cache` for benchmark cold-cache runs; the endpoint clears host search Gemini caches and evicts per-user service bundles. |

## Trial and guest quota

| Variable | Default | Accepted values | Interactions / fallbacks |
| --- | --- | --- | --- |
| `DANOTE_TRIAL_ENABLED` | `1` | Boolean-like (`1/0`, `true/false`, `yes/no`) | Enables hosted-key metering for signed-in users without keys and guest users. |
| `DANOTE_TRIAL_DAILY_SEARCH_LIMIT` | `50` | Integer string parseable by Python `int()` | Distinct word searches per signed-in no-key user per reset day. |
| `DANOTE_GUEST_DAILY_SEARCH_LIMIT` | `20` | Integer string parseable by Python `int()` | Distinct word searches per anonymous guest browser id per reset day. |
| `DANOTE_TRIAL_RESET_TIMEZONE` | `Europe/Copenhagen` | IANA timezone string | Local date boundary used for signed-in trial and guest quota resets; invalid values fall back to UTC. |
