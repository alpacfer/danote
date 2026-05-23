from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.services.token_classifier import normalize_token

if TYPE_CHECKING:
    from app.services.verification import WordVerificationInput, WordVerificationSurfaceForm


def optional_clean_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def optional_clean_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned_values: list[str] = []
    seen: set[str] = set()
    for item in value:
        cleaned = optional_clean_str(item)
        if cleaned is None or cleaned in seen:
            continue
        seen.add(cleaned)
        cleaned_values.append(cleaned)
    return cleaned_values


def verification_surface_forms(payload: WordVerificationInput) -> tuple[WordVerificationSurfaceForm, ...]:
    normalized_lemma = normalize_token(payload.stored_lemma)
    if payload.review_intent == "complete_variations" and payload.meaning_id is not None:
        return tuple(form for form in payload.available_surface_forms if form.meaning_id == payload.meaning_id)
    if payload.meaning_id is not None:
        return tuple(form for form in payload.available_surface_forms if form.meaning_id == payload.meaning_id)
    if payload.stored_surface_form:
        normalized_surface = normalize_token(payload.stored_surface_form)
        return tuple(
            form
            for form in payload.available_surface_forms
            if normalize_token(form.form) in {normalized_lemma, normalized_surface}
        )
    return tuple(
        form for form in payload.available_surface_forms if normalize_token(form.form) == normalized_lemma
    )


def category_surface_forms(payload: WordVerificationInput) -> tuple[WordVerificationSurfaceForm, ...]:
    if payload.meaning_id is not None:
        return tuple(form for form in payload.available_surface_forms if form.meaning_id == payload.meaning_id)
    return payload.available_surface_forms


def is_valid_new_category(label: str) -> bool:
    normalized = " ".join(label.strip().split())
    if not normalized:
        return False
    if len(normalized) > 40:
        return False
    words = normalized.split(" ")
    if len(words) > 3:
        return False
    blocked = {
        "action",
        "actions",
        "thing",
        "things",
        "object",
        "objects",
        "misc",
        "miscellaneous",
        "other",
        "general",
        "noun",
        "nouns",
        "verb",
        "verbs",
        "adjective",
        "adjectives",
        "adverb",
        "adverbs",
        "pronoun",
        "pronouns",
        "preposition",
        "prepositions",
        "conjunction",
        "conjunctions",
        "singular",
        "plural",
        "definite",
        "indefinite",
        "masculine",
        "feminine",
        "neuter",
    }
    if normalized.casefold() in blocked:
        return False
    return any(character.isalpha() for character in normalized)
