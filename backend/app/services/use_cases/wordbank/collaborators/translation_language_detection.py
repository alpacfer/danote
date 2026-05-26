from __future__ import annotations

from collections.abc import Callable

from app.api.schemas.v1.wordbank import DetectWordLanguageResponse
from app.services.token_classifier import normalize_token

AMBIGUOUS_SHORT_WORDS = frozenset({"an", "at", "de", "den", "det", "en", "for", "gift", "i", "in", "is", "it", "to"})


def detect_word_language(
    source_word: str,
    *,
    detect_source_language: Callable[[str], str | None],
    cor_entries_lookup: Callable[[str], list] | None = None,
) -> DetectWordLanguageResponse:
    normalized_source = normalize_token(source_word)
    if not normalized_source:
        raise ValueError("source_word is required")

    normalized_lower = normalized_source.lower()
    if any(char in normalized_lower for char in ("æ", "ø", "å")):
        return DetectWordLanguageResponse(source_word=normalized_source, language="da", confidence=0.99)
    if " " in normalized_source:
        parts = normalized_source.split()
        if len(parts) > 3:
            return DetectWordLanguageResponse(source_word=normalized_source, language="ambiguous", confidence=0.25)
    if not normalized_lower.isascii() or not normalized_lower.replace("-", "").replace("'", "").replace(" ", "").isalpha():
        return DetectWordLanguageResponse(source_word=normalized_source, language="ambiguous", confidence=0.25)
    if cor_entries_lookup is not None and cor_entries_lookup(normalized_source):
        return DetectWordLanguageResponse(source_word=normalized_source, language="da", confidence=0.95)

    detected = detect_source_language(normalized_source)
    if normalized_lower in AMBIGUOUS_SHORT_WORDS:
        return DetectWordLanguageResponse(source_word=normalized_source, language="ambiguous", confidence=0.4)
    if len(normalized_lower) <= 2:
        if detected in {"en", "da"}:
            return DetectWordLanguageResponse(source_word=normalized_source, language=detected, confidence=0.45)
        return DetectWordLanguageResponse(source_word=normalized_source, language="ambiguous", confidence=0.4)
    if detected in {"en", "da"}:
        return DetectWordLanguageResponse(source_word=normalized_source, language=detected, confidence=0.82)

    fallback_english_like = bool(
        normalized_lower and normalized_lower[0].isalpha() and any(char in "aeiouy" for char in normalized_lower)
    )
    if fallback_english_like:
        return DetectWordLanguageResponse(source_word=normalized_source, language="en", confidence=0.55)
    return DetectWordLanguageResponse(source_word=normalized_source, language="ambiguous", confidence=0.35)
