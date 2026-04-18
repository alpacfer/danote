from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TranslationLookupResult:
    translation: str | None
    provider: str | None


@dataclass(frozen=True, slots=True)
class AlternativeTranslationsLookupResult:
    primary_translation: str | None
    alternative_translations: list[str]
    provider: str | None
