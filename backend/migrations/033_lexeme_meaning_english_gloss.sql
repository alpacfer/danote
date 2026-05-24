-- Persist the English equivalent of a meaning's Danish gloss.
--
-- The sense-discovery fan-out (gemini_sense_discovery) generates both a
-- short Danish definition (``gloss``) and a short English definition
-- (``english_gloss``) for every discovered sense. We already stored the
-- Danish text on ``lexeme_meanings.gloss``; this column gives the English
-- equivalent a home so the wordbank header can render
-- ``playing card (a piece of stiff paper used in card games)`` instead of
-- ``playing card (stykke papir eller pap brugt til spil)``.
--
-- Backfilling existing rows is intentionally a no-op: legacy meanings either
-- have no gloss at all or carry a COR gloss whose translation is computed at
-- query time via ``lookup_translation_for_cor_gloss``. Saving a new sense
-- through the search dialog now populates this column directly.

ALTER TABLE lexeme_meanings ADD COLUMN english_gloss TEXT;
