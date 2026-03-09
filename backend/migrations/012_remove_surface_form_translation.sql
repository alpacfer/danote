PRAGMA foreign_keys=OFF;

CREATE TABLE surface_forms_new (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lexeme_id INTEGER NOT NULL,
  form TEXT NOT NULL COLLATE NOCASE,
  source TEXT NOT NULL DEFAULT 'observed',
  created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  seen_count INTEGER NOT NULL DEFAULT 1,
  last_seen_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  pos_tag TEXT,
  morphology TEXT,
  pronunciation_audio BLOB,
  pronunciation_mime_type TEXT,
  pronunciation_provider TEXT,
  pronunciation_model TEXT,
  pronunciation_generated_at TEXT,
  meaning_id INTEGER REFERENCES lexeme_meanings(id) ON DELETE SET NULL,
  FOREIGN KEY (lexeme_id) REFERENCES lexemes(id) ON DELETE CASCADE
);

INSERT INTO surface_forms_new (
  id,
  lexeme_id,
  form,
  source,
  created_at,
  seen_count,
  last_seen_at,
  pos_tag,
  morphology,
  pronunciation_audio,
  pronunciation_mime_type,
  pronunciation_provider,
  pronunciation_model,
  pronunciation_generated_at,
  meaning_id
)
SELECT
  id,
  lexeme_id,
  form,
  source,
  created_at,
  COALESCE(seen_count, 1),
  COALESCE(last_seen_at, created_at, CURRENT_TIMESTAMP),
  pos_tag,
  morphology,
  pronunciation_audio,
  pronunciation_mime_type,
  pronunciation_provider,
  pronunciation_model,
  pronunciation_generated_at,
  meaning_id
FROM surface_forms;

DROP TABLE surface_forms;
ALTER TABLE surface_forms_new RENAME TO surface_forms;

CREATE INDEX IF NOT EXISTS idx_surface_forms_form ON surface_forms(form);
CREATE INDEX IF NOT EXISTS idx_surface_forms_lexeme_id ON surface_forms(lexeme_id);
CREATE INDEX IF NOT EXISTS idx_surface_forms_meaning_id ON surface_forms(meaning_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_surface_forms_meaning_form_unique
  ON surface_forms(meaning_id, form)
  WHERE meaning_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_surface_forms_lexeme_form_root_unique
  ON surface_forms(lexeme_id, form)
  WHERE meaning_id IS NULL;

PRAGMA foreign_keys=ON;
