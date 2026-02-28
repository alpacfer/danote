from __future__ import annotations

import os
from typing import Literal

from app.api.schemas.v1.wordbank import (
    AddWordResponse,
    GeneratePhraseTranslationResponse,
    GenerateTranslationResponse,
    LemmaDetailsResponse,
    LemmaListResponse,
    LemmaSummary,
    ResetDatabaseResponse,
)
from app.db.migrations import apply_migrations, get_connection
from app.nlp.adapter import NLPAdapter
from app.nlp.token_filter import is_wordlike_token
from app.services.token_classifier import normalize_token
from app.services.translation import TranslationService


class WordbankUseCase:
    def __init__(
        self,
        db_path,
        typo_engine=None,
        translation_service: TranslationService | None = None,
        nlp_adapter: NLPAdapter | None = None,
    ):
        self._db_path = db_path
        self._typo_engine = typo_engine
        self._translation_service = translation_service
        self._nlp_adapter = nlp_adapter

    def add_word(self, surface_token: str, lemma_candidate: str | None) -> AddWordResponse:
        normalized_surface = normalize_token(surface_token)
        normalized_lemma = normalize_token(lemma_candidate or "")
        stored_lemma = normalized_lemma or normalized_surface

        if not stored_lemma:
            raise ValueError("surface_token or lemma_candidate is required")

        inserted_lexeme = False
        inserted_surface_form = False
        lemma_translation = self._lookup_translation(stored_lemma)
        surface_translation = self._lookup_translation(normalized_surface) if normalized_surface else None

        with get_connection(self._db_path) as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO lexemes (lemma, source, english_translation, translation_provider)
                VALUES (?, ?, ?, ?)
                """,
                (
                    stored_lemma,
                    "manual",
                    lemma_translation,
                    "deepl" if lemma_translation else None,
                ),
            )
            inserted_lexeme = cursor.rowcount == 1

            lexeme_row = conn.execute(
                "SELECT id FROM lexemes WHERE lemma = ?",
                (stored_lemma,),
            ).fetchone()
            if lexeme_row is None:
                raise RuntimeError("Failed to create or load lexeme")

            if lemma_translation:
                conn.execute(
                    """
                    UPDATE lexemes
                    SET english_translation = ?, translation_provider = 'deepl'
                    WHERE id = ?
                    """,
                    (lemma_translation, lexeme_row["id"]),
                )

            if normalized_surface:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO surface_forms (
                        lexeme_id,
                        form,
                        source,
                        english_translation,
                        translation_provider
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        lexeme_row["id"],
                        normalized_surface,
                        "manual",
                        surface_translation,
                        "deepl" if surface_translation else None,
                    ),
                )
                inserted_surface_form = cursor.rowcount == 1
                conn.execute(
                    """
                    UPDATE surface_forms
                    SET seen_count = seen_count + 1,
                        last_seen_at = CURRENT_TIMESTAMP
                    WHERE lexeme_id = ? AND form = ?
                    """,
                    (lexeme_row["id"], normalized_surface),
                )
                if surface_translation:
                    conn.execute(
                        """
                        UPDATE surface_forms
                        SET english_translation = ?, translation_provider = 'deepl'
                        WHERE lexeme_id = ? AND form = ?
                        """,
                        (surface_translation, lexeme_row["id"], normalized_surface),
                    )

        inserted = inserted_lexeme or inserted_surface_form
        if self._typo_engine is not None and inserted:
            self._typo_engine.add_user_lexeme(stored_lemma)

        status: Literal["inserted", "exists"] = "inserted" if inserted else "exists"
        message = (
            f"Added '{stored_lemma}' to wordbank."
            if inserted
            else f"'{stored_lemma}' is already in the wordbank."
        )

        return AddWordResponse(
            status=status,
            stored_lemma=stored_lemma,
            stored_surface_form=normalized_surface or None,
            source="manual",
            message=message,
        )

    def generate_translation(self, surface_token: str, lemma_candidate: str | None) -> GenerateTranslationResponse:
        normalized_surface = normalize_token(surface_token)
        normalized_lemma = normalize_token(lemma_candidate or "")
        stored_lemma = normalized_lemma or normalized_surface

        if not normalized_surface:
            raise ValueError("surface_token or lemma_candidate is required")

        english_translation = self._lookup_translation(normalized_surface)
        if english_translation:
            with get_connection(self._db_path) as conn:
                conn.execute(
                    """
                    UPDATE surface_forms
                    SET english_translation = ?, translation_provider = 'deepl'
                    WHERE form = ?
                    """,
                    (english_translation, normalized_surface),
                )

        return GenerateTranslationResponse(
            status="generated" if english_translation else "unavailable",
            source_word=normalized_surface,
            lemma=stored_lemma,
            english_translation=english_translation,
        )

    def generate_phrase_translation(self, source_text: str) -> GeneratePhraseTranslationResponse:
        normalized_source_text = normalize_token(source_text)
        if not normalized_source_text:
            raise ValueError("source_text is required")

        with get_connection(self._db_path) as conn:
            existing = conn.execute(
                """
                SELECT english_translation
                FROM phrase_translations
                WHERE source_phrase = ?
                LIMIT 1
                """,
                (normalized_source_text,),
            ).fetchone()

            if existing is not None:
                cached_translation = existing["english_translation"]
                return GeneratePhraseTranslationResponse(
                    status="cached" if cached_translation else "unavailable",
                    source_text=normalized_source_text,
                    english_translation=cached_translation,
                )

            english_translation = self._lookup_translation(normalized_source_text)
            conn.execute(
                """
                INSERT INTO phrase_translations (
                    source_phrase,
                    english_translation,
                    translation_provider
                )
                VALUES (?, ?, ?)
                """,
                (
                    normalized_source_text,
                    english_translation,
                    "deepl" if english_translation else None,
                ),
            )

        return GeneratePhraseTranslationResponse(
            status="generated" if english_translation else "unavailable",
            source_text=normalized_source_text,
            english_translation=english_translation,
        )

    def list_lemmas(self) -> LemmaListResponse:
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                """
                SELECT
                    l.lemma,
                    CASE
                        WHEN l.translation_provider = 'deepl' THEN l.english_translation
                        ELSE NULL
                    END AS english_translation,
                    COUNT(sf.id) AS variation_count
                FROM lexemes l
                LEFT JOIN surface_forms sf ON sf.lexeme_id = l.id
                GROUP BY l.id, l.lemma
                ORDER BY l.lemma COLLATE NOCASE
                """
            ).fetchall()

        return LemmaListResponse(
            items=[
                LemmaSummary(
                    lemma=row["lemma"],
                    english_translation=row["english_translation"],
                    variation_count=int(row["variation_count"]),
                )
                for row in rows
            ]
        )

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
                    CASE
                        WHEN translation_provider = 'deepl' THEN english_translation
                        ELSE NULL
                    END AS english_translation
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
                    CASE
                        WHEN translation_provider = 'deepl' THEN english_translation
                        ELSE NULL
                    END AS english_translation
                FROM surface_forms
                WHERE lexeme_id = ?
                ORDER BY form COLLATE NOCASE
                """,
                (lexeme_row["id"],),
            ).fetchall()

        lemma_pos_tag, lemma_morphology = self._extract_pos_and_morphology(lexeme_row["lemma"])

        surface_forms: list[LemmaDetailsResponse.SurfaceFormDetails] = []
        for row in form_rows:
            pos_tag, morphology = self._extract_pos_and_morphology(row["form"])
            surface_forms.append(
                LemmaDetailsResponse.SurfaceFormDetails(
                    form=row["form"],
                    english_translation=row["english_translation"],
                    pos_tag=pos_tag,
                    morphology=morphology,
                )
            )

        return LemmaDetailsResponse(
            lemma=lexeme_row["lemma"],
            english_translation=lexeme_row["english_translation"],
            pos_tag=lemma_pos_tag,
            morphology=lemma_morphology,
            surface_forms=surface_forms,
        )


    def _extract_pos_and_morphology(self, value: str) -> tuple[str | None, str | None]:
        if self._nlp_adapter is None:
            return None, None

        for token in self._nlp_adapter.tokenize(value):
            surface = token.text
            if not surface.strip():
                continue
            if token.is_punctuation:
                continue
            if not is_wordlike_token(surface):
                continue
            return token.pos, token.morphology

        return None, None


    def _lookup_translation(self, source_word: str) -> str | None:
        if self._translation_service is None:
            return None

        try:
            return self._translation_service.translate_da_to_en(source_word)
        except Exception:
            return None

    def reset_database(self) -> ResetDatabaseResponse:
        if self._db_path.exists():
            os.remove(self._db_path)
        apply_migrations(self._db_path)
        if self._typo_engine is not None:
            self._typo_engine.invalidate_cache()

        return ResetDatabaseResponse(
            status="reset",
            message="Database reset complete.",
        )
