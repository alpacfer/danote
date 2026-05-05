CREATE TABLE IF NOT EXISTS numbers_reference_audio (
    id INTEGER PRIMARY KEY,
    term TEXT UNIQUE NOT NULL COLLATE NOCASE,
    audio BLOB,
    mime_type TEXT,
    provider TEXT,
    model TEXT,
    generated_at TEXT
);
