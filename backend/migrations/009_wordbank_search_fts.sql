CREATE INDEX IF NOT EXISTS idx_lexemes_lemma_nocase ON lexemes(lemma COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_lexemes_translation_nocase ON lexemes(english_translation COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_surface_forms_lexeme_form_nocase ON surface_forms(lexeme_id, form COLLATE NOCASE);
