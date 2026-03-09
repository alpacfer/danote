from __future__ import annotations

from dataclasses import dataclass
import re

from app.db.repositories.wordbank import LexemeMeaningRecord
from app.services.cor_local import CORLocalEntry
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.runtime import WordbankRuntime

LEGACY_WORDBANK_RESET_REQUIRED_MESSAGE = (
    "Wordbank data is incompatible with meaning sections. "
    "Reset the database from Developer settings and add words again."
)

_LIKELY_ENGLISH_GLOSS_RE = re.compile(r"^[A-Za-z][A-Za-z ',-]*$")


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


@dataclass(frozen=True, slots=True)
class MeaningResolution:
    selected: LexemeMeaningRecord | None
    surface_cor_entry: CORLocalEntry | None
    lemma_cor_entry: CORLocalEntry | None
    cor_lemma_idx: int | None
    gloss: str | None
    pos_tag: str | None
    morphology: str | None
    meaning_key: str


def resolve_non_verb_meaning(
    runtime: WordbankRuntime,
    *,
    lexeme_id: int,
    stored_lemma: str,
    normalized_surface: str,
    normalized_cor_id: str | None,
    preferred_pos_tag: str | None,
    preferred_morphology: str | None,
) -> MeaningResolution | None:
    if is_verb_like_pos_tag(preferred_pos_tag):
        return None

    existing_meanings = runtime.repository.list_lexeme_meanings(lexeme_id)
    surface_form = normalized_surface or stored_lemma
    selected = _resolve_existing_meaning_by_cor_id(
        runtime,
        lexeme_id=lexeme_id,
        normalized_cor_id=normalized_cor_id,
        existing_meanings=existing_meanings,
    )
    surface_cor_entry = _resolve_surface_cor_entry(
        runtime,
        stored_lemma=stored_lemma,
        surface_form=surface_form,
        normalized_cor_id=normalized_cor_id,
        preferred_pos_tag=preferred_pos_tag,
        preferred_lemma_idx=selected.cor_lemma_idx if selected is not None else None,
    )
    cor_lemma_idx = (
        surface_cor_entry.lemma_idx
        if surface_cor_entry is not None
        else selected.cor_lemma_idx if selected is not None else None
    )
    if selected is None:
        selected = _resolve_existing_meaning_by_surface(
            runtime,
            lexeme_id=lexeme_id,
            surface_form=surface_form,
            existing_meanings=existing_meanings,
            cor_lemma_idx=cor_lemma_idx,
        )

    candidate_entries = runtime.cor.cor_local_entries_for_form(
        form=surface_form,
        lemma=stored_lemma,
        preferred_pos_tag=preferred_pos_tag,
    )
    candidate_lemma_idxs = {entry.lemma_idx for entry in candidate_entries}
    if selected is None and len(candidate_lemma_idxs) == 1:
        cor_lemma_idx = next(iter(candidate_lemma_idxs))
        selected = next(
            (item for item in existing_meanings if item.cor_lemma_idx == cor_lemma_idx),
            None,
        )
    if selected is None and len(existing_meanings) > 1:
        selected = _select_existing_meaning_with_gemini(
            runtime,
            surface_form=surface_form,
            stored_lemma=stored_lemma,
            preferred_pos_tag=preferred_pos_tag,
            preferred_morphology=preferred_morphology,
            candidate_entries=candidate_entries,
            existing_meanings=existing_meanings,
        )
    if selected is not None and cor_lemma_idx is None:
        cor_lemma_idx = selected.cor_lemma_idx
    if surface_cor_entry is None and cor_lemma_idx is not None:
        surface_cor_entry = runtime.cor.best_cor_local_entry_for_form(
            form=surface_form,
            lemma=stored_lemma,
            preferred_pos_tag=preferred_pos_tag,
            preferred_lemma_idx=cor_lemma_idx,
        )

    lemma_cor_entry = None
    if cor_lemma_idx is not None:
        lemma_cor_entry = runtime.cor.best_cor_local_lemma_entry(
            lemma_idx=cor_lemma_idx,
            lemma=stored_lemma,
            preferred_pos_tag=preferred_pos_tag or (surface_cor_entry.pos_tag if surface_cor_entry else None),
        )
    if lemma_cor_entry is None and surface_cor_entry is not None and normalize_token(surface_cor_entry.form) == stored_lemma:
        lemma_cor_entry = surface_cor_entry

    gloss_source = (
        (lemma_cor_entry.gloss if lemma_cor_entry is not None else None)
        or (surface_cor_entry.gloss if surface_cor_entry is not None else None)
        or (selected.gloss if selected is not None else None)
    )
    gloss = normalize_token(gloss_source) if gloss_source else None
    pos_tag = (
        preferred_pos_tag
        or (lemma_cor_entry.pos_tag if lemma_cor_entry is not None else None)
        or (surface_cor_entry.pos_tag if surface_cor_entry is not None else None)
        or (selected.pos_tag if selected is not None else None)
    )
    morphology = (
        preferred_morphology
        or (lemma_cor_entry.morphology if lemma_cor_entry is not None else None)
        or (surface_cor_entry.morphology if surface_cor_entry is not None else None)
        or (selected.morphology if selected is not None else None)
    )
    meaning_key = normalize_token(
        gloss
        or (selected.meaning_key if selected is not None else stored_lemma)
    ) or stored_lemma

    return MeaningResolution(
        selected=selected,
        surface_cor_entry=surface_cor_entry,
        lemma_cor_entry=lemma_cor_entry,
        cor_lemma_idx=cor_lemma_idx,
        gloss=gloss,
        pos_tag=pos_tag,
        morphology=morphology,
        meaning_key=meaning_key,
    )


def build_meaning_assignment(record: LexemeMeaningRecord) -> MeaningAssignment:
    return MeaningAssignment(
        id=record.id,
        meaning_key=record.meaning_key,
        gloss=record.gloss,
        english_translation=record.english_translation,
    )


def resolve_meaning_translation(
    runtime: WordbankRuntime,
    *,
    cor_entry: CORLocalEntry | None,
    gloss: str | None,
    lemma_translation: str | None,
) -> str | None:
    normalized_lemma_translation = normalize_token(lemma_translation or "")
    normalized_gloss = normalize_token(gloss or "")
    normalized_translated_gloss = None
    if cor_entry is not None:
        translated_gloss = runtime.cor.lookup_translation_for_cor_gloss(
            entry=cor_entry,
            lemma_translation=lemma_translation,
            cache={},
        )
        normalized_translated_gloss = normalize_token(translated_gloss or "")
    if normalized_lemma_translation:
        return normalized_lemma_translation
    if normalized_translated_gloss:
        return normalized_translated_gloss
    if normalized_gloss:
        return normalized_gloss
    return None


def _is_likely_english_gloss(gloss: str | None) -> bool:
    normalized_gloss = normalize_token(gloss or "")
    if not normalized_gloss:
        return False
    return _LIKELY_ENGLISH_GLOSS_RE.fullmatch(normalized_gloss) is not None


def _resolve_existing_meaning_by_cor_id(
    runtime: WordbankRuntime,
    *,
    lexeme_id: int,
    normalized_cor_id: str | None,
    existing_meanings: list[LexemeMeaningRecord],
) -> LexemeMeaningRecord | None:
    if not normalized_cor_id:
        return None
    linked_surface = runtime.repository.find_surface_form_by_cor_id(normalized_cor_id)
    if linked_surface is None or linked_surface.lexeme_id != lexeme_id or linked_surface.meaning_id is None:
        return None
    return next((item for item in existing_meanings if item.id == linked_surface.meaning_id), None)


def _resolve_surface_cor_entry(
    runtime: WordbankRuntime,
    *,
    stored_lemma: str,
    surface_form: str,
    normalized_cor_id: str | None,
    preferred_pos_tag: str | None,
    preferred_lemma_idx: int | None,
) -> CORLocalEntry | None:
    if normalized_cor_id:
        entry = runtime.cor.cor_local_entry_for_cor_id(cor_id=normalized_cor_id)
        if entry is not None and normalize_token(entry.lemma) == stored_lemma:
            return entry
    return runtime.cor.best_cor_local_entry_for_form(
        form=surface_form,
        lemma=stored_lemma,
        preferred_pos_tag=preferred_pos_tag,
        preferred_lemma_idx=preferred_lemma_idx,
    )


def _resolve_existing_meaning_by_surface(
    runtime: WordbankRuntime,
    *,
    lexeme_id: int,
    surface_form: str,
    existing_meanings: list[LexemeMeaningRecord],
    cor_lemma_idx: int | None,
) -> LexemeMeaningRecord | None:
    if cor_lemma_idx is not None:
        by_cor_lemma_idx = next(
            (item for item in existing_meanings if item.cor_lemma_idx == cor_lemma_idx),
            None,
        )
        return by_cor_lemma_idx

    exact_rows = runtime.repository.find_surface_forms(lexeme_id=lexeme_id, form=surface_form)
    meaning_ids = {row.meaning_id for row in exact_rows if row.meaning_id is not None}
    if len(meaning_ids) != 1:
        return None
    meaning_id = next(iter(meaning_ids))
    return next((item for item in existing_meanings if item.id == meaning_id), None)


def _select_existing_meaning_with_gemini(
    runtime: WordbankRuntime,
    *,
    surface_form: str,
    stored_lemma: str,
    preferred_pos_tag: str | None,
    preferred_morphology: str | None,
    candidate_entries: list[CORLocalEntry],
    existing_meanings: list[LexemeMeaningRecord],
) -> LexemeMeaningRecord | None:
    if not existing_meanings:
        return None
    candidate_glosses = {
        normalize_token(entry.gloss or "")
        for entry in candidate_entries
        if normalize_token(entry.gloss or "")
    }
    gloss = next(iter(candidate_glosses)) if len(candidate_glosses) == 1 else None
    english_translation = None
    if gloss and candidate_entries:
        english_translation = runtime.cor.lookup_translation_for_cor_gloss(
            entry=candidate_entries[0],
            lemma_translation=None,
            cache={},
        )
    selected_id = runtime.translation.select_meaning_section(
        surface_form=surface_form,
        lemma=stored_lemma,
        pos_tag=preferred_pos_tag or (candidate_entries[0].pos_tag if candidate_entries else None),
        morphology=preferred_morphology or (candidate_entries[0].morphology if candidate_entries else None),
        gloss=gloss,
        english_translation=normalize_token(english_translation or "") or None,
        meaning_candidates=existing_meanings,
    )
    if selected_id is None:
        return None
    return next((item for item in existing_meanings if item.id == selected_id), None)
