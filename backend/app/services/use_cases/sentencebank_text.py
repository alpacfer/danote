from __future__ import annotations

from typing import Literal


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


