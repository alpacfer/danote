CREATE TABLE IF NOT EXISTS surface_form_cor_variants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lexeme_id INTEGER NOT NULL,
  form TEXT NOT NULL COLLATE NOCASE,
  cor_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  FOREIGN KEY (lexeme_id) REFERENCES lexemes(id) ON DELETE CASCADE,
  UNIQUE (lexeme_id, form, cor_id)
);

CREATE INDEX IF NOT EXISTS idx_surface_form_cor_variants_lexeme_form
  ON surface_form_cor_variants(lexeme_id, form);

CREATE INDEX IF NOT EXISTS idx_surface_form_cor_variants_cor_id
  ON surface_form_cor_variants(cor_id);
