CREATE TABLE IF NOT EXISTS sentence_bank_tokens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sentence_id INTEGER NOT NULL REFERENCES sentence_bank(id) ON DELETE CASCADE,
  token_index INTEGER NOT NULL,
  surface_form TEXT NOT NULL,
  normalized_surface TEXT NOT NULL COLLATE NOCASE,
  stored_lemma TEXT NOT NULL COLLATE NOCASE,
  lexeme_id INTEGER NOT NULL REFERENCES lexemes(id) ON DELETE CASCADE,
  meaning_id INTEGER REFERENCES lexeme_meanings(id) ON DELETE SET NULL,
  cor_id TEXT,
  pos_tag TEXT,
  morphology TEXT,
  gloss TEXT,
  english_translation TEXT,
  gloss_translation TEXT,
  created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  UNIQUE(sentence_id, token_index)
);

CREATE INDEX IF NOT EXISTS idx_sentence_bank_tokens_sentence_id
ON sentence_bank_tokens(sentence_id, token_index, id);

CREATE INDEX IF NOT EXISTS idx_sentence_bank_tokens_stored_lemma
ON sentence_bank_tokens(stored_lemma, sentence_id, token_index);

CREATE INDEX IF NOT EXISTS idx_sentence_bank_tokens_lexeme_id
ON sentence_bank_tokens(lexeme_id, sentence_id, token_index);
