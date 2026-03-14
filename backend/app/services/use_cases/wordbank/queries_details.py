from __future__ import annotations

import re

from app.api.schemas.v1.wordbank import LemmaDetailsResponse
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.meaning_sections import ensure_wordbank_meaning_compatibility
from app.services.use_cases.wordbank.runtime import WordbankRuntime
from app.services.use_cases.wordbank.verification_records import verification_record_to_schema

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
    verification_records = {
        record.meaning_id: verification_record_to_schema(record)
        for record in runtime.repository.list_verification_records(lexeme.id)
    }
    if lexeme.source != "search":
        return _get_manual_lemma_details(runtime, lexeme, form_rows, meaning_rows, verification_records)

    if not meaning_rows:
        return LemmaDetailsResponse(
            lemma=lexeme.lemma,
            english_translation=lexeme.english_translation,
            pos_tag=lexeme.pos_tag,
            morphology=lexeme.morphology,
            is_sectioned=False,
            verification=verification_records.get(None),
            meaning_sections=[],
            surface_forms=[
                _surface_form_details(
                    form=row.form,
                    pos_tag=row.pos_tag,
                    morphology=row.morphology,
                    lemma=lexeme.lemma,
                    lemma_translation=lexeme.english_translation,
                    gloss=None,
                    has_pronunciation=row.has_pronunciation,
                )
                for row in form_rows
            ],
        )

    section_forms: dict[int, list[LemmaDetailsResponse.SurfaceFormDetails]] = {
        meaning.id: [] for meaning in meaning_rows
    }
    meaning_by_id = {meaning.id: meaning for meaning in meaning_rows}
    for row in form_rows:
        if row.meaning_id is None or row.form == lexeme.lemma:
            continue
        meaning = meaning_by_id.get(row.meaning_id)
        if meaning is None:
            continue
        section_forms[row.meaning_id].append(
            _surface_form_details(
                form=row.form,
                pos_tag=row.pos_tag,
                morphology=row.morphology,
                lemma=lexeme.lemma,
                lemma_translation=meaning.english_translation or lexeme.english_translation,
                gloss=meaning.gloss,
                has_pronunciation=row.has_pronunciation,
            )
        )

    if len(meaning_rows) == 1:
        top_level_translation = meaning_rows[0].english_translation or lexeme.english_translation
        top_level_pos_tag = meaning_rows[0].pos_tag or lexeme.pos_tag
        top_level_morphology = meaning_rows[0].morphology or lexeme.morphology
    else:
        top_level_translation = None
        top_level_pos_tag = None
        top_level_morphology = None

    top_level_surface_forms = _dedupe_surface_form_details(
        [
            _sectioned_lemma_surface_form_details(
                form=row.form,
                pos_tag=row.pos_tag,
                morphology=row.morphology,
                has_pronunciation=row.has_pronunciation,
            )
            for row in form_rows
            if row.form == lexeme.lemma
        ]
    )
    gloss_translation_cache: dict[tuple[str, str, str | None, str | None, str, str | None, str | None], str | None] = {}

    return LemmaDetailsResponse(
        lemma=lexeme.lemma,
        english_translation=top_level_translation,
        pos_tag=top_level_pos_tag,
        morphology=top_level_morphology,
        is_sectioned=True,
        verification=verification_records.get(None),
        meaning_sections=[
            LemmaDetailsResponse.MeaningSection(
                id=meaning.id,
                meaning_key=meaning.meaning_key,
                gloss=meaning.gloss,
                english_translation=meaning.english_translation,
                gloss_translation=_meaning_gloss_translation(
                    runtime,
                    lexeme_lemma=lexeme.lemma,
                    lexeme_pos_tag=lexeme.pos_tag,
                    meaning=meaning,
                    cache=gloss_translation_cache,
                ),
                pos_tag=meaning.pos_tag,
                morphology=meaning.morphology,
                verification=verification_records.get(meaning.id),
                surface_forms=section_forms.get(meaning.id, []),
            )
            for meaning in meaning_rows
        ],
        surface_forms=top_level_surface_forms,
    )


def _get_manual_lemma_details(runtime: WordbankRuntime, lexeme, form_rows, meaning_rows, verification_records) -> LemmaDetailsResponse:
    if not meaning_rows:
        return LemmaDetailsResponse(
            lemma=lexeme.lemma,
            english_translation=lexeme.english_translation,
            pos_tag=lexeme.pos_tag,
            morphology=lexeme.morphology,
            is_sectioned=False,
            verification=verification_records.get(None),
            meaning_sections=[],
            surface_forms=[
                _manual_surface_form_details(
                    runtime,
                    lexeme=lexeme,
                    form_row=row,
                    meaning=None,
                )
                for row in form_rows
            ],
        )

    meaning_by_id = {meaning.id: meaning for meaning in meaning_rows}
    section_forms: dict[int, list[LemmaDetailsResponse.SurfaceFormDetails]] = {
        meaning.id: [] for meaning in meaning_rows
    }
    for row in form_rows:
        if row.meaning_id is None or row.form == lexeme.lemma:
            continue
        meaning = meaning_by_id.get(row.meaning_id)
        if meaning is None:
            continue
        section_forms[row.meaning_id].append(
            _manual_surface_form_details(
                runtime,
                lexeme=lexeme,
                form_row=row,
                meaning=meaning,
            )
        )

    if len(meaning_rows) == 1:
        top_level_translation = meaning_rows[0].english_translation or lexeme.english_translation
        top_level_pos_tag = meaning_rows[0].pos_tag or lexeme.pos_tag
        top_level_morphology = meaning_rows[0].morphology or lexeme.morphology
    else:
        top_level_translation = None
        top_level_pos_tag = None
        top_level_morphology = None

    gloss_translation_cache: dict[tuple[str, str, str | None, str | None, str, str | None, str | None], str | None] = {}
    top_level_surface_forms = _dedupe_surface_form_details(
        [
            _manual_sectioned_lemma_surface_form_details(
                runtime,
                lexeme=lexeme,
                form_row=row,
                meaning=meaning_by_id.get(row.meaning_id) if row.meaning_id is not None else None,
            )
            for row in form_rows
            if row.form == lexeme.lemma
        ]
    )
    return LemmaDetailsResponse(
        lemma=lexeme.lemma,
        english_translation=top_level_translation,
        pos_tag=top_level_pos_tag,
        morphology=top_level_morphology,
        is_sectioned=True,
        verification=verification_records.get(None),
        meaning_sections=[
            LemmaDetailsResponse.MeaningSection(
                id=meaning.id,
                meaning_key=meaning.meaning_key,
                gloss=meaning.gloss,
                english_translation=meaning.english_translation,
                gloss_translation=_meaning_gloss_translation(
                    runtime,
                    lexeme_lemma=lexeme.lemma,
                    lexeme_pos_tag=lexeme.pos_tag,
                    meaning=meaning,
                    cache=gloss_translation_cache,
                ),
                pos_tag=meaning.pos_tag,
                morphology=meaning.morphology,
                verification=verification_records.get(meaning.id),
                surface_forms=section_forms.get(meaning.id, []),
            )
            for meaning in meaning_rows
        ],
        surface_forms=top_level_surface_forms,
    )


def _surface_form_details(
    *,
    form: str,
    pos_tag: str | None,
    morphology: str | None,
    lemma: str,
    lemma_translation: str | None,
    gloss: str | None,
    has_pronunciation: bool,
) -> LemmaDetailsResponse.SurfaceFormDetails:
    return LemmaDetailsResponse.SurfaceFormDetails(
        form=form,
        pos_tag=pos_tag,
        morphology=morphology,
        lemma=lemma,
        lemma_translation=lemma_translation,
        gloss=gloss,
        gloss_translation=None,
        gram_raw=None,
        has_pronunciation=has_pronunciation,
    )


def _manual_surface_form_details(runtime: WordbankRuntime, *, lexeme, form_row, meaning) -> LemmaDetailsResponse.SurfaceFormDetails:
    cor_entry = _resolve_cor_entry(runtime, lexeme=lexeme, form_row=form_row, meaning=meaning)
    gloss = cor_entry.gloss if cor_entry is not None else (meaning.gloss if meaning is not None else None)
    lemma_translation = (
        meaning.english_translation if meaning is not None else lexeme.english_translation
    )
    return LemmaDetailsResponse.SurfaceFormDetails(
        form=form_row.form,
        pos_tag=form_row.pos_tag,
        morphology=form_row.morphology,
        lemma=lexeme.lemma,
        lemma_translation=lemma_translation,
        gloss=gloss,
        gloss_translation=_gloss_translation(
            runtime,
            cor_entry=cor_entry,
            gloss=gloss,
            lemma_translation=lemma_translation,
        ),
        gram_raw=cor_entry.gram_raw if cor_entry is not None else None,
        has_pronunciation=form_row.has_pronunciation,
    )


def _sectioned_lemma_surface_form_details(
    *,
    form: str,
    pos_tag: str | None,
    morphology: str | None,
    has_pronunciation: bool,
) -> LemmaDetailsResponse.SurfaceFormDetails:
    return LemmaDetailsResponse.SurfaceFormDetails(
        form=form,
        pos_tag=pos_tag,
        morphology=morphology,
        has_pronunciation=has_pronunciation,
    )


def _manual_sectioned_lemma_surface_form_details(
    runtime: WordbankRuntime,
    *,
    lexeme,
    form_row,
    meaning,
) -> LemmaDetailsResponse.SurfaceFormDetails:
    cor_entry = None
    if meaning is not None and meaning.cor_lemma_idx is not None:
        cor_entry = runtime.cor.best_cor_local_lemma_entry(
            lemma_idx=meaning.cor_lemma_idx,
            lemma=lexeme.lemma,
            preferred_pos_tag=meaning.pos_tag or lexeme.pos_tag,
        )
    if cor_entry is None:
        cor_entry = _resolve_cor_entry(runtime, lexeme=lexeme, form_row=form_row, meaning=meaning)
    return LemmaDetailsResponse.SurfaceFormDetails(
        form=form_row.form,
        pos_tag=cor_entry.pos_tag if cor_entry is not None else form_row.pos_tag,
        morphology=cor_entry.morphology if cor_entry is not None else form_row.morphology,
        gram_raw=cor_entry.gram_raw if cor_entry is not None else None,
        has_pronunciation=form_row.has_pronunciation,
    )


def _dedupe_surface_form_details(
    forms: list[LemmaDetailsResponse.SurfaceFormDetails],
) -> list[LemmaDetailsResponse.SurfaceFormDetails]:
    deduped: dict[str, LemmaDetailsResponse.SurfaceFormDetails] = {}
    for form in forms:
        existing = deduped.get(form.form)
        if existing is None or _surface_form_detail_priority(form) > _surface_form_detail_priority(existing):
            deduped[form.form] = form
    return list(deduped.values())


def _surface_form_detail_priority(
    detail: LemmaDetailsResponse.SurfaceFormDetails,
) -> tuple[int, int, int, int, int, int, int]:
    return (
        int(detail.has_pronunciation),
        int(bool(detail.gram_raw)),
        int(bool(detail.gloss_translation)),
        int(bool(detail.gloss)),
        int(bool(detail.lemma_translation)),
        int(bool(detail.morphology)),
        int(bool(detail.pos_tag)),
    )


def _resolve_cor_entry(runtime: WordbankRuntime, *, lexeme, form_row, meaning):
    if form_row.cor_id:
        cor_entry = runtime.cor.cor_local_entry_for_cor_id(cor_id=form_row.cor_id)
        if cor_entry is not None:
            return cor_entry
    return runtime.cor.best_cor_local_entry_for_form(
        form=form_row.form,
        lemma=lexeme.lemma,
        preferred_pos_tag=form_row.pos_tag,
        preferred_lemma_idx=meaning.cor_lemma_idx if meaning is not None else None,
    )


def _meaning_gloss_translation(
    runtime: WordbankRuntime,
    *,
    lexeme_lemma: str,
    lexeme_pos_tag: str | None,
    meaning,
    cache: dict[tuple[str, str, str | None, str | None, str, str | None, str | None], str | None],
) -> str | None:
    if _is_likely_english_gloss(meaning.gloss):
        return normalize_token(meaning.gloss or "") or None
    if meaning.cor_lemma_idx is None:
        return None
    cor_entry = runtime.cor.best_cor_local_lemma_entry(
        lemma_idx=meaning.cor_lemma_idx,
        lemma=lexeme_lemma,
        preferred_pos_tag=meaning.pos_tag or lexeme_pos_tag,
    )
    return _gloss_translation(
        runtime,
        cor_entry=cor_entry,
        gloss=meaning.gloss,
        lemma_translation=meaning.english_translation,
        cache=cache,
    )


def _gloss_translation(
    runtime: WordbankRuntime,
    *,
    cor_entry,
    gloss: str | None,
    lemma_translation: str | None,
    cache: dict[tuple[str, str, str | None, str | None, str, str | None, str | None], str | None] | None = None,
) -> str | None:
    if _is_likely_english_gloss(gloss):
        return normalize_token(gloss or "") or None
    if cor_entry is None:
        return None
    return runtime.cor.lookup_translation_for_cor_gloss(
        entry=cor_entry,
        lemma_translation=lemma_translation,
        cache=cache if cache is not None else {},
    )


def _is_likely_english_gloss(gloss: str | None) -> bool:
    normalized_gloss = normalize_token(gloss or "")
    if not normalized_gloss:
        return False
    return _LIKELY_ENGLISH_GLOSS_RE.fullmatch(normalized_gloss) is not None
