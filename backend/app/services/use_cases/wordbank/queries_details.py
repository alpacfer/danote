from __future__ import annotations

import re

from app.api.schemas.v1.wordbank import LemmaDetailsResponse
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.meaning_sections import (
    LEGACY_WORDBANK_RESET_REQUIRED_MESSAGE,
    ensure_wordbank_meaning_compatibility,
    is_verb_like_pos_tag,
)
from app.services.use_cases.wordbank.runtime import WordbankRuntime

_LIKELY_ENGLISH_GLOSS_RE = re.compile(r"^[A-Za-z][A-Za-z ',-]*$")


def get_lemma_details(runtime: WordbankRuntime, lemma: str) -> LemmaDetailsResponse:
    ensure_wordbank_meaning_compatibility(runtime)
    normalized_lemma = normalize_token(lemma)
    if not normalized_lemma:
        raise ValueError("lemma is required")

    lexeme = runtime.repository.get_lexeme(normalized_lemma)
    if lexeme is None:
        raise LookupError(f"Lemma '{normalized_lemma}' was not found")
    form_rows = runtime.repository.list_surface_forms(lexeme.id)
    meaning_rows = runtime.repository.list_lexeme_meanings(lexeme.id)
    meaning_by_id = {row.id: row for row in meaning_rows}

    lemma_pos_tag = lexeme.pos_tag
    lemma_morphology = lexeme.morphology
    if not meaning_rows and lemma_pos_tag is None and lemma_morphology is None:
        lemma_pos_tag, lemma_morphology = runtime.nlp.extract_pos_and_morphology(lexeme.lemma)
        _store_lexeme_metadata(
            runtime,
            lexeme_id=lexeme.id,
            pos_tag=lemma_pos_tag,
            morphology=lemma_morphology,
        )

    uncached_forms = [
        row.form
        for row in form_rows
        if row.pos_tag is None and row.morphology is None
    ]
    extracted_forms = runtime.nlp.extract_pos_and_morphology_batch(uncached_forms)
    detailed_forms: list[tuple[int | None, LemmaDetailsResponse.SurfaceFormDetails]] = []
    gloss_translation_cache: dict[tuple[str, str, str | None, str | None, str, str | None, str | None], str | None] = {}

    for row in form_rows:
        pos_tag = row.pos_tag
        morphology = row.morphology
        if pos_tag is None and morphology is None:
            pos_tag, morphology = extracted_forms.get(row.form, (None, None))
            _store_surface_form_metadata(
                runtime,
                surface_form_id=row.id,
                pos_tag=pos_tag,
                morphology=morphology,
            )
        meaning = meaning_by_id.get(row.meaning_id) if row.meaning_id is not None else None
        cor_local_entry = (
            runtime.cor.cor_local_entry_for_cor_id(cor_id=row.cor_id)
            if row.cor_id is not None
            else None
        )
        if cor_local_entry is None:
            cor_local_entry = (
                runtime.cor.best_cor_local_entry_for_form(
                    form=row.form,
                    lemma=lexeme.lemma,
                    preferred_pos_tag=pos_tag,
                    preferred_lemma_idx=meaning.cor_lemma_idx if meaning is not None else None,
                )
                if meaning is not None
                else runtime.cor.best_cor_local_entry_for_form(
                    form=row.form,
                    lemma=lexeme.lemma,
                    preferred_pos_tag=pos_tag,
                )
            )
        gloss = cor_local_entry.gloss if cor_local_entry is not None else None
        lemma_translation = (
            meaning.english_translation
            if meaning is not None
            else lexeme.english_translation
        )
        gloss_translation = None
        if _is_likely_english_gloss(gloss):
            gloss_translation = normalize_token(gloss or "")
        elif cor_local_entry is not None:
            gloss_translation = runtime.cor.lookup_translation_for_cor_gloss(
                entry=cor_local_entry,
                lemma_translation=lemma_translation,
                cache=gloss_translation_cache,
            )
        detailed_forms.append(
            (
                row.meaning_id,
                LemmaDetailsResponse.SurfaceFormDetails(
                    form=row.form,
                    pos_tag=pos_tag,
                    morphology=morphology,
                    lemma=lexeme.lemma,
                    lemma_translation=lemma_translation,
                    gloss=gloss,
                    gloss_translation=gloss_translation,
                    gram_raw=cor_local_entry.gram_raw if cor_local_entry is not None else None,
                    has_pronunciation=row.has_pronunciation,
                ),
            )
        )

    if is_verb_like_pos_tag(lemma_pos_tag):
        return LemmaDetailsResponse(
            lemma=lexeme.lemma,
            english_translation=lexeme.english_translation,
            pos_tag=lemma_pos_tag,
            morphology=lemma_morphology,
            is_sectioned=False,
            meaning_sections=[],
            surface_forms=[detail for _meaning_id, detail in detailed_forms],
        )

    if any(meaning_id is None for meaning_id, _detail in detailed_forms):
        raise RuntimeError(LEGACY_WORDBANK_RESET_REQUIRED_MESSAGE)

    details_by_meaning_id: dict[int, list[LemmaDetailsResponse.SurfaceFormDetails]] = {}
    for meaning_id, detail in detailed_forms:
        if meaning_id is None:
            continue
        details_by_meaning_id.setdefault(meaning_id, [])
        if detail.form != lexeme.lemma:
            details_by_meaning_id[meaning_id].append(detail)

    meaning_gloss_translations = {
        meaning.id: _resolve_meaning_gloss_translation(
            runtime,
            lexeme_lemma=lexeme.lemma,
            lexeme_pos_tag=lexeme.pos_tag,
            meaning=meaning,
            details=details_by_meaning_id.get(meaning.id, []),
            gloss_translation_cache=gloss_translation_cache,
        )
        for meaning in meaning_rows
    }

    if len(meaning_rows) == 1:
        lemma_pos_tag = meaning_rows[0].pos_tag or lemma_pos_tag
        lemma_morphology = meaning_rows[0].morphology or lemma_morphology
        lemma_translation = meaning_rows[0].english_translation or lexeme.english_translation
    else:
        lemma_pos_tag = None
        lemma_morphology = None
        lemma_translation = None

    meaning_sections = [
        LemmaDetailsResponse.MeaningSection(
            id=meaning.id,
            meaning_key=meaning.meaning_key,
            gloss=meaning.gloss,
            english_translation=meaning.english_translation,
            gloss_translation=meaning_gloss_translations.get(meaning.id),
            pos_tag=meaning.pos_tag,
            morphology=meaning.morphology,
            surface_forms=details_by_meaning_id.get(meaning.id, []),
        )
        for meaning in meaning_rows
    ]

    return LemmaDetailsResponse(
        lemma=lexeme.lemma,
        english_translation=lemma_translation,
        pos_tag=lemma_pos_tag,
        morphology=lemma_morphology,
        is_sectioned=True,
        meaning_sections=meaning_sections,
        surface_forms=[],
    )


def _store_lexeme_metadata(
    runtime: WordbankRuntime,
    *,
    lexeme_id: int,
    pos_tag: str | None,
    morphology: str | None,
) -> None:
    runtime.repository.update_lexeme_metadata(
        lexeme_id=lexeme_id,
        pos_tag=pos_tag,
        morphology=morphology,
    )


def _store_surface_form_metadata(
    runtime: WordbankRuntime,
    *,
    surface_form_id: int,
    pos_tag: str | None,
    morphology: str | None,
) -> None:
    runtime.repository.update_surface_form_metadata(
        surface_form_id=surface_form_id,
        pos_tag=pos_tag,
        morphology=morphology,
    )


def _is_likely_english_gloss(gloss: str | None) -> bool:
    normalized_gloss = normalize_token(gloss or "")
    if not normalized_gloss:
        return False
    return _LIKELY_ENGLISH_GLOSS_RE.fullmatch(normalized_gloss) is not None


def _resolve_meaning_gloss_translation(
    runtime: WordbankRuntime,
    *,
    lexeme_lemma: str,
    lexeme_pos_tag: str | None,
    meaning,
    details: list[LemmaDetailsResponse.SurfaceFormDetails],
    gloss_translation_cache: dict[tuple[str, str, str | None, str | None, str, str | None, str | None], str | None],
) -> str | None:
    existing = next((detail.gloss_translation for detail in details if detail.gloss_translation), None)
    if existing:
        return existing

    if _is_likely_english_gloss(meaning.gloss):
        return normalize_token(meaning.gloss or "")

    if meaning.cor_lemma_idx is None:
        return None

    cor_local_entry = runtime.cor.best_cor_local_lemma_entry(
        lemma_idx=meaning.cor_lemma_idx,
        lemma=lexeme_lemma,
        preferred_pos_tag=meaning.pos_tag or lexeme_pos_tag,
    )
    if cor_local_entry is None:
        return None

    return runtime.cor.lookup_translation_for_cor_gloss(
        entry=cor_local_entry,
        lemma_translation=meaning.english_translation,
        cache=gloss_translation_cache,
    )
