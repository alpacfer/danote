CREATE TABLE IF NOT EXISTS wordbank_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    normalized_label TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    updated_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_wordbank_categories_normalized_label
ON wordbank_categories(normalized_label);

CREATE TABLE IF NOT EXISTS wordbank_category_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lexeme_id INTEGER NOT NULL REFERENCES lexemes(id) ON DELETE CASCADE,
    meaning_id INTEGER REFERENCES lexeme_meanings(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES wordbank_categories(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    updated_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_wordbank_category_assignments_scope
ON wordbank_category_assignments(
    lexeme_id,
    COALESCE(meaning_id, 0),
    category_id
);

CREATE INDEX IF NOT EXISTS idx_wordbank_category_assignments_lookup
ON wordbank_category_assignments(lexeme_id, meaning_id);

INSERT OR IGNORE INTO wordbank_categories (label, normalized_label) VALUES
    ('Animals', 'animals'),
    ('Plants', 'plants'),
    ('Food', 'food'),
    ('Drinks', 'drinks'),
    ('Family', 'family'),
    ('People', 'people'),
    ('Body', 'body'),
    ('Clothing', 'clothing'),
    ('Home', 'home'),
    ('Household Objects', 'household objects'),
    ('Nature', 'nature'),
    ('Weather', 'weather'),
    ('Places', 'places'),
    ('Transport', 'transport'),
    ('Work', 'work'),
    ('School', 'school'),
    ('Health', 'health'),
    ('Time', 'time'),
    ('Actions', 'actions'),
    ('Emotions', 'emotions');
