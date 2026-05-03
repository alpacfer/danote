CREATE TABLE IF NOT EXISTS sentence_bank_tokens_next (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sentence_id INTEGER NOT NULL REFERENCES sentence_bank(id) ON DELETE CASCADE,
  token_index INTEGER NOT NULL,
  surface_form TEXT NOT NULL,
  normalized_surface TEXT NOT NULL COLLATE NOCASE,
  stored_lemma TEXT COLLATE NOCASE,
  lexeme_id INTEGER REFERENCES lexemes(id) ON DELETE CASCADE,
  meaning_id INTEGER REFERENCES lexeme_meanings(id) ON DELETE SET NULL,
  cor_id TEXT,
  pos_tag TEXT,
  morphology TEXT,
  gloss TEXT,
  english_translation TEXT,
  gloss_translation TEXT,
  save_status TEXT NOT NULL DEFAULT 'saved' CHECK (save_status IN ('saved', 'unsaved')),
  created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  UNIQUE(sentence_id, token_index)
);

INSERT INTO sentence_bank_tokens_next (
  id,
  sentence_id,
  token_index,
  surface_form,
  normalized_surface,
  stored_lemma,
  lexeme_id,
  meaning_id,
  cor_id,
  pos_tag,
  morphology,
  gloss,
  english_translation,
  gloss_translation,
  save_status,
  created_at
)
SELECT
  id,
  sentence_id,
  token_index,
  surface_form,
  normalized_surface,
  stored_lemma,
  lexeme_id,
  meaning_id,
  cor_id,
  pos_tag,
  morphology,
  gloss,
  english_translation,
  gloss_translation,
  'saved',
  created_at
FROM sentence_bank_tokens;

DROP TABLE sentence_bank_tokens;
ALTER TABLE sentence_bank_tokens_next RENAME TO sentence_bank_tokens;

CREATE INDEX IF NOT EXISTS idx_sentence_bank_tokens_sentence_id
ON sentence_bank_tokens(sentence_id, token_index, id);

CREATE INDEX IF NOT EXISTS idx_sentence_bank_tokens_stored_lemma
ON sentence_bank_tokens(stored_lemma, sentence_id, token_index)
WHERE stored_lemma IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_sentence_bank_tokens_lexeme_id
ON sentence_bank_tokens(lexeme_id, sentence_id, token_index)
WHERE lexeme_id IS NOT NULL;
