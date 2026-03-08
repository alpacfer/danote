from __future__ import annotations

from dataclasses import dataclass

from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.runtime import WordbankRuntime

LEGACY_WORDBANK_RESET_REQUIRED_MESSAGE = (
    "Wordbank data is incompatible with meaning sections. "
    "Reset the database from Developer settings and add words again."
)


def is_verb_like_pos_tag(pos_tag: str | None) -> bool:
    return (pos_tag or "").upper() in {"VERB", "AUX"}


def ensure_wordbank_meaning_compatibility(runtime: WordbankRuntime) -> None:
    if runtime.repository.has_non_verb_forms_without_meaning():
        raise RuntimeError(LEGACY_WORDBANK_RESET_REQUIRED_MESSAGE)


@dataclass(frozen=True, slots=True)
class MeaningAssignment:
    id: int
    meaning_key: str
    gloss: str | None
    english_translation: str | None


def assign_non_verb_meaning(
    runtime: WordbankRuntime,
    *,
    lexeme_id: int,
    stored_lemma: str,
    normalized_surface: str,
    normalized_cor_id: str | None,
    pos_tag: str | None,
    morphology: str | None,
    lemma_translation: str | None,
    surface_translation: str | None,
) -> MeaningAssignment | None:
    if is_verb_like_pos_tag(pos_tag):
        return None

    existing_meanings = runtime.repository.list_lexeme_meanings(lexeme_id)
    cor_entry = _resolve_cor_entry(
        runtime,
        stored_lemma=stored_lemma,
        normalized_surface=normalized_surface,
        normalized_cor_id=normalized_cor_id,
        pos_tag=pos_tag,
    )
    gloss = normalize_token(cor_entry.gloss or "") or None if cor_entry is not None else None
    english_translation = _resolve_meaning_translation(
        runtime,
        cor_entry=cor_entry,
        gloss=gloss,
        lemma_translation=lemma_translation,
        surface_translation=surface_translation,
    )
    meaning_key = normalize_token(gloss or english_translation or stored_lemma)
    if not meaning_key:
        meaning_key = stored_lemma

    selected = next((item for item in existing_meanings if item.meaning_key == meaning_key), None)
    if selected is None and len(existing_meanings) > 1:
        selected_id = runtime.translation.select_meaning_section(
            surface_form=normalized_surface or stored_lemma,
            lemma=stored_lemma,
            pos_tag=pos_tag,
            morphology=morphology,
            gloss=gloss,
            english_translation=english_translation,
            meaning_candidates=existing_meanings,
        )
        if selected_id is not None:
            selected = next((item for item in existing_meanings if item.id == selected_id), None)

    selected_record, _inserted = runtime.repository.upsert_lexeme_meaning(
        lexeme_id=lexeme_id,
        meaning_key=selected.meaning_key if selected is not None else meaning_key,
        gloss=gloss,
        english_translation=english_translation,
        pos_tag=pos_tag,
        morphology=morphology,
    )
    for form in _forms_to_assign(stored_lemma=stored_lemma, normalized_surface=normalized_surface):
        runtime.repository.assign_surface_form_meaning_if_unset(
            lexeme_id=lexeme_id,
            form=form,
            meaning_id=selected_record.id,
        )
    return MeaningAssignment(
        id=selected_record.id,
        meaning_key=selected_record.meaning_key,
        gloss=selected_record.gloss,
        english_translation=selected_record.english_translation,
    )


def _forms_to_assign(*, stored_lemma: str, normalized_surface: str) -> set[str]:
    values = {stored_lemma}
    if normalized_surface:
        values.add(normalized_surface)
    return {value for value in values if value}


def _resolve_cor_entry(
    runtime: WordbankRuntime,
    *,
    stored_lemma: str,
    normalized_surface: str,
    normalized_cor_id: str | None,
    pos_tag: str | None,
):
    if normalized_cor_id:
        entry = runtime.cor.cor_local_entry_for_cor_id(cor_id=normalized_cor_id)
        if entry is not None and normalize_token(entry.lemma) == stored_lemma:
            return entry
    return runtime.cor.best_cor_local_entry_for_form(
        form=normalized_surface or stored_lemma,
        lemma=stored_lemma,
        preferred_pos_tag=pos_tag,
    )


def _resolve_meaning_translation(
    runtime: WordbankRuntime,
    *,
    cor_entry,
    gloss: str | None,
    lemma_translation: str | None,
    surface_translation: str | None,
) -> str | None:
    if cor_entry is not None:
        translated_gloss = runtime.cor.lookup_translation_for_cor_gloss(
            entry=cor_entry,
            lemma_translation=lemma_translation,
            cache={},
        )
        normalized_translated_gloss = normalize_token(translated_gloss or "")
        if normalized_translated_gloss:
            return normalized_translated_gloss
    if gloss:
        return gloss
    if lemma_translation:
        return normalize_token(lemma_translation)
    if surface_translation:
        return normalize_token(surface_translation)
    return None
