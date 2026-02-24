ALTER TABLE surface_forms ADD COLUMN seen_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE surface_forms ADD COLUMN last_seen_at TEXT;

CREATE TABLE IF NOT EXISTS token_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  raw_token TEXT NOT NULL,
  normalized_token TEXT NOT NULL,
  final_status TEXT NOT NULL,
  top_suggestion TEXT,
  confidence REAL,
  latency_ms REAL,
  context_window TEXT,
  created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)
);

CREATE INDEX IF NOT EXISTS idx_token_events_normalized_token ON token_events(normalized_token);
CREATE INDEX IF NOT EXISTS idx_token_events_created_at ON token_events(created_at);

CREATE TABLE IF NOT EXISTS typo_feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  raw_token TEXT NOT NULL,
  predicted_status TEXT NOT NULL,
  suggestions_shown TEXT,
  user_action TEXT NOT NULL,
  chosen_value TEXT,
  created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)
);

CREATE INDEX IF NOT EXISTS idx_typo_feedback_raw_token ON typo_feedback(raw_token);
CREATE INDEX IF NOT EXISTS idx_typo_feedback_created_at ON typo_feedback(created_at);

CREATE TABLE IF NOT EXISTS ignored_tokens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  token TEXT NOT NULL COLLATE NOCASE,
  scope TEXT NOT NULL DEFAULT 'global',
  expires_at TEXT,
  created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  UNIQUE(token, scope)
);

CREATE INDEX IF NOT EXISTS idx_ignored_tokens_token ON ignored_tokens(token);
