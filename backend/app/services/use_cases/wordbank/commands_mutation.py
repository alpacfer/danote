from __future__ import annotations

import logging

from app.api.schemas.v1.wordbank import AddWordResponse
from app.db.migrations import get_connection
from app.nlp.token_filter import is_wordlike_token
from app.services.token_classifier import normalize_token

logger = logging.getLogger(__name__)


class WordbankCommandsMutationMixin:
    def add_word(
        self,
        surface_token: str,
        lemma_candidate: str | None,
        *,
        pos_tag: str | None = None,
        morphology: str | None = None,
    ) -> AddWordResponse:
        normalized_surface = normalize_token(surface_token)
        normalized_lemma = normalize_token(lemma_candidate or "")
        stored_lemma = normalized_lemma or normalized_surface

        if not stored_lemma:
            raise ValueError("surface_token or lemma_candidate is required")

        selected_pos_tag = self._normalize_optional_pos_tag(pos_tag)
        selected_morphology = self._normalize_optional_morphology(morphology)
        inserted_lexeme = False
        inserted_surface_form = False
        inserted_lemma_surface_form = False
        lemma_translation = self._lookup_translation(stored_lemma)
        surface_translation = self._lookup_translation(normalized_surface) if normalized_surface else None
        lemma_pos_tag, lemma_morphology = self._extract_pos_and_morphology(
            stored_lemma,
            preferred_pos_tag=selected_pos_tag,
        )
        if lemma_pos_tag is None and selected_pos_tag is not None:
            lemma_pos_tag = selected_pos_tag
        if lemma_morphology is None and selected_morphology is not None:
            lemma_morphology = selected_morphology
        surface_pos_tag: str | None = None
        surface_morphology: str | None = None
        if normalized_surface:
            if selected_pos_tag is not None or selected_morphology is not None:
                # Preserve search-selected analysis for the saved surface form.
                surface_pos_tag = selected_pos_tag
                surface_morphology = selected_morphology
            else:
                surface_pos_tag, surface_morphology = self._extract_pos_and_morphology(
                    normalized_surface,
                    preferred_pos_tag=selected_pos_tag,
                )
        provider = self._translation_provider_name()

        with get_connection(self._db_path) as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO lexemes (
                    lemma,
                    source,
                    english_translation,
                    translation_provider,
                    pos_tag,
                    morphology
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    stored_lemma,
                    "manual",
                    lemma_translation,
                    provider if lemma_translation else None,
                    lemma_pos_tag,
                    lemma_morphology,
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
                    SET english_translation = ?, translation_provider = ?
                    WHERE id = ?
                    """,
                    (lemma_translation, provider, lexeme_row["id"]),
                )

            conn.execute(
                """
                UPDATE lexemes
                SET pos_tag = COALESCE(pos_tag, ?),
                    morphology = COALESCE(morphology, ?)
                WHERE id = ?
                """,
                (lemma_pos_tag, lemma_morphology, lexeme_row["id"]),
            )

            if normalized_surface and normalized_surface != stored_lemma:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO surface_forms (
                        lexeme_id,
                        form,
                        source,
                        english_translation,
                        translation_provider,
                        pos_tag,
                        morphology
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lexeme_row["id"],
                        stored_lemma,
                        "manual",
                        lemma_translation,
                        provider if lemma_translation else None,
                        lemma_pos_tag,
                        lemma_morphology,
                    ),
                )
                inserted_lemma_surface_form = cursor.rowcount == 1
                conn.execute(
                    """
                    UPDATE surface_forms
                    SET seen_count = seen_count + 1,
                        last_seen_at = CURRENT_TIMESTAMP
                    WHERE lexeme_id = ? AND form = ?
                    """,
                    (lexeme_row["id"], stored_lemma),
                )
                if lemma_translation:
                    conn.execute(
                        """
                        UPDATE surface_forms
                        SET english_translation = ?, translation_provider = ?
                        WHERE lexeme_id = ? AND form = ?
                        """,
                        (lemma_translation, provider, lexeme_row["id"], stored_lemma),
                    )
                conn.execute(
                    """
                    UPDATE surface_forms
                    SET pos_tag = COALESCE(pos_tag, ?),
                        morphology = COALESCE(morphology, ?)
                    WHERE lexeme_id = ? AND form = ?
                    """,
                    (lemma_pos_tag, lemma_morphology, lexeme_row["id"], stored_lemma),
                )

            if normalized_surface:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO surface_forms (
                        lexeme_id,
                        form,
                        source,
                        english_translation,
                        translation_provider,
                        pos_tag,
                        morphology
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lexeme_row["id"],
                        normalized_surface,
                        "manual",
                        surface_translation,
                        provider if surface_translation else None,
                        surface_pos_tag,
                        surface_morphology,
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
                        SET english_translation = ?, translation_provider = ?
                        WHERE lexeme_id = ? AND form = ?
                        """,
                        (surface_translation, provider, lexeme_row["id"], normalized_surface),
                    )
                conn.execute(
                    """
                    UPDATE surface_forms
                    SET pos_tag = COALESCE(pos_tag, ?),
                        morphology = COALESCE(morphology, ?)
                    WHERE lexeme_id = ? AND form = ?
                    """,
                    (surface_pos_tag, surface_morphology, lexeme_row["id"], normalized_surface),
                )

        self._invalidate_pos_cache(stored_lemma, normalized_surface)

        inserted = inserted_lexeme or inserted_surface_form or inserted_lemma_surface_form
        if self._typo_engine is not None and inserted:
            self._typo_engine.add_user_lexeme(stored_lemma)

        status: Literal["inserted", "exists"] = "inserted" if inserted else "exists"
        message = (
            f"Added '{stored_lemma}' to wordbank."
            if inserted
            else f"'{stored_lemma}' is already in the wordbank."
        )
        verification = self._queued_verification_result()

        return AddWordResponse(
            status=status,
            stored_lemma=stored_lemma,
            stored_surface_form=normalized_surface or None,
            source="manual",
            message=message,
            verification=verification,
        )




    def _extract_pos_and_morphology_batch(self, values: list[str]) -> dict[str, tuple[str | None, str | None]]:
        return {value: self._extract_pos_and_morphology(value) for value in values}




    def _extract_pos_and_morphology(
        self,
        value: str,
        *,
        preferred_pos_tag: str | None = None,
    ) -> tuple[str | None, str | None]:
        normalized_value = normalize_token(value)
        normalized_preferred_pos = self._normalize_optional_pos_tag(preferred_pos_tag)
        cache_key = (normalized_value, normalized_preferred_pos)
        cached = self._pos_morph_cache.get(cache_key)
        if cached is not None:
            return cached

        cor_entry = self._best_cor_entry(
            self._cor_entries_for_surface(normalized_value),
            normalized_surface=normalized_value,
            preferred_pos_tag=normalized_preferred_pos,
        )
        if cor_entry is not None:
            extracted = (cor_entry.pos_tag, cor_entry.morphology)
            self._pos_morph_cache[cache_key] = extracted
            return extracted

        if self._nlp_adapter is None:
            self._pos_morph_cache[cache_key] = (None, None)
            return None, None

        for token in self._nlp_adapter.tokenize(normalized_value):
            surface = token.text
            if not surface.strip():
                continue
            if token.is_punctuation:
                continue
            if not is_wordlike_token(surface):
                continue
            extracted = (token.pos, token.morphology)
            self._pos_morph_cache[cache_key] = extracted
            return extracted

        self._pos_morph_cache[cache_key] = (None, None)
        return None, None




    @staticmethod
    def _normalize_optional_pos_tag(value: str | None) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip().upper()
        if not cleaned:
            return None
        return cleaned




    @staticmethod
    def _normalize_optional_morphology(value: str | None) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        return cleaned



