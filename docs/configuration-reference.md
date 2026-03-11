# Configuration reference

This document is the canonical environment variable reference for backend runtime configuration.
All values are loaded from process environment variables first, then from `<repo-root>/.env.local`, and finally from hardcoded defaults in `backend/app/core/config.py`.

## Source precedence

`load_settings()` resolves values with this precedence:

1. Environment variable exported in the current shell/process.
2. Matching key in `<repo-root>/.env.local`.
3. Built-in default from `config.py`.

Notes:

- `.env.local` is optional; if it does not exist, only process env and defaults are used.
- Boolean flags treat `0`, `false`, and `no` (case-insensitive) as disabled; any other non-empty value is enabled.
- `DANOTE_CORS_ORIGINS` is comma-separated; empty or whitespace-only falls back to default local origins.

## App/core

| Variable | Default | Accepted values | Interactions / fallbacks |
| --- | --- | --- | --- |
| `DANOTE_ENV` | `development` | Any string (for example `development`, `test`, `production`) | No special fallback behavior beyond standard precedence. |
| `DANOTE_APP_NAME` | `danote-backend` | Any non-empty string | Used in app metadata/logging only. |
| `DANOTE_HOST` | `127.0.0.1` | Host/IP string | Usually paired with `DANOTE_PORT` for local bind address. |
| `DANOTE_PORT` | `8000` | Integer string parseable by Python `int()` | Invalid integer values raise at startup. |
| `DANOTE_CORS_ORIGINS` | `http://127.0.0.1:4173,http://localhost:4173` (effective fallback) | Comma-separated origins | Empty string or only commas/spaces falls back to default local origins tuple. |

## Database

| Variable | Default | Accepted values | Interactions / fallbacks |
| --- | --- | --- | --- |
| `DANOTE_DB_PATH` | `backend/data/danote.sqlite3` | Any filesystem path | Path is consumed as `Path(...)`; parent directory must be writable at runtime. |

## NLP

| Variable | Default | Accepted values | Interactions / fallbacks |
| --- | --- | --- | --- |
| `DANOTE_NLP_MODEL` | `da_dacy_small_trf-0.2.0` | Installed spaCy/DaCy model name | Used when NLP adapter is enabled. |
| `DANOTE_NLP_ENABLED` | `1` | Boolean-like (`1/0`, `true/false`, `yes/no`) | Disabled when value is `0`, `false`, or `no` (case-insensitive). |

## Typo pipeline

| Variable | Default | Accepted values | Interactions / fallbacks |
| --- | --- | --- | --- |
| `DANOTE_TYPO_ENABLED` | `1` | Boolean-like (`1/0`, `true/false`, `yes/no`) | Controls typo services globally. |
| `DANOTE_TYPO_DICTIONARY_PATH` | unset (`None`) | Any filesystem path | Optional override dictionary path for typo logic. |

## Translation

| Variable | Default | Accepted values | Interactions / fallbacks |
| --- | --- | --- | --- |
| `DANOTE_TRANSLATION_ENABLED` | `1` | Boolean-like (`1/0`, `true/false`, `yes/no`) | Disables translation features when falsey. |
| `DANOTE_TRANSLATION_PROVIDER` | `deepl` | Provider key string (`deepl`, `azure`, or provider implementation alias used by app code) | Must correspond to a registered provider implementation. |
| `DANOTE_TRANSLATION_DEEPL_API_KEY` | unset (`None`) | DeepL API key string | Required for DeepL provider in authenticated modes. |
| `DANOTE_TRANSLATION_DEEPL_ENDPOINT` | unset (`None`) | URL string | Optional endpoint override; provider defaults are used when omitted. |
| `DANOTE_TRANSLATION_AZURE_API_KEY` | unset (`None`) | Azure Translator key string | Required when `DANOTE_TRANSLATION_PROVIDER=azure`. |
| `DANOTE_TRANSLATION_AZURE_REGION` | unset (`None`) | Azure region string | Required for many Azure Translator deployments. |
| `DANOTE_TRANSLATION_AZURE_ENDPOINT` | unset (`None`) | URL string | Optional custom endpoint override. |
| `DANOTE_TRANSLATION_AZURE_API_VERSION` | `3.0` | API version string | Used by Azure translation client requests. |

## TTS

| Variable | Default | Accepted values | Interactions / fallbacks |
| --- | --- | --- | --- |
| `DANOTE_TTS_ENABLED` | `1` | Boolean-like (`1/0`, `true/false`, `yes/no`) | Disables TTS features when falsey. |
| `DANOTE_TTS_PROVIDER` | `azure` | Provider key string (`azure` or provider implementation alias used by app code) | Must correspond to a registered TTS provider implementation. |
| `DANOTE_TTS_AZURE_API_KEY` | unset (`None`) | Azure Speech key string | Required for Azure TTS requests. |
| `DANOTE_TTS_AZURE_REGION` | unset (`None`) | Azure region string | Required for Azure TTS unless endpoint-only setup is used. |
| `DANOTE_TTS_AZURE_ENDPOINT` | unset (`None`) | URL string | Optional endpoint override for Azure Speech. |
| `DANOTE_TTS_AZURE_VOICE_NAME` | `da-DK-ChristelNeural` | Voice name string recognized by provider | Defaults to Danish neural voice. |

## COR lookup

| Variable | Default | Accepted values | Interactions / fallbacks |
| --- | --- | --- | --- |
| `DANOTE_COR_LOOKUP_ENABLED` | `1` | Boolean-like (`1/0`, `true/false`, `yes/no`) | Disables COR lookup path when falsey. |
| `DANOTE_COR_LOOKUP_TIMEOUT_SECONDS` | `4.0` | Float string parseable by Python `float()` | Invalid float values raise at startup. |
| `DANOTE_COR_LOCAL_DB_PATH` | `backend/resources/dictionaries/cor.sqlite` | Any filesystem path | Should point to a built COR SQLite file. |

## Word verification + Gemini aliases

| Variable | Default | Accepted values | Interactions / fallbacks |
| --- | --- | --- | --- |
| `DANOTE_WORD_VERIFICATION_ENABLED` | `1` | Boolean-like (`1/0`, `true/false`, `yes/no`) | Disables Gemini-based word verification when falsey. |
| `DANOTE_WORD_VERIFICATION_GEMINI_API_KEY` | fallback chain | Gemini API key string | Resolution order: explicit `DANOTE_WORD_VERIFICATION_GEMINI_API_KEY` -> fallback `DANOTE_GEMINI_API_KEY` -> unset. |
| `DANOTE_WORD_VERIFICATION_GEMINI_MODEL` | `gemini-3.1-flash-lite-preview` (via alias fallback) | Gemini model name string | Resolution order: explicit `DANOTE_WORD_VERIFICATION_GEMINI_MODEL` -> fallback `DANOTE_GEMINI_MODEL` -> built-in default. |
| `DANOTE_GEMINI_API_KEY` | fallback chain | Gemini API key string | Resolution order: explicit `DANOTE_GEMINI_API_KEY` -> fallback `DANOTE_WORD_VERIFICATION_GEMINI_API_KEY` -> unset. Acts as alias for shared Gemini credentials. |
| `DANOTE_GEMINI_MODEL` | `gemini-3.1-flash-lite-preview` (via alias fallback) | Gemini model name string | Resolution order: explicit `DANOTE_GEMINI_MODEL` -> fallback `DANOTE_WORD_VERIFICATION_GEMINI_MODEL` -> built-in default. Acts as alias for shared Gemini model config. |
| `DANOTE_GEMINI_CHANGES_LOG_PATH` | `backend/data/gemini-applied-changes.jsonl` | Any filesystem path | Controls audit log location for Gemini “apply changes” actions. |
