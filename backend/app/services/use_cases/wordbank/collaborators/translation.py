from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.api.schemas.v1.wordbank import (
    DetectWordLanguageResponse,
    GeneratePhraseTranslationResponse,
    GenerateReverseTranslationResponse,
    GenerateTranslationResponse,
)
from app.db.migrations import get_connection
from app.services.token_classifier import normalize_token
from app.services.translation import TranslationService


class TranslationCollaborator:
    """Handles DA↔EN translation, language detection, and related DB writes."""

    _AMBIGUOUS_SHORT_WORDS = frozenset(
        {
            "an",
            "at",
            "de",
            "den",
            "det",
            "en",
            "for",
            "gift",
            "i",
            "in",
            "is",
            "it",
            "to",
        }
    )

    def __init__(self, translation_service: TranslationService | None, db_path: Path) -> None:
        self._translation_service = translation_service
        self._db_path = db_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_translation(
        self, surface_token: str, lemma_candidate: str | None
    ) -> GenerateTranslationResponse:
        normalized_surface = normalize_token(surface_token)
        normalized_lemma = normalize_token(lemma_candidate or "")
        stored_lemma = normalized_lemma or normalized_surface

        if not normalized_surface:
            raise ValueError("surface_token or lemma_candidate is required")

        english_translation = self.lookup_translation(normalized_surface)
        provider = self.provider_name()
        if english_translation:
            with get_connection(self._db_path) as conn:
                conn.execute(
                    """
                    UPDATE surface_forms
                    SET english_translation = ?, translation_provider = ?
                    WHERE form = ?
                    """,
                    (english_translation, provider, normalized_surface),
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

            english_translation = self.lookup_translation(normalized_source_text)
            provider = self.provider_name()
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
                    provider if english_translation else None,
                ),
            )

        return GeneratePhraseTranslationResponse(
            status="generated" if english_translation else "unavailable",
            source_text=normalized_source_text,
            english_translation=english_translation,
        )

    def generate_reverse_translation(self, source_word: str) -> GenerateReverseTranslationResponse:
        normalized_source = normalize_token(source_word)
        if not normalized_source:
            raise ValueError("source_word is required")
        danish_translation_raw = self._lookup_reverse_translation(normalized_source)
        danish_translation = (
            normalize_token(danish_translation_raw) if danish_translation_raw else None
        )
        return GenerateReverseTranslationResponse(
            status="generated" if danish_translation else "unavailable",
            source_word=normalized_source,
            danish_translation=danish_translation,
        )

    def detect_word_language(
        self,
        source_word: str,
        *,
        cor_entries_lookup: Callable[[str], list] | None = None,
    ) -> DetectWordLanguageResponse:
        """Detect whether source_word is Danish, English, or ambiguous.

        cor_entries_lookup: optional callable(normalized_token) -> list[COREntry].
        When provided, a non-empty result signals the word is Danish.
        """
        normalized_source = normalize_token(source_word)
        if not normalized_source:
            raise ValueError("source_word is required")

        normalized_lower = normalized_source.lower()
        if any(char in normalized_lower for char in ("æ", "ø", "å")):
            return DetectWordLanguageResponse(
                source_word=normalized_source,
                language="da",
                confidence=0.99,
            )

        if " " in normalized_source:
            return DetectWordLanguageResponse(
                source_word=normalized_source,
                language="ambiguous",
                confidence=0.25,
            )

        if not normalized_lower.isascii() or not normalized_lower.replace("-", "").replace("'", "").isalpha():
            return DetectWordLanguageResponse(
                source_word=normalized_source,
                language="ambiguous",
                confidence=0.25,
            )

        if cor_entries_lookup is not None and cor_entries_lookup(normalized_source):
            return DetectWordLanguageResponse(
                source_word=normalized_source,
                language="da",
                confidence=0.95,
            )

        detected_source_language = self._lookup_detected_source_language(normalized_source)
        if normalized_lower in self._AMBIGUOUS_SHORT_WORDS:
            return DetectWordLanguageResponse(
                source_word=normalized_source,
                language="ambiguous",
                confidence=0.4,
            )

        if len(normalized_lower) <= 2:
            if detected_source_language in {"en", "da"}:
                return DetectWordLanguageResponse(
                    source_word=normalized_source,
                    language=detected_source_language,
                    confidence=0.45,
                )
            return DetectWordLanguageResponse(
                source_word=normalized_source,
                language="ambiguous",
                confidence=0.4,
            )

        if detected_source_language in {"en", "da"}:
            return DetectWordLanguageResponse(
                source_word=normalized_source,
                language=detected_source_language,
                confidence=0.82,
            )

        fallback_english_like = bool(
            normalized_lower
            and normalized_lower[0].isalpha()
            and any(char in "aeiouy" for char in normalized_lower)
        )
        if fallback_english_like:
            return DetectWordLanguageResponse(
                source_word=normalized_source,
                language="en",
                confidence=0.55,
            )

        return DetectWordLanguageResponse(
            source_word=normalized_source,
            language="ambiguous",
            confidence=0.35,
        )

    def lookup_translation(self, source_word: str) -> str | None:
        if self._translation_service is None:
            return None
        try:
            translated = self._translation_service.translate_da_to_en(source_word)
            return self.normalize_translation_value(translated)
        except Exception:
            return None

    def provider_name(self) -> str:
        provider = getattr(self._translation_service, "provider", None)
        if isinstance(provider, str):
            cleaned = provider.strip().lower()
            if cleaned:
                return cleaned
        return "translation"

    def normalize_comparable(self, value: str) -> str:
        return " ".join(value.strip().lower().split())

    def is_likely_english_word(self, value: str) -> bool:
        normalized = value.strip().lower()
        if not normalized or " " in normalized:
            return False
        if any(char in normalized for char in ("æ", "ø", "å")):
            return False
        allowed = set("abcdefghijklmnopqrstuvwxyz'-")
        if any(char not in allowed for char in normalized):
            return False
        return any(char in "aeiouy" for char in normalized)

    def lookup_reverse_translation(self, source_word: str) -> str | None:
        return self._lookup_reverse_translation(source_word)

    @staticmethod
    def normalize_translation_value(value: str | None) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            return None
        return cleaned.lower()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _lookup_reverse_translation(self, source_word: str) -> str | None:
        if self._translation_service is None:
            return None
        translate_en_to_da = getattr(self._translation_service, "translate_en_to_da", None)
        if not callable(translate_en_to_da):
            return None
        try:
            translated = translate_en_to_da(source_word)
            return self.normalize_translation_value(translated)
        except Exception:
            return None

    def _lookup_detected_source_language(self, source_word: str) -> str | None:
        if self._translation_service is None:
            return None
        detect_source_language = getattr(self._translation_service, "detect_source_language", None)
        if not callable(detect_source_language):
            return None
        try:
            provider_language = detect_source_language(source_word)
        except Exception:
            return None
        if not provider_language:
            return None
        normalized = provider_language.strip().lower()
        if normalized.startswith("en"):
            return "en"
        if normalized.startswith("da"):
            return "da"
        return None
