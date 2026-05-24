-- Allow many sense rows under one COR lemma_idx for a lexeme.
--
-- Migration 011 enforced UNIQUE (lexeme_id, cor_lemma_idx) under the
-- assumption that each COR lemma_idx maps to one wordbank meaning. That
-- holds for nouns/adjectives where COR splits homonyms by lemma_idx, but it
-- blocks the sense-discovery fan-out for verbs/AUX where one COR lemma_idx
-- (e.g. ``slå`` = 30449, ``holde`` = 30577) covers many semantically
-- distinct senses (hit / mow / ring / fold for slå; hold / stop / host for
-- holde). The save flow now writes one row per sense keyed on meaning_key,
-- and the constraint here would otherwise reject the second sense's INSERT
-- with a UNIQUE-violation 500.
--
-- Replace the cor_lemma_idx uniqueness with strict meaning_key uniqueness
-- across the whole (lexeme_id, meaning_key) pair (the old fallback index
-- only enforced it when cor_lemma_idx was NULL).

DROP INDEX IF EXISTS idx_lexeme_meanings_lexeme_cor_lemma_idx_unique;
DROP INDEX IF EXISTS idx_lexeme_meanings_lexeme_meaning_key_fallback_unique;

CREATE UNIQUE INDEX IF NOT EXISTS idx_lexeme_meanings_lexeme_meaning_key_unique
  ON lexeme_meanings(lexeme_id, meaning_key);
