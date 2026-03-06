from __future__ import annotations

from app.api.schemas.v1.wordbank import LemmaDetailsResponse
from app.db.migrations import get_connection
from app.services.token_classifier import normalize_token


class WordbankQueriesDetailsMixin:
    def get_lemma_details(self, lemma: str) -> LemmaDetailsResponse:
        normalized_lemma = normalize_token(lemma)
        if not normalized_lemma:
            raise ValueError("lemma is required")

        with get_connection(self._db_path) as conn:
            lexeme_row = conn.execute(
                """
                SELECT
                    id,
                    lemma,
                    english_translation AS english_translation,
                    pos_tag,
                    morphology
                FROM lexemes
                WHERE lemma = ?
                """,
                (normalized_lemma,),
            ).fetchone()

            if lexeme_row is None:
                raise LookupError(f"Lemma '{normalized_lemma}' was not found")

            form_rows = conn.execute(
                """
                SELECT
                    form,
                    english_translation AS english_translation,
                    pos_tag,
                    morphology,
                    CASE WHEN pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END AS has_pronunciation
                FROM surface_forms
                WHERE lexeme_id = ?
                ORDER BY form COLLATE NOCASE
                """,
                (lexeme_row["id"],),
            ).fetchall()

        lemma_pos_tag = lexeme_row["pos_tag"]
        lemma_morphology = lexeme_row["morphology"]
        if lemma_pos_tag is None and lemma_morphology is None:
            lemma_pos_tag, lemma_morphology = self._extract_pos_and_morphology(lexeme_row["lemma"])
            self._store_lexeme_metadata(lexeme_row["id"], lemma_pos_tag, lemma_morphology)

        surface_forms: list[LemmaDetailsResponse.SurfaceFormDetails] = []
        uncached_forms = [row["form"] for row in form_rows if row["pos_tag"] is None and row["morphology"] is None]
        extracted_forms = self._extract_pos_and_morphology_batch(uncached_forms)
        gloss_translation_cache: dict[str, str | None] = {}

        for row in form_rows:
            pos_tag = row["pos_tag"]
            morphology = row["morphology"]
            if pos_tag is None and morphology is None:
                pos_tag, morphology = extracted_forms.get(row["form"], (None, None))
                self._store_surface_form_metadata(lexeme_row["id"], row["form"], pos_tag, morphology)
            cor_local_entry = self._best_cor_local_entry_for_form(
                form=row["form"],
                lemma=lexeme_row["lemma"],
                preferred_pos_tag=pos_tag,
            )
            gram_raw = cor_local_entry.gram_raw if cor_local_entry is not None else None
            gloss = cor_local_entry.gloss if cor_local_entry is not None else None
            gloss_translation = self._lookup_translation_for_cor_gloss(gloss, gloss_translation_cache)
            surface_forms.append(
                LemmaDetailsResponse.SurfaceFormDetails(
                    form=row["form"],
                    english_translation=row["english_translation"],
                    pos_tag=pos_tag,
                    morphology=morphology,
                    lemma=lexeme_row["lemma"],
                    lemma_translation=lexeme_row["english_translation"],
                    gloss=gloss,
                    gloss_translation=gloss_translation,
                    gram_raw=gram_raw,
                    has_pronunciation=bool(row["has_pronunciation"]),
                )
            )

        return LemmaDetailsResponse(
            lemma=lexeme_row["lemma"],
            english_translation=lexeme_row["english_translation"],
            pos_tag=lemma_pos_tag,
            morphology=lemma_morphology,
            surface_forms=surface_forms,
        )


