ALTER TABLE lexemes
ADD COLUMN dictionary_status TEXT NOT NULL DEFAULT 'unknown';

ALTER TABLE lexeme_meanings
ADD COLUMN dictionary_status TEXT NOT NULL DEFAULT 'unknown';

UPDATE lexemes
SET dictionary_status = 'cor'
WHERE EXISTS (
    SELECT 1
    FROM lexeme_meanings lm
    WHERE lm.lexeme_id = lexemes.id
      AND lm.cor_lemma_idx IS NOT NULL
);

UPDATE lexeme_meanings
SET dictionary_status = 'cor'
WHERE cor_lemma_idx IS NOT NULL;
