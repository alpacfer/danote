-- Allow the same discovered meaning label to exist under distinct COR/POS
-- identities for homographs such as "nok" (ADV/ADJ/NOUN "probably").
DROP INDEX IF EXISTS idx_lexeme_meanings_lexeme_meaning_key_unique;

CREATE UNIQUE INDEX IF NOT EXISTS idx_lexeme_meanings_lexeme_meaning_key_cor_unique
  ON lexeme_meanings(lexeme_id, meaning_key, cor_lemma_idx)
  WHERE cor_lemma_idx IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_lexeme_meanings_lexeme_meaning_key_pos_unique
  ON lexeme_meanings(lexeme_id, meaning_key, pos_tag)
  WHERE cor_lemma_idx IS NULL AND pos_tag IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_lexeme_meanings_lexeme_meaning_key_fallback_unique
  ON lexeme_meanings(lexeme_id, meaning_key)
  WHERE cor_lemma_idx IS NULL AND pos_tag IS NULL;
