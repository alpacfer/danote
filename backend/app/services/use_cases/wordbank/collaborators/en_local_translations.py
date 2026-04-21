from __future__ import annotations

import logging
from typing import Protocol

from app.services.translation import TranslationService


logger = logging.getLogger(__name__)


class _EnGeminiLike(Protocol):
    def translate_english_lemma(
        self, *, lemma: str, pos_ud: str | None, gloss: str | None
    ) -> str | None: ...


def translate_en_lemma_contextual(
    *,
    lemma: str,
    pos_ud: str | None,
    gloss: str | None,
    gemini_service: _EnGeminiLike | None,
    translation_service: TranslationService | None,
    cache: dict[tuple[str, str, str], str | None] | None = None,
) -> str | None:
    normalized_lemma = (lemma or "").strip()
    if not normalized_lemma:
        return None

    cache_key = (
        normalized_lemma.lower(),
        (pos_ud or "").upper(),
        (gloss or "").strip().lower(),
    )
    if cache is not None and cache_key in cache:
        return cache[cache_key]

    result: str | None = None
    if gemini_service is not None:
        try:
            result = gemini_service.translate_english_lemma(
                lemma=normalized_lemma,
                pos_ud=pos_ud,
                gloss=gloss,
            )
        except Exception:
            logger.exception("en_gemini_translation_failed")
            result = None

    if not result and translation_service is not None:
        try:
            result = translation_service.translate_en_to_da(normalized_lemma)
        except Exception:
            logger.exception("en_fallback_translation_failed")
            result = None

    if isinstance(result, str):
        result = result.strip() or None

    if cache is not None:
        cache[cache_key] = result
    return result
