from __future__ import annotations

from typing import Literal

from app.api.schemas.v1.sentencebank import (
    AddSentenceResponse,
    SentenceListResponse,
    SentenceSummary,
)
from app.db.migrations import get_connection
from app.services.token_classifier import normalize_token
from app.services.translation import TranslationService


def _normalize_sentence_text(source_text: str) -> str:
    return " ".join(source_text.strip().split())


class SentencebankUseCase:
    def __init__(
        self,
        db_path,
        translation_service: TranslationService | None = None,
    ):
        self._db_path = db_path
        self._translation_service = translation_service

    def add_sentence(self, source_text: str) -> AddSentenceResponse:
        normalized_source_text = _normalize_sentence_text(source_text)
        normalized_key = normalize_token(source_text)
        if not normalized_source_text or not normalized_key:
            raise ValueError("source_text is required")

        with get_connection(self._db_path) as conn:
            existing = conn.execute(
                """
                SELECT source_sentence, english_translation
                FROM sentence_bank
                WHERE normalized_sentence = ?
                LIMIT 1
                """,
                (normalized_key,),
            ).fetchone()
            if existing is not None:
                stored_sentence = str(existing["source_sentence"])
                return AddSentenceResponse(
                    status="exists",
                    source_text=stored_sentence,
                    english_translation=existing["english_translation"],
                    message=f'"{stored_sentence}" is already in sentencebank.',
                )

            english_translation = self._lookup_translation(normalized_source_text)

            conn.execute(
                """
                INSERT INTO sentence_bank (
                    source_sentence,
                    normalized_sentence,
                    english_translation,
                    translation_provider
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    normalized_source_text,
                    normalized_key,
                    english_translation,
                    "deepl" if english_translation else None,
                ),
            )

        status: Literal["inserted", "exists"] = "inserted"
        return AddSentenceResponse(
            status=status,
            source_text=normalized_source_text,
            english_translation=english_translation,
            message=f'Added "{normalized_source_text}" to sentencebank.',
        )

    def list_sentences(self) -> SentenceListResponse:
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, source_sentence, english_translation, created_at
                FROM sentence_bank
                ORDER BY datetime(created_at) DESC, id DESC
                """
            ).fetchall()

        return SentenceListResponse(
            items=[
                SentenceSummary(
                    id=int(row["id"]),
                    source_text=str(row["source_sentence"]),
                    english_translation=row["english_translation"],
                    created_at=str(row["created_at"]),
                )
                for row in rows
            ]
        )

    def _lookup_translation(self, source_text: str) -> str | None:
        if self._translation_service is None:
            return None
        try:
            return self._translation_service.translate_da_to_en(source_text)
        except Exception:
            return None
