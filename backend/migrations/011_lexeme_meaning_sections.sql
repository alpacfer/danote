CREATE TABLE IF NOT EXISTS lexeme_meanings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lexeme_id INTEGER NOT NULL,
  meaning_key TEXT NOT NULL COLLATE NOCASE,
  cor_lemma_idx INTEGER,
  gloss TEXT,
  english_translation TEXT,
  pos_tag TEXT,
  morphology TEXT,
  created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  updated_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  FOREIGN KEY (lexeme_id) REFERENCES lexemes(id) ON DELETE CASCADE
);

ALTER TABLE surface_forms ADD COLUMN meaning_id INTEGER REFERENCES lexeme_meanings(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_lexeme_meanings_lexeme_id ON lexeme_meanings(lexeme_id);
CREATE INDEX IF NOT EXISTS idx_lexeme_meanings_cor_lemma_idx ON lexeme_meanings(cor_lemma_idx);
CREATE INDEX IF NOT EXISTS idx_surface_forms_meaning_id ON surface_forms(meaning_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_lexeme_meanings_lexeme_cor_lemma_idx_unique
  ON lexeme_meanings(lexeme_id, cor_lemma_idx)
  WHERE cor_lemma_idx IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_lexeme_meanings_lexeme_meaning_key_fallback_unique
  ON lexeme_meanings(lexeme_id, meaning_key)
  WHERE cor_lemma_idx IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_surface_forms_meaning_form_unique
  ON surface_forms(meaning_id, form)
  WHERE meaning_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_surface_forms_lexeme_form_root_unique
  ON surface_forms(lexeme_id, form)
  WHERE meaning_id IS NULL;
