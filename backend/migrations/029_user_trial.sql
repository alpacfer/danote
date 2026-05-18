-- 029_user_trial.sql
-- Free-trial support: users who have not configured their own API keys can
-- opt into a capped daily quota that runs on the host fallback services.
-- Builds on app_users (027) and complements user_api_keys (028).

ALTER TABLE app_users ADD COLUMN trial_opted_in_at TEXT;

CREATE TABLE IF NOT EXISTS user_search_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_user_id INTEGER NOT NULL,
  usage_date TEXT NOT NULL,           -- YYYY-MM-DD in the trial reset timezone
  query_key TEXT NOT NULL,            -- normalized distinct word looked up
  created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  UNIQUE (owner_user_id, usage_date, query_key),
  FOREIGN KEY (owner_user_id) REFERENCES app_users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_search_usage_owner_date
  ON user_search_usage(owner_user_id, usage_date);
