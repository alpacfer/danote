from __future__ import annotations

from typing import Literal

from app.api.schemas.v1.sentencebank import SentenceSearchPreviewResponse
from app.services.sentence_verification import (
    SentenceMWEMeaning,
    SentenceVerificationError,
    SentenceVerificationErrorSpan,
    SentenceVerificationResult,
    SentenceVerificationService,
)
from app.services.translation import TranslationService


def normalize_sentence_text(source_text: str) -> str:
    return " ".join(source_text.strip().split())


def normalize_sentence_text_without_terminal_period(source_text: str) -> str:
    normalized = normalize_sentence_text(source_text)
    if normalized.endswith("."):
        return normalized[:-1].rstrip()
    return normalized


def capitalize_sentence_translation(english_translation: str | None) -> str | None:
    if not isinstance(english_translation, str):
        return None
    cleaned = " ".join(english_translation.strip().split())
    if not cleaned:
        return None

    alpha_index = next((idx for idx, char in enumerate(cleaned) if char.isalpha()), None)
    if alpha_index is None or cleaned[alpha_index].isupper():
        return cleaned
    return cleaned[:alpha_index] + cleaned[alpha_index].upper() + cleaned[alpha_index + 1 :]


def preserve_leading_letter_case(source_text: str, corrected_text: str | None) -> str | None:
    if not corrected_text:
        return None

    source_index = next((idx for idx, char in enumerate(source_text) if char.isalpha()), None)
    corrected_index = next((idx for idx, char in enumerate(corrected_text) if char.isalpha()), None)
    if source_index is None or corrected_index is None:
        return corrected_text

    source_char = source_text[source_index]
    corrected_char = corrected_text[corrected_index]
    if source_char.islower() and corrected_char.isupper():
        return (
            corrected_text[:corrected_index]
            + corrected_char.lower()
            + corrected_text[corrected_index + 1 :]
        )
    if source_char.isupper() and corrected_char.islower():
        return (
            corrected_text[:corrected_index]
            + corrected_char.upper()
            + corrected_text[corrected_index + 1 :]
        )
    return corrected_text


def normalize_query_language(value: str | None) -> Literal["da", "en", "unknown"]:
    cleaned = value.strip().lower() if isinstance(value, str) else ""
    if cleaned == "da":
        return "da"
    if cleaned == "en":
        return "en"
    return "unknown"


def starts_with_uppercase_letter(text: str) -> bool:
    for char in text:
        if char.isalpha():
            return char.isupper()
    return False


def has_internal_uppercase_letter(text: str) -> bool:
    seen_alpha = False
    for char in text:
        if not char.isalpha():
            continue
        if seen_alpha and char.isupper():
            return True
        seen_alpha = True
    return False


def should_skip_sentence_wordbank_token(
    *,
    surface_form: str,
    lemma_candidate: str,
    pos_tag: str | None,
    token_index: int,
) -> bool:
    if (pos_tag or "").strip().upper() == "PROPN":
        return True
    if token_index > 0 and starts_with_uppercase_letter(surface_form):
        return True
    return has_internal_uppercase_letter(surface_form) or has_internal_uppercase_letter(
        lemma_candidate
    )


def heuristic_detect_language(source_text: str) -> Literal["da", "en", "unknown"]:
    lower = source_text.lower()
    if any(char in lower for char in ("æ", "ø", "å")):
        return "da"
    if source_text.isascii():
        return "en"
    return "unknown"


def translation_provider_name(translation_service: object | None) -> str:
    provider = getattr(translation_service, "provider", None)
    if isinstance(provider, str):
        cleaned = provider.strip().lower()
        if cleaned:
            return cleaned
    return "translation"


_DANISH_MARKERS = {
    "jeg", "du", "han", "hun", "vi", "de", "det", "den", "der", "har", "er",
    "en", "et", "på", "og", "ikke", "hunden", "katten", "tøj",
}
_ENGLISH_MARKERS = {
    "you", "he", "she", "we", "they", "a", "an", "the", "have", "has",
    "is", "are", "dog", "run", "garden", "happy", "want", "buy", "clothes",
}


def looks_mixed_language(source_text: str) -> bool:
    words = [word.strip(".,!?;:()[]{}\"'").casefold() for word in source_text.split()]
    words = [word for word in words if word]
    if not words:
        return False
    has_danish = any(word in _DANISH_MARKERS or any(ch in word for ch in "æøå") for word in words)
    has_english = any(word in _ENGLISH_MARKERS for word in words)
    if not has_danish or not has_english:
        return False
    # Uppercase "I" is a Danish pronoun in e.g. "I har en hund"; do not treat it
    # as English when the rest of the sentence is Danish.
    if len(words) >= 3 and source_text.split()[0] == "I" and {"har", "er"} & set(words[1:]):
        return False
    return True


def meaning_id_suffix(meaning: SentenceMWEMeaning, *, fallback_index: int) -> str:
    """Pick a stable suffix for the synthesized cor_id of an MWE meaning.

    Prefer Gemini's meaning_key; fall back to the english_translation (snake);
    last resort is the position. Always normalized to uppercase ASCII-safe form
    so it slots into a cor_id-like string.
    """
    candidate = (meaning.meaning_key or meaning.english_translation or meaning.gloss or "").strip()
    if not candidate:
        return f"SENSE_{fallback_index}"
    # Compact + safe for use inside a cor_id-like identifier.
    normalized = "_".join(candidate.upper().split())
    safe = "".join(ch for ch in normalized if ch.isalnum() or ch in {"_", "-"})
    return safe or f"SENSE_{fallback_index}"


def blocked_preview(
    *,
    query_language: Literal["da", "en", "unknown"],
    message: str,
) -> SentenceSearchPreviewResponse:
    return SentenceSearchPreviewResponse(
        status="blocked",
        query_language=query_language,
        source_text=None,
        english_translation=None,
        is_valid=False,
        errors=[],
        message=message,
    )


def heuristic_danish_correction(source_text: str) -> SentenceVerificationResult | None:
    replacements = {
        "spise": "spiser",
        "løbe": "løber",
        "købe": "køber",
        "have": "har",
    }
    words = source_text.split()
    if len(words) < 2:
        return None
    subject = words[0].casefold()
    verb = words[1].casefold().strip(".,!?")
    if subject not in {"jeg", "du", "han", "hun", "vi", "de"} or verb not in replacements:
        return None
    corrected_words = list(words)
    corrected_words[1] = replacements[verb]
    corrected = " ".join(corrected_words)
    start = source_text.find(words[1])
    end = start + len(words[1]) if start >= 0 else len(words[0]) + 1 + len(words[1])
    return SentenceVerificationResult(
        is_valid=False,
        errors=[SentenceVerificationErrorSpan(start=start, end=end, message="Use the finite verb form.")],
        corrected_text=corrected,
        language="da",
    )


def curated_mwe_meanings(normalized: str) -> list[SentenceMWEMeaning]:
    if normalized == "tage på":
        return [
            SentenceMWEMeaning(
                gloss="iføre sig tøj",
                english_translation="to put on",
                pos_tag="VERB",
                meaning_key="iføre sig tøj",
            ),
            SentenceMWEMeaning(
                gloss="forøge sin kropsvægt",
                english_translation="to gain weight",
                pos_tag="VERB",
                meaning_key="tage på i vægt",
            ),
            SentenceMWEMeaning(
                gloss="tage afsted",
                english_translation="to go somewhere",
                pos_tag="VERB",
                meaning_key="tage afsted",
            ),
        ]
    if normalized == "gå ud":
        return [
            SentenceMWEMeaning(
                gloss="forlade et sted eller være socialt ude",
                english_translation="to go out",
                pos_tag="VERB",
                meaning_key="gå ud",
            )
        ]
    if normalized == "se efter":
        return [
            SentenceMWEMeaning(
                gloss="lede efter eller undersøge",
                english_translation="to look for",
                pos_tag="VERB",
                meaning_key="se efter",
            )
        ]
    return []


def lookup_reverse_translation(
    *,
    source_text: str,
    translation_service: TranslationService | None,
) -> str | None:
    if translation_service is None:
        return None
    translate_en_to_da = getattr(translation_service, "translate_en_to_da", None)
    if not callable(translate_en_to_da):
        return None
    try:
        translated = translate_en_to_da(source_text)
        return (
            normalize_sentence_text_without_terminal_period(translated)
            if isinstance(translated, str) and translated.strip()
            else None
        )
    except Exception:
        return None


def detect_query_language_for_preview(
    *,
    source_text: str,
    translation_service: TranslationService | None,
) -> Literal["da", "en", "unknown"]:
    if translation_service is None:
        return "unknown"
    detect_source_language = getattr(translation_service, "detect_source_language", None)
    if not callable(detect_source_language):
        return "unknown"
    try:
        return normalize_query_language(detect_source_language(source_text))
    except Exception:
        return "unknown"


def verify_sentence_result(
    *,
    source_text: str,
    sentence_verification_service: SentenceVerificationService | None,
) -> SentenceVerificationResult:
    if sentence_verification_service is None:
        return SentenceVerificationResult(
            is_valid=True,
            errors=[],
            corrected_text=None,
            language="unknown",
        )
    try:
        return sentence_verification_service.verify_sentence(source_text)
    except Exception as exc:
        raise SentenceVerificationError("Sentence verification unavailable.") from exc



