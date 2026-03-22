from __future__ import annotations

from app.api.schemas.v1.wordbank import FindAlternativeTranslationsResponse
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.translation_helpers import normalize_translation_value
from app.services.use_cases.wordbank.runtime import WordbankRuntime


def find_alternative_translations(
    runtime: WordbankRuntime,
    *,
    stored_lemma: str,
    meaning_id: int | None,
) -> FindAlternativeTranslationsResponse:
    normalized_lemma = normalize_token(stored_lemma)
    if not normalized_lemma:
        raise ValueError("stored_lemma is required")

    lexeme = runtime.repository.get_lexeme(normalized_lemma)
    if lexeme is None:
        raise LookupError(f"Lemma '{normalized_lemma}' was not found.")

    meaning = None
    if meaning_id is not None:
        meaning = next(
            (record for record in runtime.repository.list_lexeme_meanings(lexeme.id) if record.id == meaning_id),
            None,
        )
        if meaning is None:
            raise LookupError(f"Meaning '{meaning_id}' was not found for lemma '{normalized_lemma}'.")

    scope_meaning_id = meaning.id if meaning is not None else None
    current_translation = meaning.english_translation if meaning is not None else lexeme.english_translation
    result = runtime.translation.find_alternative_translations(
        surface_form=lexeme.lemma,
        lemma=lexeme.lemma,
        pos_tag=meaning.pos_tag if meaning is not None else lexeme.pos_tag,
        morphology=meaning.morphology if meaning is not None else lexeme.morphology,
        gloss=meaning.gloss if meaning is not None else None,
        current_translation=current_translation,
        existing_additional_translations=_translation_values(
            runtime.repository.list_additional_translations(
                lexeme_id=lexeme.id,
                meaning_id=scope_meaning_id,
            )
        ),
    )
    if result.provider is None:
        return FindAlternativeTranslationsResponse(
            status="error",
            stored_lemma=lexeme.lemma,
            meaning_id=scope_meaning_id,
            primary_translation=normalize_translation_value(current_translation),
            added_additional_translations=[],
            message="Alternative translations are unavailable because Gemini translation is not configured.",
        )

    normalized_current = normalize_translation_value(current_translation)
    normalized_primary = normalize_translation_value(result.primary_translation)
    updated_primary_translation = (
        normalized_primary is not None and normalized_primary != normalized_current
    )

    if updated_primary_translation:
        if meaning is not None:
            runtime.repository.replace_lexeme_meaning_translation(
                meaning_id=meaning.id,
                english_translation=normalized_primary,
            )
        else:
            runtime.repository.replace_lexeme_translation(
                lexeme_id=lexeme.id,
                english_translation=normalized_primary,
                provider=result.provider,
            )

    final_primary = normalized_primary or normalized_current
    added_additional_translations: list[str] = []
    for translation in _unique_translation_values(result.alternative_translations):
        if translation == final_primary:
            continue
        if runtime.repository.insert_additional_translation(
            lexeme_id=lexeme.id,
            meaning_id=scope_meaning_id,
            english_translation=translation,
            source="alternative_translations",
        ):
            added_additional_translations.append(translation)

    if updated_primary_translation or added_additional_translations:
        return FindAlternativeTranslationsResponse(
            status="updated",
            stored_lemma=lexeme.lemma,
            meaning_id=scope_meaning_id,
            primary_translation=final_primary,
            added_additional_translations=added_additional_translations,
            message=_updated_message(
                lemma=lexeme.lemma,
                updated_primary_translation=updated_primary_translation,
                added_additional_translations=added_additional_translations,
            ),
        )

    return FindAlternativeTranslationsResponse(
        status="skipped",
        stored_lemma=lexeme.lemma,
        meaning_id=scope_meaning_id,
        primary_translation=final_primary,
        added_additional_translations=[],
        message=f"No common alternative translations found for '{lexeme.lemma}'.",
    )


def _translation_values(records: list[object]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for record in records:
        normalized = normalize_translation_value(getattr(record, "english_translation", None))
        if normalized is None or normalized in seen:
            continue
        seen.add(normalized)
        values.append(normalized)
    return values


def _unique_translation_values(values: list[str]) -> list[str]:
    unique_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = normalize_translation_value(value)
        if normalized is None or normalized in seen:
            continue
        seen.add(normalized)
        unique_values.append(normalized)
    return unique_values


def _updated_message(
    *,
    lemma: str,
    updated_primary_translation: bool,
    added_additional_translations: list[str],
) -> str:
    if updated_primary_translation and added_additional_translations:
        return f"Updated the main translation and added {len(added_additional_translations)} alternative translations for '{lemma}'."
    if updated_primary_translation:
        return f"Updated the main translation for '{lemma}'."
    count = len(added_additional_translations)
    label = "translation" if count == 1 else "translations"
    return f"Added {count} alternative {label} for '{lemma}'."
