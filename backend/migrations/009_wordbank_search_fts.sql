CREATE INDEX IF NOT EXISTS idx_lexemes_lemma_nocase ON lexemes(lemma COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_lexemes_translation_nocase ON lexemes(english_translation COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_surface_forms_lexeme_form_nocase ON surface_forms(lexeme_id, form COLLATE NOCASE);

CREATE VIRTUAL TABLE IF NOT EXISTS wordbank_search_fts USING fts5(
  lexeme_id UNINDEXED,
  lemma,
  english_translation,
  surface_forms,
  tokenize = 'trigram'
);

DELETE FROM wordbank_search_fts;

INSERT INTO wordbank_search_fts (rowid, lexeme_id, lemma, english_translation, surface_forms)
SELECT
  l.id,
  l.id,
  l.lemma,
  COALESCE(l.english_translation, ''),
  COALESCE(
    (
      SELECT group_concat(form, ' ')
      FROM (
        SELECT sf.form
        FROM surface_forms sf
        WHERE sf.lexeme_id = l.id
        ORDER BY sf.form COLLATE NOCASE
      )
    ),
    ''
  )
FROM lexemes l;

CREATE TRIGGER IF NOT EXISTS trg_wordbank_search_fts_lexemes_ai
AFTER INSERT ON lexemes
BEGIN
  INSERT INTO wordbank_search_fts (rowid, lexeme_id, lemma, english_translation, surface_forms)
  VALUES (
    NEW.id,
    NEW.id,
    NEW.lemma,
    COALESCE(NEW.english_translation, ''),
    COALESCE(
      (
        SELECT group_concat(form, ' ')
        FROM (
          SELECT sf.form
          FROM surface_forms sf
          WHERE sf.lexeme_id = NEW.id
          ORDER BY sf.form COLLATE NOCASE
        )
      ),
      ''
    )
  );
END;

CREATE TRIGGER IF NOT EXISTS trg_wordbank_search_fts_lexemes_au
AFTER UPDATE OF lemma, english_translation ON lexemes
BEGIN
  DELETE FROM wordbank_search_fts WHERE rowid = OLD.id;
  INSERT INTO wordbank_search_fts (rowid, lexeme_id, lemma, english_translation, surface_forms)
  VALUES (
    NEW.id,
    NEW.id,
    NEW.lemma,
    COALESCE(NEW.english_translation, ''),
    COALESCE(
      (
        SELECT group_concat(form, ' ')
        FROM (
          SELECT sf.form
          FROM surface_forms sf
          WHERE sf.lexeme_id = NEW.id
          ORDER BY sf.form COLLATE NOCASE
        )
      ),
      ''
    )
  );
END;

CREATE TRIGGER IF NOT EXISTS trg_wordbank_search_fts_lexemes_ad
AFTER DELETE ON lexemes
BEGIN
  DELETE FROM wordbank_search_fts WHERE rowid = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_wordbank_search_fts_surface_forms_ai
AFTER INSERT ON surface_forms
BEGIN
  DELETE FROM wordbank_search_fts WHERE rowid = NEW.lexeme_id;
  INSERT INTO wordbank_search_fts (rowid, lexeme_id, lemma, english_translation, surface_forms)
  SELECT
    l.id,
    l.id,
    l.lemma,
    COALESCE(l.english_translation, ''),
    COALESCE(
      (
        SELECT group_concat(form, ' ')
        FROM (
          SELECT sf.form
          FROM surface_forms sf
          WHERE sf.lexeme_id = l.id
          ORDER BY sf.form COLLATE NOCASE
        )
      ),
      ''
    )
  FROM lexemes l
  WHERE l.id = NEW.lexeme_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_wordbank_search_fts_surface_forms_au
AFTER UPDATE OF form ON surface_forms
BEGIN
  DELETE FROM wordbank_search_fts WHERE rowid = NEW.lexeme_id;
  INSERT INTO wordbank_search_fts (rowid, lexeme_id, lemma, english_translation, surface_forms)
  SELECT
    l.id,
    l.id,
    l.lemma,
    COALESCE(l.english_translation, ''),
    COALESCE(
      (
        SELECT group_concat(form, ' ')
        FROM (
          SELECT sf.form
          FROM surface_forms sf
          WHERE sf.lexeme_id = l.id
          ORDER BY sf.form COLLATE NOCASE
        )
      ),
      ''
    )
  FROM lexemes l
  WHERE l.id = NEW.lexeme_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_wordbank_search_fts_surface_forms_ad
AFTER DELETE ON surface_forms
BEGIN
  DELETE FROM wordbank_search_fts WHERE rowid = OLD.lexeme_id;
  INSERT INTO wordbank_search_fts (rowid, lexeme_id, lemma, english_translation, surface_forms)
  SELECT
    l.id,
    l.id,
    l.lemma,
    COALESCE(l.english_translation, ''),
    COALESCE(
      (
        SELECT group_concat(form, ' ')
        FROM (
          SELECT sf.form
          FROM surface_forms sf
          WHERE sf.lexeme_id = l.id
          ORDER BY sf.form COLLATE NOCASE
        )
      ),
      ''
    )
  FROM lexemes l
  WHERE l.id = OLD.lexeme_id;
END;
