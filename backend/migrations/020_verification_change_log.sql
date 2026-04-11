CREATE TABLE IF NOT EXISTS verification_change_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stored_lemma TEXT NOT NULL,
    stored_surface_form TEXT,
    meaning_id INTEGER,
    action_type TEXT NOT NULL,
    before_json TEXT NOT NULL,
    after_json TEXT NOT NULL,
    applied_at TEXT NOT NULL,
    reverted_at TEXT,
    provider TEXT
);

CREATE INDEX IF NOT EXISTS idx_vcl_lemma ON verification_change_log (stored_lemma);