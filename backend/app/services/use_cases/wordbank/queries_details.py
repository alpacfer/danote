from __future__ import annotations

from app.api.schemas.v1.wordbank import LemmaDetailsResponse
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.meaning_sections import (
    LEGACY_WORDBANK_RESET_REQUIRED_MESSAGE,
    ensure_wordbank_meaning_compatibility,
    is_verb_like_pos_tag,
)
from app.services.use_cases.wordbank.runtime import WordbankRuntime


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

    lemma_pos_tag = lexeme.pos_tag
    lemma_morphology = lexeme.morphology
    if lemma_pos_tag is None and lemma_morphology is None:
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
    gloss_translation_cache: dict[
        tuple[str, str, str | None, str | None, str, str | None, str | None],
        str | None,
    ] = {}
    detailed_forms: list[tuple[int | None, LemmaDetailsResponse.SurfaceFormDetails]] = []

    for row in form_rows:
        pos_tag = row.pos_tag
        morphology = row.morphology
        if pos_tag is None and morphology is None:
            pos_tag, morphology = extracted_forms.get(row.form, (None, None))
            _store_surface_form_metadata(
                runtime,
                lexeme_id=lexeme.id,
                form=row.form,
                pos_tag=pos_tag,
                morphology=morphology,
            )
        cor_local_entry = runtime.cor.best_cor_local_entry_for_form(
            form=row.form,
            lemma=lexeme.lemma,
            preferred_pos_tag=pos_tag,
        )
        gloss = cor_local_entry.gloss if cor_local_entry is not None else None
        gloss_translation = (
            runtime.cor.lookup_translation_for_cor_gloss(
                entry=cor_local_entry,
                lemma_translation=lexeme.english_translation,
                cache=gloss_translation_cache,
            )
            if cor_local_entry is not None
            else None
        )
        detailed_forms.append(
            (
                row.meaning_id,
                LemmaDetailsResponse.SurfaceFormDetails(
                    form=row.form,
                    english_translation=row.english_translation,
                    pos_tag=pos_tag,
                    morphology=morphology,
                    lemma=lexeme.lemma,
                    lemma_translation=lexeme.english_translation,
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

    meaning_sections = [
        LemmaDetailsResponse.MeaningSection(
            id=meaning.id,
            meaning_key=meaning.meaning_key,
            gloss=meaning.gloss,
            english_translation=meaning.english_translation,
            pos_tag=meaning.pos_tag,
            morphology=meaning.morphology,
            surface_forms=details_by_meaning_id.get(meaning.id, []),
        )
        for meaning in meaning_rows
    ]

    return LemmaDetailsResponse(
        lemma=lexeme.lemma,
        english_translation=lexeme.english_translation,
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
    lexeme_id: int,
    form: str,
    pos_tag: str | None,
    morphology: str | None,
) -> None:
    runtime.repository.update_surface_form_metadata(
        lexeme_id=lexeme_id,
        form=form,
        pos_tag=pos_tag,
        morphology=morphology,
    )
