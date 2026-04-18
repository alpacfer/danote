from __future__ import annotations


def normalize_sentence_text(source_text: str) -> str:
    return " ".join(source_text.strip().split())


def normalize_sentence_translation_value(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.strip().split())
    return cleaned or None


def align_sentence_translation_capitalization(
    source_text: str,
    english_translation: str | None,
) -> str | None:
    if not english_translation:
        return None

    source_index = next((idx for idx, char in enumerate(source_text) if char.isalpha()), None)
    translation_index = next((idx for idx, char in enumerate(english_translation) if char.isalpha()), None)
    if translation_index is None:
        return english_translation

    translation_char = english_translation[translation_index]
    if source_index is None or source_text[source_index].islower():
        if translation_char.islower():
            return (
                english_translation[:translation_index]
                + translation_char.upper()
                + english_translation[translation_index + 1 :]
            )
        return english_translation

    if source_text[source_index].isupper() and translation_char.islower():
        return (
            english_translation[:translation_index]
            + translation_char.upper()
            + english_translation[translation_index + 1 :]
        )
    return english_translation
