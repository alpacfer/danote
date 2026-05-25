-- FTS5 index over saved-wordbank text so the sidebar's English-query search can
-- match every field a user might type: the Danish lemma, the primary English
-- translation, the descriptive english_gloss, alternative English translations,
-- the Danish gloss, and inflection surfaces. Powered by the porter+unicode61
-- tokenizer so "learns" matches "learn" and accented Danish forms collapse to
-- ASCII for English-side queries.
--
-- A "search unit" is either (a) a lexeme_meanings row, or (b) a lexeme with no
-- meanings (verb-style). meaning_id is NULL for the verb-style row.

CREATE VIRTUAL TABLE IF NOT EXISTS wordbank_fts USING fts5(
  lemma,
  gloss,
  english_translation,
  english_gloss,
  alt_translations,
  surface_forms,
  meaning_id UNINDEXED,
  lexeme_id UNINDEXED,
  owner_user_id UNINDEXED,
  pos_tag UNINDEXED,
  tokenize = "porter unicode61 remove_diacritics 1"
);

-- Initial backfill: meaning rows
INSERT INTO wordbank_fts(
  lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
  meaning_id, lexeme_id, owner_user_id, pos_tag
)
SELECT
  l.lemma,
  COALESCE(lm.gloss, ''),
  COALESCE(lm.english_translation, l.english_translation, ''),
  COALESCE(lm.english_gloss, ''),
  COALESCE((
    SELECT GROUP_CONCAT(at.english_translation, ' ')
    FROM wordbank_additional_translations at
    WHERE at.lexeme_id = l.id
      AND (at.meaning_id = lm.id OR at.meaning_id IS NULL)
  ), ''),
  COALESCE((
    SELECT GROUP_CONCAT(sf.form, ' ')
    FROM surface_forms sf
    WHERE sf.meaning_id = lm.id
  ), ''),
  lm.id,
  l.id,
  l.owner_user_id,
  COALESCE(lm.pos_tag, l.pos_tag)
FROM lexemes l
JOIN lexeme_meanings lm ON lm.lexeme_id = l.id;

-- Initial backfill: lexeme-only (verb-style) rows
INSERT INTO wordbank_fts(
  lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
  meaning_id, lexeme_id, owner_user_id, pos_tag
)
SELECT
  l.lemma,
  '',
  COALESCE(l.english_translation, ''),
  '',
  COALESCE((
    SELECT GROUP_CONCAT(at.english_translation, ' ')
    FROM wordbank_additional_translations at
    WHERE at.lexeme_id = l.id AND at.meaning_id IS NULL
  ), ''),
  COALESCE((
    SELECT GROUP_CONCAT(sf.form, ' ')
    FROM surface_forms sf
    WHERE sf.lexeme_id = l.id AND sf.meaning_id IS NULL
  ), ''),
  NULL,
  l.id,
  l.owner_user_id,
  l.pos_tag
FROM lexemes l
WHERE NOT EXISTS (SELECT 1 FROM lexeme_meanings lm WHERE lm.lexeme_id = l.id);

-- Trigger helpers: each "refresh lexeme" block deletes the lexeme's FTS rows
-- then re-inserts one row per meaning (or the lexeme-only fallback row when
-- no meanings exist). Triggers fire AFTER mutations on lexemes,
-- lexeme_meanings, surface_forms, and wordbank_additional_translations.

-- ─── lexemes ──────────────────────────────────────────────────────────────
CREATE TRIGGER IF NOT EXISTS wordbank_fts_lexemes_ai
AFTER INSERT ON lexemes
BEGIN
  DELETE FROM wordbank_fts WHERE lexeme_id = NEW.id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma,
    COALESCE(lm.gloss, ''),
    COALESCE(lm.english_translation, l.english_translation, ''),
    COALESCE(lm.english_gloss, ''),
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id
                AND (at.meaning_id = lm.id OR at.meaning_id IS NULL)), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf WHERE sf.meaning_id = lm.id), ''),
    lm.id, l.id, l.owner_user_id, COALESCE(lm.pos_tag, l.pos_tag)
  FROM lexemes l JOIN lexeme_meanings lm ON lm.lexeme_id = l.id
  WHERE l.id = NEW.id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma, '', COALESCE(l.english_translation, ''), '',
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id AND at.meaning_id IS NULL), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf
              WHERE sf.lexeme_id = l.id AND sf.meaning_id IS NULL), ''),
    NULL, l.id, l.owner_user_id, l.pos_tag
  FROM lexemes l
  WHERE l.id = NEW.id
    AND NOT EXISTS (SELECT 1 FROM lexeme_meanings lm WHERE lm.lexeme_id = l.id);
END;

CREATE TRIGGER IF NOT EXISTS wordbank_fts_lexemes_au
AFTER UPDATE ON lexemes
BEGIN
  DELETE FROM wordbank_fts WHERE lexeme_id = NEW.id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma,
    COALESCE(lm.gloss, ''),
    COALESCE(lm.english_translation, l.english_translation, ''),
    COALESCE(lm.english_gloss, ''),
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id
                AND (at.meaning_id = lm.id OR at.meaning_id IS NULL)), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf WHERE sf.meaning_id = lm.id), ''),
    lm.id, l.id, l.owner_user_id, COALESCE(lm.pos_tag, l.pos_tag)
  FROM lexemes l JOIN lexeme_meanings lm ON lm.lexeme_id = l.id
  WHERE l.id = NEW.id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma, '', COALESCE(l.english_translation, ''), '',
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id AND at.meaning_id IS NULL), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf
              WHERE sf.lexeme_id = l.id AND sf.meaning_id IS NULL), ''),
    NULL, l.id, l.owner_user_id, l.pos_tag
  FROM lexemes l
  WHERE l.id = NEW.id
    AND NOT EXISTS (SELECT 1 FROM lexeme_meanings lm WHERE lm.lexeme_id = l.id);
END;

CREATE TRIGGER IF NOT EXISTS wordbank_fts_lexemes_ad
AFTER DELETE ON lexemes
BEGIN
  DELETE FROM wordbank_fts WHERE lexeme_id = OLD.id;
END;

-- ─── lexeme_meanings ──────────────────────────────────────────────────────
CREATE TRIGGER IF NOT EXISTS wordbank_fts_meanings_ai
AFTER INSERT ON lexeme_meanings
BEGIN
  DELETE FROM wordbank_fts WHERE lexeme_id = NEW.lexeme_id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma,
    COALESCE(lm.gloss, ''),
    COALESCE(lm.english_translation, l.english_translation, ''),
    COALESCE(lm.english_gloss, ''),
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id
                AND (at.meaning_id = lm.id OR at.meaning_id IS NULL)), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf WHERE sf.meaning_id = lm.id), ''),
    lm.id, l.id, l.owner_user_id, COALESCE(lm.pos_tag, l.pos_tag)
  FROM lexemes l JOIN lexeme_meanings lm ON lm.lexeme_id = l.id
  WHERE l.id = NEW.lexeme_id;
END;

CREATE TRIGGER IF NOT EXISTS wordbank_fts_meanings_au
AFTER UPDATE ON lexeme_meanings
BEGIN
  DELETE FROM wordbank_fts WHERE lexeme_id = NEW.lexeme_id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma,
    COALESCE(lm.gloss, ''),
    COALESCE(lm.english_translation, l.english_translation, ''),
    COALESCE(lm.english_gloss, ''),
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id
                AND (at.meaning_id = lm.id OR at.meaning_id IS NULL)), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf WHERE sf.meaning_id = lm.id), ''),
    lm.id, l.id, l.owner_user_id, COALESCE(lm.pos_tag, l.pos_tag)
  FROM lexemes l JOIN lexeme_meanings lm ON lm.lexeme_id = l.id
  WHERE l.id = NEW.lexeme_id;
END;

CREATE TRIGGER IF NOT EXISTS wordbank_fts_meanings_ad
AFTER DELETE ON lexeme_meanings
BEGIN
  DELETE FROM wordbank_fts WHERE lexeme_id = OLD.lexeme_id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma,
    COALESCE(lm.gloss, ''),
    COALESCE(lm.english_translation, l.english_translation, ''),
    COALESCE(lm.english_gloss, ''),
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id
                AND (at.meaning_id = lm.id OR at.meaning_id IS NULL)), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf WHERE sf.meaning_id = lm.id), ''),
    lm.id, l.id, l.owner_user_id, COALESCE(lm.pos_tag, l.pos_tag)
  FROM lexemes l JOIN lexeme_meanings lm ON lm.lexeme_id = l.id
  WHERE l.id = OLD.lexeme_id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma, '', COALESCE(l.english_translation, ''), '',
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id AND at.meaning_id IS NULL), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf
              WHERE sf.lexeme_id = l.id AND sf.meaning_id IS NULL), ''),
    NULL, l.id, l.owner_user_id, l.pos_tag
  FROM lexemes l
  WHERE l.id = OLD.lexeme_id
    AND NOT EXISTS (SELECT 1 FROM lexeme_meanings lm WHERE lm.lexeme_id = l.id);
END;

-- ─── surface_forms ────────────────────────────────────────────────────────
CREATE TRIGGER IF NOT EXISTS wordbank_fts_surface_ai
AFTER INSERT ON surface_forms
BEGIN
  DELETE FROM wordbank_fts WHERE lexeme_id = NEW.lexeme_id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma,
    COALESCE(lm.gloss, ''),
    COALESCE(lm.english_translation, l.english_translation, ''),
    COALESCE(lm.english_gloss, ''),
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id
                AND (at.meaning_id = lm.id OR at.meaning_id IS NULL)), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf WHERE sf.meaning_id = lm.id), ''),
    lm.id, l.id, l.owner_user_id, COALESCE(lm.pos_tag, l.pos_tag)
  FROM lexemes l JOIN lexeme_meanings lm ON lm.lexeme_id = l.id
  WHERE l.id = NEW.lexeme_id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma, '', COALESCE(l.english_translation, ''), '',
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id AND at.meaning_id IS NULL), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf
              WHERE sf.lexeme_id = l.id AND sf.meaning_id IS NULL), ''),
    NULL, l.id, l.owner_user_id, l.pos_tag
  FROM lexemes l
  WHERE l.id = NEW.lexeme_id
    AND NOT EXISTS (SELECT 1 FROM lexeme_meanings lm WHERE lm.lexeme_id = l.id);
END;

CREATE TRIGGER IF NOT EXISTS wordbank_fts_surface_au
AFTER UPDATE ON surface_forms
BEGIN
  DELETE FROM wordbank_fts WHERE lexeme_id = NEW.lexeme_id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma,
    COALESCE(lm.gloss, ''),
    COALESCE(lm.english_translation, l.english_translation, ''),
    COALESCE(lm.english_gloss, ''),
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id
                AND (at.meaning_id = lm.id OR at.meaning_id IS NULL)), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf WHERE sf.meaning_id = lm.id), ''),
    lm.id, l.id, l.owner_user_id, COALESCE(lm.pos_tag, l.pos_tag)
  FROM lexemes l JOIN lexeme_meanings lm ON lm.lexeme_id = l.id
  WHERE l.id = NEW.lexeme_id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma, '', COALESCE(l.english_translation, ''), '',
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id AND at.meaning_id IS NULL), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf
              WHERE sf.lexeme_id = l.id AND sf.meaning_id IS NULL), ''),
    NULL, l.id, l.owner_user_id, l.pos_tag
  FROM lexemes l
  WHERE l.id = NEW.lexeme_id
    AND NOT EXISTS (SELECT 1 FROM lexeme_meanings lm WHERE lm.lexeme_id = l.id);
END;

CREATE TRIGGER IF NOT EXISTS wordbank_fts_surface_ad
AFTER DELETE ON surface_forms
BEGIN
  DELETE FROM wordbank_fts WHERE lexeme_id = OLD.lexeme_id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma,
    COALESCE(lm.gloss, ''),
    COALESCE(lm.english_translation, l.english_translation, ''),
    COALESCE(lm.english_gloss, ''),
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id
                AND (at.meaning_id = lm.id OR at.meaning_id IS NULL)), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf WHERE sf.meaning_id = lm.id), ''),
    lm.id, l.id, l.owner_user_id, COALESCE(lm.pos_tag, l.pos_tag)
  FROM lexemes l JOIN lexeme_meanings lm ON lm.lexeme_id = l.id
  WHERE l.id = OLD.lexeme_id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma, '', COALESCE(l.english_translation, ''), '',
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id AND at.meaning_id IS NULL), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf
              WHERE sf.lexeme_id = l.id AND sf.meaning_id IS NULL), ''),
    NULL, l.id, l.owner_user_id, l.pos_tag
  FROM lexemes l
  WHERE l.id = OLD.lexeme_id
    AND NOT EXISTS (SELECT 1 FROM lexeme_meanings lm WHERE lm.lexeme_id = l.id);
END;

-- ─── wordbank_additional_translations ─────────────────────────────────────
CREATE TRIGGER IF NOT EXISTS wordbank_fts_alt_ai
AFTER INSERT ON wordbank_additional_translations
BEGIN
  DELETE FROM wordbank_fts WHERE lexeme_id = NEW.lexeme_id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma,
    COALESCE(lm.gloss, ''),
    COALESCE(lm.english_translation, l.english_translation, ''),
    COALESCE(lm.english_gloss, ''),
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id
                AND (at.meaning_id = lm.id OR at.meaning_id IS NULL)), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf WHERE sf.meaning_id = lm.id), ''),
    lm.id, l.id, l.owner_user_id, COALESCE(lm.pos_tag, l.pos_tag)
  FROM lexemes l JOIN lexeme_meanings lm ON lm.lexeme_id = l.id
  WHERE l.id = NEW.lexeme_id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma, '', COALESCE(l.english_translation, ''), '',
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id AND at.meaning_id IS NULL), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf
              WHERE sf.lexeme_id = l.id AND sf.meaning_id IS NULL), ''),
    NULL, l.id, l.owner_user_id, l.pos_tag
  FROM lexemes l
  WHERE l.id = NEW.lexeme_id
    AND NOT EXISTS (SELECT 1 FROM lexeme_meanings lm WHERE lm.lexeme_id = l.id);
END;

CREATE TRIGGER IF NOT EXISTS wordbank_fts_alt_au
AFTER UPDATE ON wordbank_additional_translations
BEGIN
  DELETE FROM wordbank_fts WHERE lexeme_id = NEW.lexeme_id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma,
    COALESCE(lm.gloss, ''),
    COALESCE(lm.english_translation, l.english_translation, ''),
    COALESCE(lm.english_gloss, ''),
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id
                AND (at.meaning_id = lm.id OR at.meaning_id IS NULL)), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf WHERE sf.meaning_id = lm.id), ''),
    lm.id, l.id, l.owner_user_id, COALESCE(lm.pos_tag, l.pos_tag)
  FROM lexemes l JOIN lexeme_meanings lm ON lm.lexeme_id = l.id
  WHERE l.id = NEW.lexeme_id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma, '', COALESCE(l.english_translation, ''), '',
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id AND at.meaning_id IS NULL), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf
              WHERE sf.lexeme_id = l.id AND sf.meaning_id IS NULL), ''),
    NULL, l.id, l.owner_user_id, l.pos_tag
  FROM lexemes l
  WHERE l.id = NEW.lexeme_id
    AND NOT EXISTS (SELECT 1 FROM lexeme_meanings lm WHERE lm.lexeme_id = l.id);
END;

CREATE TRIGGER IF NOT EXISTS wordbank_fts_alt_ad
AFTER DELETE ON wordbank_additional_translations
BEGIN
  DELETE FROM wordbank_fts WHERE lexeme_id = OLD.lexeme_id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma,
    COALESCE(lm.gloss, ''),
    COALESCE(lm.english_translation, l.english_translation, ''),
    COALESCE(lm.english_gloss, ''),
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id
                AND (at.meaning_id = lm.id OR at.meaning_id IS NULL)), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf WHERE sf.meaning_id = lm.id), ''),
    lm.id, l.id, l.owner_user_id, COALESCE(lm.pos_tag, l.pos_tag)
  FROM lexemes l JOIN lexeme_meanings lm ON lm.lexeme_id = l.id
  WHERE l.id = OLD.lexeme_id;
  INSERT INTO wordbank_fts(
    lemma, gloss, english_translation, english_gloss, alt_translations, surface_forms,
    meaning_id, lexeme_id, owner_user_id, pos_tag
  )
  SELECT
    l.lemma, '', COALESCE(l.english_translation, ''), '',
    COALESCE((SELECT GROUP_CONCAT(at.english_translation, ' ')
              FROM wordbank_additional_translations at
              WHERE at.lexeme_id = l.id AND at.meaning_id IS NULL), ''),
    COALESCE((SELECT GROUP_CONCAT(sf.form, ' ')
              FROM surface_forms sf
              WHERE sf.lexeme_id = l.id AND sf.meaning_id IS NULL), ''),
    NULL, l.id, l.owner_user_id, l.pos_tag
  FROM lexemes l
  WHERE l.id = OLD.lexeme_id
    AND NOT EXISTS (SELECT 1 FROM lexeme_meanings lm WHERE lm.lexeme_id = l.id);
END;
