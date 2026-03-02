ALTER TABLE surface_forms ADD COLUMN pronunciation_audio BLOB;
ALTER TABLE surface_forms ADD COLUMN pronunciation_mime_type TEXT;
ALTER TABLE surface_forms ADD COLUMN pronunciation_provider TEXT;
ALTER TABLE surface_forms ADD COLUMN pronunciation_model TEXT;
ALTER TABLE surface_forms ADD COLUMN pronunciation_generated_at TEXT;
