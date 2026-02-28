CREATE TABLE IF NOT EXISTS phrase_translations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_phrase TEXT NOT NULL COLLATE NOCASE,
  english_translation TEXT,
  translation_provider TEXT,
  created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  updated_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  UNIQUE(source_phrase)
);

CREATE INDEX IF NOT EXISTS idx_phrase_translations_source_phrase ON phrase_translations(source_phrase);
