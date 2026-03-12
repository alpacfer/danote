from __future__ import annotations


def provider_name(translation_service: object | None) -> str:
    provider = getattr(translation_service, "provider", None)
    if isinstance(provider, str):
        cleaned = provider.strip().lower()
        if cleaned:
            return cleaned
    return "translation"


def contextual_provider_name(gemini_word_translation_service: object | None) -> str:
    provider = getattr(gemini_word_translation_service, "provider", None)
    if isinstance(provider, str):
        cleaned = provider.strip().lower()
        if cleaned:
            return cleaned
    return "gemini_word_translation"
