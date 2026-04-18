ALTER TABLE sentence_bank ADD COLUMN pronunciation_audio BLOB;
ALTER TABLE sentence_bank ADD COLUMN pronunciation_mime_type TEXT;
ALTER TABLE sentence_bank ADD COLUMN pronunciation_provider TEXT;
ALTER TABLE sentence_bank ADD COLUMN pronunciation_model TEXT;
ALTER TABLE sentence_bank ADD COLUMN pronunciation_generated_at TEXT;
