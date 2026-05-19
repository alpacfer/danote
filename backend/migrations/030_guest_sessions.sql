-- 030_guest_sessions.sql
-- Guest access creates fresh per-session users while metering daily usage by
-- an anonymous browser id hash so notes reset without resetting quota.

CREATE TABLE IF NOT EXISTS guest_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_user_id INTEGER NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  browser_id_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  last_seen_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  FOREIGN KEY (owner_user_id) REFERENCES app_users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_guest_sessions_owner
  ON guest_sessions(owner_user_id);

CREATE INDEX IF NOT EXISTS idx_guest_sessions_browser
  ON guest_sessions(browser_id_hash);

CREATE TABLE IF NOT EXISTS guest_search_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  browser_id_hash TEXT NOT NULL,
  usage_date TEXT NOT NULL,
  query_key TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  UNIQUE (browser_id_hash, usage_date, query_key)
);

CREATE INDEX IF NOT EXISTS idx_guest_search_usage_browser_date
  ON guest_search_usage(browser_id_hash, usage_date);
