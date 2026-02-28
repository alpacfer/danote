CREATE TABLE IF NOT EXISTS sentence_bank (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_sentence TEXT NOT NULL,
  normalized_sentence TEXT NOT NULL COLLATE NOCASE,
  english_translation TEXT,
  translation_provider TEXT,
  created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  updated_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  UNIQUE(normalized_sentence)
);

CREATE INDEX IF NOT EXISTS idx_sentence_bank_normalized_sentence ON sentence_bank(normalized_sentence);
CREATE INDEX IF NOT EXISTS idx_sentence_bank_created_at ON sentence_bank(created_at);
