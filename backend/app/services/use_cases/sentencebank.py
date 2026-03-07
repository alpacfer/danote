from __future__ import annotations

from typing import Literal

from app.api.schemas.v1.sentencebank import (
    AddSentenceResponse,
    SentenceListResponse,
    SentenceSummary,
)
from app.db.repositories import SentencebankRepository
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
        self._repository = SentencebankRepository(db_path)
        self._translation_service = translation_service

    def add_sentence(self, source_text: str) -> AddSentenceResponse:
        normalized_source_text = _normalize_sentence_text(source_text)
        normalized_key = normalize_token(source_text)
        if not normalized_source_text or not normalized_key:
            raise ValueError("source_text is required")

        existing = self._repository.find_by_normalized_sentence(normalized_key)
        if existing is not None:
            return AddSentenceResponse(
                status="exists",
                source_text=existing.source_text,
                english_translation=existing.english_translation,
                message=f'"{existing.source_text}" is already in sentencebank.',
            )

        english_translation = self._lookup_translation(normalized_source_text)
        provider = self._translation_provider_name()
        self._repository.insert_sentence(
            source_text=normalized_source_text,
            normalized_sentence=normalized_key,
            english_translation=english_translation,
            translation_provider=provider if english_translation else None,
        )

        status: Literal["inserted", "exists"] = "inserted"
        return AddSentenceResponse(
            status=status,
            source_text=normalized_source_text,
            english_translation=english_translation,
            message=f'Added "{normalized_source_text}" to sentencebank.',
        )

    def list_sentences(self) -> SentenceListResponse:
        rows = self._repository.list_sentences()

        return SentenceListResponse(
            items=[
                SentenceSummary(
                    id=row.id,
                    source_text=row.source_text,
                    english_translation=row.english_translation,
                    created_at=row.created_at,
                )
                for row in rows
            ]
        )

    def _lookup_translation(self, source_text: str) -> str | None:
        if self._translation_service is None:
            return None
        try:
            translated = self._translation_service.translate_da_to_en(source_text)
            if not isinstance(translated, str):
                return None
            cleaned = " ".join(translated.strip().split())
            if not cleaned:
                return None
            return cleaned.lower()
        except Exception:
            return None

    def _translation_provider_name(self) -> str:
        provider = getattr(self._translation_service, "provider", None)
        if isinstance(provider, str):
            cleaned = provider.strip().lower()
            if cleaned:
                return cleaned
        return "translation"
