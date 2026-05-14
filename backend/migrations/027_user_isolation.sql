CREATE TABLE IF NOT EXISTS app_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    auth_provider TEXT NOT NULL,
    auth_subject TEXT NOT NULL,
    email TEXT,
    display_name TEXT,
    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    last_seen_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    UNIQUE(auth_provider, auth_subject)
);

INSERT OR IGNORE INTO app_users (id, auth_provider, auth_subject, email, display_name)
VALUES (1, 'local', 'local-dev', 'local@danote.local', 'Local Danote User');

PRAGMA foreign_keys=OFF;

CREATE TABLE lexemes_new (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_user_id INTEGER NOT NULL DEFAULT 1 REFERENCES app_users(id),
  lemma TEXT NOT NULL COLLATE NOCASE,
  source TEXT NOT NULL DEFAULT 'manual',
  created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  updated_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  english_translation TEXT,
  translation_provider TEXT,
  pos_tag TEXT,
  morphology TEXT,
  dictionary_status TEXT NOT NULL DEFAULT 'unknown',
  UNIQUE(owner_user_id, lemma)
);

INSERT INTO lexemes_new (
  id, owner_user_id, lemma, source, created_at, updated_at, english_translation,
  translation_provider, pos_tag, morphology, dictionary_status
)
SELECT
  id, 1, lemma, source, created_at, updated_at, english_translation,
  translation_provider, pos_tag, morphology, COALESCE(dictionary_status, 'unknown')
FROM lexemes;

DROP TABLE lexemes;
ALTER TABLE lexemes_new RENAME TO lexemes;

CREATE TABLE phrase_translations_new (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_user_id INTEGER NOT NULL DEFAULT 1 REFERENCES app_users(id),
  source_phrase TEXT NOT NULL COLLATE NOCASE,
  english_translation TEXT,
  translation_provider TEXT,
  created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  updated_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  UNIQUE(owner_user_id, source_phrase)
);

INSERT INTO phrase_translations_new (
  id, owner_user_id, source_phrase, english_translation, translation_provider, created_at, updated_at
)
SELECT id, 1, source_phrase, english_translation, translation_provider, created_at, updated_at
FROM phrase_translations;

DROP TABLE phrase_translations;
ALTER TABLE phrase_translations_new RENAME TO phrase_translations;

CREATE TABLE sentence_bank_new (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_user_id INTEGER NOT NULL DEFAULT 1 REFERENCES app_users(id),
  source_sentence TEXT NOT NULL,
  normalized_sentence TEXT NOT NULL COLLATE NOCASE,
  english_translation TEXT,
  translation_provider TEXT,
  created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  updated_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  pronunciation_audio BLOB,
  pronunciation_mime_type TEXT,
  pronunciation_provider TEXT,
  pronunciation_model TEXT,
  pronunciation_generated_at TEXT,
  UNIQUE(owner_user_id, normalized_sentence)
);

INSERT INTO sentence_bank_new (
  id, owner_user_id, source_sentence, normalized_sentence, english_translation,
  translation_provider, created_at, updated_at, pronunciation_audio,
  pronunciation_mime_type, pronunciation_provider, pronunciation_model, pronunciation_generated_at
)
SELECT
  id, 1, source_sentence, normalized_sentence, english_translation,
  translation_provider, created_at, updated_at, pronunciation_audio,
  pronunciation_mime_type, pronunciation_provider, pronunciation_model, pronunciation_generated_at
FROM sentence_bank;

DROP TABLE sentence_bank;
ALTER TABLE sentence_bank_new RENAME TO sentence_bank;

CREATE TABLE ignored_tokens_new (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_user_id INTEGER NOT NULL DEFAULT 1 REFERENCES app_users(id),
  token TEXT NOT NULL COLLATE NOCASE,
  scope TEXT NOT NULL DEFAULT 'global',
  expires_at TEXT,
  created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  UNIQUE(owner_user_id, token, scope)
);

INSERT INTO ignored_tokens_new (id, owner_user_id, token, scope, expires_at, created_at)
SELECT id, 1, token, scope, expires_at, created_at
FROM ignored_tokens;

DROP TABLE ignored_tokens;
ALTER TABLE ignored_tokens_new RENAME TO ignored_tokens;

CREATE TABLE wordbank_background_jobs_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_user_id INTEGER NOT NULL DEFAULT 1 REFERENCES app_users(id),
    job_type TEXT NOT NULL,
    dedupe_key TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    available_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    last_error TEXT,
    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    updated_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    completed_at TEXT,
    rerun_requested INTEGER NOT NULL DEFAULT 0,
    UNIQUE(owner_user_id, dedupe_key)
);

INSERT INTO wordbank_background_jobs_new (
  id, owner_user_id, job_type, dedupe_key, payload_json, status, attempt_count,
  max_attempts, available_at, last_error, created_at, updated_at, completed_at, rerun_requested
)
SELECT
  id, 1, job_type, dedupe_key, payload_json, status, attempt_count,
  max_attempts, available_at, last_error, created_at, updated_at, completed_at, COALESCE(rerun_requested, 0)
FROM wordbank_background_jobs;

DROP TABLE wordbank_background_jobs;
ALTER TABLE wordbank_background_jobs_new RENAME TO wordbank_background_jobs;

ALTER TABLE token_events ADD COLUMN owner_user_id INTEGER NOT NULL DEFAULT 1 REFERENCES app_users(id);
ALTER TABLE typo_feedback ADD COLUMN owner_user_id INTEGER NOT NULL DEFAULT 1 REFERENCES app_users(id);
ALTER TABLE verification_change_log ADD COLUMN owner_user_id INTEGER NOT NULL DEFAULT 1 REFERENCES app_users(id);

PRAGMA foreign_keys=ON;

CREATE INDEX IF NOT EXISTS idx_lexemes_owner_lemma_lookup
ON lexemes(owner_user_id, lemma COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_lexemes_translation_nocase
ON lexemes(english_translation COLLATE NOCASE);

CREATE UNIQUE INDEX IF NOT EXISTS idx_lexeme_meanings_lexeme_cor_lemma_idx_unique
  ON lexeme_meanings(lexeme_id, cor_lemma_idx)
  WHERE cor_lemma_idx IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_lexeme_meanings_lexeme_meaning_key_fallback_unique
  ON lexeme_meanings(lexeme_id, meaning_key)
  WHERE cor_lemma_idx IS NULL;

CREATE INDEX IF NOT EXISTS idx_sentence_bank_owner_created_at
ON sentence_bank(owner_user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_phrase_translations_owner_source_phrase
ON phrase_translations(owner_user_id, source_phrase COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_ignored_tokens_owner_token
ON ignored_tokens(owner_user_id, token COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_wordbank_background_jobs_owner_poll
ON wordbank_background_jobs(owner_user_id, status, available_at, created_at);
CREATE INDEX IF NOT EXISTS idx_vcl_owner_lemma
ON verification_change_log(owner_user_id, stored_lemma COLLATE NOCASE);
