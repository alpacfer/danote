CREATE TABLE IF NOT EXISTS wordbank_related_words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_lexeme_id INTEGER NOT NULL,
    relation_type TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    related_lemma TEXT NOT NULL COLLATE NOCASE,
    english_translation TEXT,
    pos_tag TEXT,
    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    updated_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (owner_lexeme_id) REFERENCES lexemes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_wordbank_related_words_owner_lexeme_id
ON wordbank_related_words(owner_lexeme_id, sort_order, id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_wordbank_related_words_owner_relation_order_unique
ON wordbank_related_words(owner_lexeme_id, relation_type, sort_order);
