CREATE TABLE IF NOT EXISTS wordbank_additional_translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lexeme_id INTEGER NOT NULL,
    meaning_id INTEGER NULL,
    english_translation TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'related_words',
    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (lexeme_id) REFERENCES lexemes(id) ON DELETE CASCADE,
    FOREIGN KEY (meaning_id) REFERENCES lexeme_meanings(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_wordbank_additional_translations_scope
    ON wordbank_additional_translations (lexeme_id, meaning_id, id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_wordbank_additional_translations_scope_translation_unique
    ON wordbank_additional_translations (
        lexeme_id,
        COALESCE(meaning_id, -1),
        english_translation
    );
