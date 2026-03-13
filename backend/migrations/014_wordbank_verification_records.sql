CREATE TABLE IF NOT EXISTS wordbank_verification_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lexeme_id INTEGER NOT NULL REFERENCES lexemes(id) ON DELETE CASCADE,
    meaning_id INTEGER REFERENCES lexeme_meanings(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    provider TEXT,
    reviewer_role TEXT,
    stored_surface_form TEXT,
    message TEXT NOT NULL,
    problem TEXT,
    change_to_implement TEXT,
    suggested_actions_json TEXT NOT NULL DEFAULT '[]',
    requested_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    updated_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_wordbank_verification_records_scope
ON wordbank_verification_records(lexeme_id, COALESCE(meaning_id, 0));

CREATE INDEX IF NOT EXISTS idx_wordbank_verification_records_lookup
ON wordbank_verification_records(lexeme_id, meaning_id);
