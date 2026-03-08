CREATE TABLE IF NOT EXISTS surface_form_cor_variants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  surface_form_id INTEGER NOT NULL,
  cor_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  FOREIGN KEY (surface_form_id) REFERENCES surface_forms(id) ON DELETE CASCADE,
  UNIQUE (surface_form_id, cor_id)
);

CREATE INDEX IF NOT EXISTS idx_surface_form_cor_variants_surface_form_id
  ON surface_form_cor_variants(surface_form_id);

CREATE INDEX IF NOT EXISTS idx_surface_form_cor_variants_cor_id
  ON surface_form_cor_variants(cor_id);
