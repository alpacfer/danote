DROP INDEX IF EXISTS idx_wordbank_verification_records_scope;

CREATE UNIQUE INDEX IF NOT EXISTS idx_wordbank_verification_records_scope
ON wordbank_verification_records(
    lexeme_id,
    COALESCE(meaning_id, 0),
    COALESCE(stored_surface_form, '')
);
