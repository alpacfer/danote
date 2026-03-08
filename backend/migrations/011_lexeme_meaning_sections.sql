CREATE TABLE IF NOT EXISTS lexeme_meanings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lexeme_id INTEGER NOT NULL,
  meaning_key TEXT NOT NULL COLLATE NOCASE,
  gloss TEXT,
  english_translation TEXT,
  pos_tag TEXT,
  morphology TEXT,
  created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  updated_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  FOREIGN KEY (lexeme_id) REFERENCES lexemes(id) ON DELETE CASCADE,
  UNIQUE (lexeme_id, meaning_key)
);

ALTER TABLE surface_forms ADD COLUMN meaning_id INTEGER REFERENCES lexeme_meanings(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_lexeme_meanings_lexeme_id ON lexeme_meanings(lexeme_id);
CREATE INDEX IF NOT EXISTS idx_surface_forms_meaning_id ON surface_forms(meaning_id);
