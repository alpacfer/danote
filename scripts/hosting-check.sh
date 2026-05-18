#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -n "${HOSTING_ENV_FILE:-}" ]]; then
  ENV_FILE="$HOSTING_ENV_FILE"
elif [[ -f "$ROOT_DIR/.env" ]]; then
  ENV_FILE="$ROOT_DIR/.env"
else
  ENV_FILE="$ROOT_DIR/.env.local"
fi
CADDYFILE="${HOSTING_CADDYFILE:-$ROOT_DIR/Caddyfile}"
DOMAIN="${DANOTE_PUBLIC_DOMAIN:-}"
STRICT="${HOSTING_CHECK_STRICT:-0}"

log() {
  printf '[hosting-check] %s\n' "$1"
}

fail() {
  printf '[hosting-check] ERROR: %s\n' "$1" >&2
  exit 1
}

warn() {
  printf '[hosting-check] WARN: %s\n' "$1" >&2
}

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s\n' "$value"
}

is_placeholder() {
  local value
  value="$(trim "$1")"
  [[ "$value" == \<*\> || "$value" == *"your-"* || "$value" == *"example.com"* || "$value" == "..." ]]
}

env_value() {
  local key="$1"
  if [[ ! -f "$ENV_FILE" ]]; then
    return 1
  fi
  awk -F= -v key="$key" '
    $0 ~ /^[[:space:]]*#/ || $0 !~ /=/ { next }
    {
      k=$1
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", k)
      if (k == key) {
        sub(/^[^=]*=/, "", $0)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", $0)
        print $0
      }
    }
  ' "$ENV_FILE" | tail -n 1
}

require_env() {
  local key="$1"
  local value
  value="$(env_value "$key" || true)"
  if [[ -z "$value" ]]; then
    fail "$key is required in ${ENV_FILE#$ROOT_DIR/}"
  fi
  if is_placeholder "$value"; then
    fail "$key in ${ENV_FILE#$ROOT_DIR/} still looks like a placeholder"
  fi
  log "$key: set"
}

optional_env() {
  local key="$1"
  local value
  value="$(env_value "$key" || true)"
  if [[ -z "$value" ]]; then
    log "$key: unset"
    return
  fi
  if is_placeholder "$value"; then
    fail "$key in ${ENV_FILE#$ROOT_DIR/} still looks like a placeholder"
  fi
  log "$key: set"
}

[[ -f "$ENV_FILE" ]] || fail "env file not found: ${ENV_FILE#$ROOT_DIR/}. Copy .env.example to .env for VPS hosting."
[[ -f "$CADDYFILE" ]] || fail "Caddyfile not found: ${CADDYFILE#$ROOT_DIR/}"

log "checking ${ENV_FILE#$ROOT_DIR/}"
auth_enabled="$(env_value DANOTE_AUTH_ENABLED || true)"
if [[ -z "$auth_enabled" ]]; then
  if [[ "$STRICT" == "1" ]]; then
    fail "DANOTE_AUTH_ENABLED is required in ${ENV_FILE#$ROOT_DIR/}"
  fi
  warn "DANOTE_AUTH_ENABLED is unset; local defaults disable auth"
  auth_enabled="0"
else
  log "DANOTE_AUTH_ENABLED: set"
fi

if [[ "$auth_enabled" != "0" && "$auth_enabled" != "false" && "$auth_enabled" != "no" ]]; then
  require_env VITE_CLERK_PUBLISHABLE_KEY
  require_env DANOTE_CLERK_JWKS_URL
  require_env DANOTE_CLERK_ISSUER
elif [[ "$STRICT" == "1" ]]; then
  fail "DANOTE_AUTH_ENABLED must be 1/true/yes for VPS hosting"
else
  warn "auth is disabled; this is okay for local smoke, not VPS hosting"
  optional_env VITE_CLERK_PUBLISHABLE_KEY
  optional_env DANOTE_CLERK_JWKS_URL
  optional_env DANOTE_CLERK_ISSUER
fi

require_env DANOTE_KEY_ENCRYPTION_SECRET
if [[ "$STRICT" == "1" ]]; then
  require_env DANOTE_CORS_ORIGINS
else
  optional_env DANOTE_CORS_ORIGINS
fi
require_env DANOTE_GEMINI_API_KEY
require_env DANOTE_TRANSLATION_DEEPL_API_KEY
require_env DANOTE_TTS_AZURE_API_KEY
require_env DANOTE_TTS_AZURE_REGION
optional_env DANOTE_ALLOWED_EMAILS
optional_env DANOTE_ALLOWED_EMAIL_DOMAINS
optional_env DANOTE_TRANSLATION_AZURE_API_KEY
optional_env DANOTE_TRANSLATION_AZURE_REGION

if grep -q 'danote.example.com' "$CADDYFILE"; then
  if [[ "$STRICT" == "1" ]]; then
    fail "Caddyfile still contains danote.example.com; replace it with your real domain before VPS deploy"
  fi
  warn "Caddyfile still contains danote.example.com; replace it before VPS deploy"
fi

if [[ -n "$DOMAIN" ]] && ! grep -q "$DOMAIN" "$CADDYFILE"; then
  fail "DANOTE_PUBLIC_DOMAIN=$DOMAIN is not present in Caddyfile"
fi
log "Caddyfile domain: configured"

(
  cd "$ROOT_DIR"
  docker compose config --no-env-resolution --quiet
)
log "docker compose config: ok"
log "hosting readiness checks passed"
