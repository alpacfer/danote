from __future__ import annotations

from app.api.schemas.v1.sentencebank import SentenceTokenCard
from app.api.schemas.v1.wordbank import LemmaDetailsResponse, VerificationResult
from app.db.repositories import SentencebankRepository
from app.services.token_classifier import normalize_token
from app.services.use_cases.static_builtin_words import (
    ensure_static_builtin_sense,
    static_builtin_reference_links,
    static_builtin_senses_for_token,
)
from app.services.use_cases.wordbank.gloss_translations import (
    gloss_translation as resolve_gloss_translation,
)
from app.services.use_cases.wordbank.gloss_translations import (
    is_likely_english_gloss,
    meaning_gloss_translation,
)
from app.services.use_cases.wordbank.meaning_sections import ensure_wordbank_meaning_compatibility
from app.services.use_cases.wordbank.runtime import WordbankRuntime
from app.services.use_cases.wordbank.static_details import static_builtin_lemma_details
from app.services.use_cases.wordbank.surface_form_ordering import order_surface_form_details
from app.services.use_cases.wordbank.verification_categories import category_labels_by_scope
from app.services.use_cases.wordbank.verification_records import verification_record_to_schema


def get_lemma_details(runtime: WordbankRuntime, lemma: str) -> LemmaDetailsResponse:
    ensure_wordbank_meaning_compatibility(runtime)
    normalized_lemma = normalize_token(lemma)
    if not normalized_lemma:
        raise ValueError("lemma is required")

    lexeme = runtime.repository.get_lexeme(normalized_lemma)
    if lexeme is None:
        static_details = static_builtin_lemma_details(lemma, normalized_lemma)
        if static_details is not None:
            return static_details
        raise LookupError(f"Lemma '{normalized_lemma}' was not found")
    static_senses = static_builtin_senses_for_token(normalized_lemma)
    if lexeme.source == "static" and static_senses and _needs_static_builtin_upgrade(runtime, lexeme.id, static_senses):
        ensure_static_builtin_sense(runtime, static_senses[0])
        lexeme = runtime.repository.get_lexeme(normalized_lemma)
        if lexeme is None:
            raise LookupError(f"Lemma '{normalized_lemma}' was not found")

    form_rows = runtime.repository.list_surface_forms(lexeme.id)
    meaning_rows = runtime.repository.list_lexeme_meanings(lexeme.id)
    root_additional_translations = _translation_values(
        runtime.repository.list_additional_translations(lexeme_id=lexeme.id, meaning_id=None),
        primary_translation=lexeme.english_translation,
    )
    related_words = runtime.related_words.build_related_words_section(
        owner_lexeme_id=lexeme.id,
        stored_lemma=lexeme.lemma,
    )
    linked_sentences = _linked_sentences(runtime, lexeme.lemma)
    verification_records = {
        (
            record.meaning_id,
            normalize_token(record.stored_surface_form or "") or None,
        ): verification_record_to_schema(record)
        for record in runtime.repository.list_verification_records(lexeme.id)
    }
    category_assignments = category_labels_by_scope(runtime.repository, lexeme_id=lexeme.id)
    if lexeme.source != "search":
        return _get_manual_lemma_details(
            runtime,
            lexeme,
            form_rows,
            meaning_rows,
            verification_records,
            category_assignments,
            related_words,
            linked_sentences,
            root_additional_translations,
        )

    if not meaning_rows:
        return LemmaDetailsResponse(
            lemma=lexeme.lemma,
            dictionary_status=lexeme.dictionary_status,
            english_translation=lexeme.english_translation,
            additional_translations=root_additional_translations,
            pos_tag=lexeme.pos_tag,
            morphology=lexeme.morphology,
            is_sectioned=False,
            categories=category_assignments.get(None, []),
            reference_links=_schema_reference_links(
                static_builtin_reference_links(
                    lexeme.lemma,
                    meaning_key=None,
                    pos_tag=lexeme.pos_tag,
                )
            ),
            verification=verification_records.get((None, None)),
            meaning_sections=[],
            related_words=related_words,
            linked_sentences=linked_sentences,
            surface_forms=order_surface_form_details(
                [
                    _surface_form_details(
                        runtime,
                        form=row.form,
                        pos_tag=row.pos_tag,
                        morphology=row.morphology,
                        lemma=lexeme.lemma,
                        lemma_translation=lexeme.english_translation,
                        gloss=None,
                        meaning=None,
                        has_pronunciation=row.has_pronunciation,
                        verification=verification_records.get((None, normalize_token(row.form))),
                    )
                    for row in form_rows
                ]
            ),
        )

    section_forms: dict[int, list[LemmaDetailsResponse.SurfaceFormDetails]] = {
        meaning.id: [] for meaning in meaning_rows
    }
    meaning_by_id = {meaning.id: meaning for meaning in meaning_rows}
    for row in form_rows:
        if row.meaning_id is None:
            continue
        meaning = meaning_by_id.get(row.meaning_id)
        if meaning is None:
            continue
        if normalize_token(row.form) == normalized_lemma:
            continue
        section_forms[row.meaning_id].append(
            _surface_form_details(
                runtime,
                form=row.form,
                pos_tag=row.pos_tag,
                morphology=row.morphology,
                lemma=lexeme.lemma,
                lemma_translation=meaning.english_translation or lexeme.english_translation,
                gloss=meaning.gloss,
                meaning=meaning,
                has_pronunciation=row.has_pronunciation,
                verification=verification_records.get((row.meaning_id, normalize_token(row.form))),
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

    top_level_surface_forms = order_surface_form_details(_dedupe_surface_form_details(
        [
            _sectioned_lemma_surface_form_details(
                runtime,
                lexeme=lexeme,
                meaning=meaning_by_id.get(row.meaning_id) if row.meaning_id is not None else None,
                form=row.form,
                pos_tag=row.pos_tag,
                morphology=row.morphology,
                has_pronunciation=row.has_pronunciation,
            )
            for row in form_rows
            if row.form == lexeme.lemma
        ]
    ))
    gloss_translation_cache: dict[tuple[str, str, str | None, str | None, str, str | None, str | None], str | None] = {}

    return LemmaDetailsResponse(
        lemma=lexeme.lemma,
        dictionary_status=lexeme.dictionary_status,
        english_translation=top_level_translation,
        additional_translations=root_additional_translations,
        pos_tag=top_level_pos_tag,
        morphology=top_level_morphology,
        is_sectioned=True,
        categories=category_assignments.get(None, []),
        verification=verification_records.get((None, None)),
        meaning_sections=[
            LemmaDetailsResponse.MeaningSection(
                id=meaning.id,
                meaning_key=meaning.meaning_key,
                dictionary_status=meaning.dictionary_status,
                gloss=meaning.gloss,
                english_translation=meaning.english_translation,
                additional_translations=_translation_values(
                    runtime.repository.list_additional_translations(lexeme_id=lexeme.id, meaning_id=meaning.id),
                    primary_translation=meaning.english_translation or top_level_translation,
                ),
                gloss_translation=_meaning_gloss_translation(
                    runtime,
                    lexeme_lemma=lexeme.lemma,
                    lexeme_pos_tag=lexeme.pos_tag,
                    meaning=meaning,
                    cache=gloss_translation_cache,
                ),
                pos_tag=meaning.pos_tag,
                morphology=meaning.morphology,
                gram_raw=_meaning_gram_raw(runtime, lexeme=lexeme, meaning=meaning),
                categories=category_assignments.get(meaning.id, []),
                reference_links=_schema_reference_links(
                    static_builtin_reference_links(
                        lexeme.lemma,
                        meaning_key=meaning.meaning_key,
                        pos_tag=meaning.pos_tag,
                    )
                ),
                verification=verification_records.get((meaning.id, None)),
                surface_forms=order_surface_form_details(section_forms.get(meaning.id, [])),
            )
            for meaning in meaning_rows
        ],
        surface_forms=top_level_surface_forms,
        related_words=related_words,
        linked_sentences=linked_sentences,
    )


def _get_manual_lemma_details(
    runtime: WordbankRuntime,
    lexeme,
    form_rows,
    meaning_rows,
    verification_records,
    category_assignments: dict[int | None, list[str]],
    related_words: LemmaDetailsResponse.RelatedWordsSection,
    linked_sentences: list[LemmaDetailsResponse.LinkedSentence],
    root_additional_translations: list[str],
) -> LemmaDetailsResponse:
    normalized_lemma = normalize_token(lexeme.lemma)
    if not meaning_rows:
        return LemmaDetailsResponse(
            lemma=lexeme.lemma,
            dictionary_status=lexeme.dictionary_status,
            english_translation=lexeme.english_translation,
            additional_translations=root_additional_translations,
            pos_tag=lexeme.pos_tag,
            morphology=lexeme.morphology,
            is_sectioned=False,
            categories=category_assignments.get(None, []),
            reference_links=_schema_reference_links(
                static_builtin_reference_links(
                    lexeme.lemma,
                    meaning_key=None,
                    pos_tag=lexeme.pos_tag,
                )
            ),
            verification=verification_records.get((None, None)),
            meaning_sections=[],
            related_words=related_words,
            linked_sentences=linked_sentences,
            surface_forms=order_surface_form_details(
                [
                    _manual_surface_form_details(
                        runtime,
                        lexeme=lexeme,
                        form_row=row,
                        meaning=None,
                        verification=verification_records.get((None, normalize_token(row.form))),
                    )
                    for row in form_rows
                ]
            ),
        )

    meaning_by_id = {meaning.id: meaning for meaning in meaning_rows}
    section_forms: dict[int, list[LemmaDetailsResponse.SurfaceFormDetails]] = {
        meaning.id: [] for meaning in meaning_rows
    }
    for row in form_rows:
        if row.meaning_id is None:
            continue
        meaning = meaning_by_id.get(row.meaning_id)
        if meaning is None:
            continue
        if normalize_token(row.form) == normalized_lemma:
            continue
        section_forms[row.meaning_id].append(
            _manual_surface_form_details(
                runtime,
                lexeme=lexeme,
                form_row=row,
                meaning=meaning,
                verification=verification_records.get((row.meaning_id, normalize_token(row.form))),
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
    top_level_surface_forms = order_surface_form_details(_dedupe_surface_form_details(
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
    ))
    return LemmaDetailsResponse(
        lemma=lexeme.lemma,
        dictionary_status=lexeme.dictionary_status,
        english_translation=top_level_translation,
        additional_translations=root_additional_translations,
        pos_tag=top_level_pos_tag,
        morphology=top_level_morphology,
        is_sectioned=True,
        categories=category_assignments.get(None, []),
        verification=verification_records.get((None, None)),
        meaning_sections=[
            LemmaDetailsResponse.MeaningSection(
                id=meaning.id,
                meaning_key=meaning.meaning_key,
                dictionary_status=meaning.dictionary_status,
                gloss=meaning.gloss,
                english_translation=meaning.english_translation,
                additional_translations=_translation_values(
                    runtime.repository.list_additional_translations(lexeme_id=lexeme.id, meaning_id=meaning.id),
                    primary_translation=meaning.english_translation or top_level_translation,
                ),
                gloss_translation=_meaning_gloss_translation(
                    runtime,
                    lexeme_lemma=lexeme.lemma,
                    lexeme_pos_tag=lexeme.pos_tag,
                    meaning=meaning,
                    cache=gloss_translation_cache,
                ),
                pos_tag=meaning.pos_tag,
                morphology=meaning.morphology,
                gram_raw=_meaning_gram_raw(runtime, lexeme=lexeme, meaning=meaning),
                categories=category_assignments.get(meaning.id, []),
                reference_links=_schema_reference_links(
                    static_builtin_reference_links(
                        lexeme.lemma,
                        meaning_key=meaning.meaning_key,
                        pos_tag=meaning.pos_tag,
                    )
                ),
                verification=verification_records.get((meaning.id, None)),
                surface_forms=order_surface_form_details(section_forms.get(meaning.id, [])),
            )
            for meaning in meaning_rows
        ],
        surface_forms=top_level_surface_forms,
        related_words=related_words,
        linked_sentences=linked_sentences,
    )


def _linked_sentences(runtime: WordbankRuntime, lemma: str) -> list[LemmaDetailsResponse.LinkedSentence]:
    rows = SentencebankRepository(runtime.db_path).list_linked_sentences_for_lemma(lemma)
    return [
        LemmaDetailsResponse.LinkedSentence(
            id=row.id,
            source_text=row.source_text,
            english_translation=row.english_translation,
            created_at=row.created_at,
            matched_token_indexes=list(row.matched_token_indexes),
            tokens=[
                SentenceTokenCard(
                    token_index=token.token_index,
                    surface_form=token.surface_form,
                    stored_lemma=token.stored_lemma,
                    lexeme_id=token.lexeme_id,
                    meaning_id=token.meaning_id,
                    pos_tag=token.pos_tag,
                    morphology=token.morphology,
                    gloss=token.gloss,
                    english_translation=token.english_translation,
                    gloss_translation=token.gloss_translation,
                )
                for token in row.tokens
            ],
        )
        for row in rows
    ]


def _needs_static_builtin_upgrade(runtime: WordbankRuntime, lexeme_id: int, static_senses) -> bool:
    meaning_rows = runtime.repository.list_lexeme_meanings(lexeme_id)
    if len(static_senses) <= 1:
        return False
    existing_keys = {meaning.meaning_key for meaning in meaning_rows}
    expected_keys = {sense.meaning_key for sense in static_senses}
    return not expected_keys.issubset(existing_keys)


def _schema_reference_links(reference_links):
    return [
        LemmaDetailsResponse.ReferenceLink(
            page_id=link.page_id,
            page_title=link.page_title,
            tab_id=link.tab_id,
            tab_title=link.tab_title,
            sentinel=link.sentinel,
        )
        for link in reference_links
    ]


def _surface_form_details(
    runtime: WordbankRuntime,
    *,
    form: str,
    pos_tag: str | None,
    morphology: str | None,
    lemma: str,
    lemma_translation: str | None,
    gloss: str | None,
    meaning,
    has_pronunciation: bool,
    verification: VerificationResult | None = None,
) -> LemmaDetailsResponse.SurfaceFormDetails:
    cor_entry = _best_cor_entry_for_saved_form(
        runtime,
        lemma=lemma,
        form=form,
        pos_tag=pos_tag,
        meaning=meaning,
    )
    return LemmaDetailsResponse.SurfaceFormDetails(
        form=form,
        pos_tag=pos_tag,
        morphology=morphology,
        lemma=lemma,
        lemma_translation=lemma_translation,
        gloss=gloss,
        gloss_translation=None,
        gram_raw=cor_entry.gram_raw if cor_entry is not None else None,
        has_pronunciation=has_pronunciation,
        verification=verification,
    )


def _translation_values(records, *, primary_translation: str | None) -> list[str]:
    primary = normalize_token(primary_translation or "")
    values: list[str] = []
    seen: set[str] = set()
    for record in records:
        normalized = normalize_token(record.english_translation)
        if not normalized or normalized == primary or normalized in seen:
            continue
        seen.add(normalized)
        values.append(record.english_translation)
    return values


def _manual_surface_form_details(
    runtime: WordbankRuntime,
    *,
    lexeme,
    form_row,
    meaning,
    verification: VerificationResult | None = None,
) -> LemmaDetailsResponse.SurfaceFormDetails:
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
        verification=verification,
    )


def _sectioned_lemma_surface_form_details(
    runtime: WordbankRuntime,
    *,
    lexeme,
    meaning,
    form: str,
    pos_tag: str | None,
    morphology: str | None,
    has_pronunciation: bool,
) -> LemmaDetailsResponse.SurfaceFormDetails:
    cor_entry = _best_cor_entry_for_saved_form(
        runtime,
        lemma=lexeme.lemma,
        form=form,
        pos_tag=pos_tag,
        meaning=meaning,
    )
    return LemmaDetailsResponse.SurfaceFormDetails(
        form=form,
        pos_tag=pos_tag,
        morphology=morphology,
        gram_raw=cor_entry.gram_raw if cor_entry is not None else None,
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
    preferred_entry = runtime.cor.best_cor_local_entry_for_form(
        form=form_row.form,
        lemma=lexeme.lemma,
        preferred_pos_tag=form_row.pos_tag,
        preferred_lemma_idx=meaning.cor_lemma_idx if meaning is not None else None,
    )
    if form_row.cor_id:
        cor_entry = runtime.cor.cor_local_entry_for_cor_id(cor_id=form_row.cor_id)
        if cor_entry is not None and preferred_entry is None:
            return cor_entry
    return preferred_entry


def _best_cor_entry_for_saved_form(
    runtime: WordbankRuntime,
    *,
    lemma: str,
    form: str,
    pos_tag: str | None,
    meaning,
):
    if meaning is not None and meaning.cor_lemma_idx is not None:
        cor_entry = runtime.cor.best_cor_local_lemma_entry(
            lemma_idx=meaning.cor_lemma_idx,
            lemma=lemma,
            preferred_pos_tag=meaning.pos_tag or pos_tag,
        )
        if cor_entry is not None and normalize_token(cor_entry.form) == normalize_token(form):
            return cor_entry
    return runtime.cor.best_cor_local_entry_for_form(
        form=form,
        lemma=lemma,
        preferred_pos_tag=pos_tag,
        preferred_lemma_idx=meaning.cor_lemma_idx if meaning is not None else None,
    )


def _meaning_gram_raw(runtime: WordbankRuntime, *, lexeme, meaning) -> str | None:
    if meaning.cor_lemma_idx is None:
        return None
    cor_entry = runtime.cor.best_cor_local_lemma_entry(
        lemma_idx=meaning.cor_lemma_idx,
        lemma=lexeme.lemma,
        preferred_pos_tag=meaning.pos_tag or lexeme.pos_tag,
    )
    return cor_entry.gram_raw if cor_entry is not None else None


def _meaning_gloss_translation(
    runtime: WordbankRuntime,
    *,
    lexeme_lemma: str,
    lexeme_pos_tag: str | None,
    meaning,
    cache: dict[tuple[str, str, str | None, str | None, str, str | None, str | None], str | None],
) -> str | None:
    return meaning_gloss_translation(
        runtime,
        lexeme_lemma=lexeme_lemma,
        lexeme_pos_tag=lexeme_pos_tag,
        meaning_gloss=meaning.gloss,
        meaning_translation=meaning.english_translation,
        meaning_pos_tag=meaning.pos_tag,
        cor_lemma_idx=meaning.cor_lemma_idx,
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
    return resolve_gloss_translation(
        runtime,
        cor_entry=cor_entry,
        gloss=gloss,
        lemma_translation=lemma_translation,
        cache=cache,
    )


def _is_likely_english_gloss(gloss: str | None) -> bool:
    return is_likely_english_gloss(gloss)
