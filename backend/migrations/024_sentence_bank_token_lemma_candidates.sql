ALTER TABLE sentence_bank_tokens
ADD COLUMN lemma_candidate TEXT COLLATE NOCASE;

UPDATE sentence_bank_tokens
SET lemma_candidate = stored_lemma
WHERE lemma_candidate IS NULL
  AND stored_lemma IS NOT NULL;
