from __future__ import annotations

from typing import Literal

from app.api.schemas.v1.sentencebank import (
    SentenceSearchPreviewResponse,
    SentenceVerificationErrorItem,
    VerifySentenceResponse,
)
from app.api.schemas.v1.wordbank import CORSearchVariant
from app.services.sentence_verification import (
    SentenceMWEMeaning,
    SentenceVerificationError,
    SentenceVerificationErrorSpan,
    SentenceVerificationResult,
    SentenceVerificationService,
)
from app.services.translation import TranslationService
from app.services.use_cases.sentencebank_text import (
    blocked_preview,
    capitalize_sentence_translation,
    curated_mwe_meanings,
    detect_query_language_for_preview,
    heuristic_danish_correction,
    heuristic_detect_language,
    looks_mixed_language,
    lookup_reverse_translation,
    meaning_id_suffix,
    normalize_query_language,
    normalize_sentence_text_without_terminal_period,
    preserve_leading_letter_case,
    translation_provider_name,
    verify_sentence_result,
)
from app.services.use_cases.wordbank import WordbankUseCase


def _build_mwe_meaning_variants(
    *,
    wordbank_use_case: WordbankUseCase,
    verification: SentenceVerificationResult,
) -> list[CORSearchVariant]:
    """Build one CORSearchVariant per distinct sense of an MWE lemma.

    - Always returns at least one variant when the verification flags an MWE (the
      single mwe_* fields supply the fallback).
    - For COR-known MWE lemmas we use the local entry as the template and clone it
      per sense, varying only gloss / english_translation / cor_id so saving each
      card creates a separate `lexeme_meanings` row keyed by gloss.
    - For non-COR MWEs we synthesize a `GENERATED_MWE:` cor_id per sense, scoped
      by meaning_key (or the english_translation) so the frontend treats them as
      distinct save targets.
    """
    lemma = verification.mwe_lemma
    if not lemma:
        return []

    # Synthesize a single back-compat meaning when Gemini didn't enumerate.
    meanings = list(verification.mwe_meanings)
    if not meanings and (verification.mwe_gloss or verification.mwe_english_translation):
        from app.services.sentence_verification import SentenceMWEMeaning  # local import to avoid cycle
        meanings = [SentenceMWEMeaning(
            gloss=verification.mwe_gloss,
            english_translation=verification.mwe_english_translation,
            pos_tag=verification.mwe_pos_tag,
            meaning_key=None,
        )]
    if not meanings:
        return []

    try:
        if " " in lemma:
            local_entry = wordbank_use_case.runtime.cor.lookup_mwe_lemma(lemma)
        else:
            candidates = wordbank_use_case.runtime.cor.lookup_form(lemma)
            local_entry = None
            if candidates:
                for cand in candidates:
                    if cand.lemma == lemma:
                        local_entry = cand
                        break
                if not local_entry:
                    local_entry = candidates[0]
    except Exception:
        local_entry = None
    variants: list[CORSearchVariant] = []
    for index, meaning in enumerate(meanings):
        pos_tag = meaning.pos_tag or verification.mwe_pos_tag
        translation = meaning.english_translation or verification.mwe_english_translation
        gloss = meaning.gloss
        sense_suffix = meaning_id_suffix(meaning, fallback_index=index)
        if local_entry is not None:
            variants.append(CORSearchVariant(
                # Disambiguate per-sense cor_id so each card is a distinct save target.
                # The first sense keeps the bare COR id for back-compat with single-meaning callers.
                cor_id=local_entry.cor_id if index == 0 else f"{local_entry.cor_id}::{sense_suffix}",
                form=local_entry.form,
                lemma=local_entry.lemma,
                gloss=gloss or local_entry.gloss,
                gloss_translation=None,
                gram_raw=local_entry.gram_raw,
                norm=local_entry.norm or "N",
                lemma_idx=local_entry.lemma_idx,
                gram_code=local_entry.gram_code,
                variation=local_entry.variation,
                pos_tag=pos_tag or local_entry.pos_tag,
                morphology=local_entry.morphology,
                features=local_entry.features,
                extra_tags=local_entry.extra_tags,
                lemma_translation=translation,
                saveable_translation=translation,
                lemma_translation_provider="gemini",
                lemma_translation_status="gemini",
                lemma_translation_reason=None,
                meaning_key=meaning.meaning_key,
            ))
        else:
            variants.append(CORSearchVariant(
                cor_id=f"GENERATED_MWE:{lemma.upper()}::{sense_suffix}",
                form=lemma,
                lemma=lemma,
                gloss=gloss,
                gloss_translation=None,
                gram_raw="",
                norm="N",
                lemma_idx=0,
                gram_code=0,
                variation=0,
                pos_tag=pos_tag or "VERB",
                morphology=None,
                features={},
                extra_tags=[],
                lemma_translation=translation,
                saveable_translation=translation,
                lemma_translation_provider="gemini",
                lemma_translation_status="gemini",
                lemma_translation_reason=None,
                dictionary_status="generated_non_cor",
                meaning_key=meaning.meaning_key,
            ))

    from app.db.migrations import get_connection
    from app.services.token_classifier import normalize_token

    try:
        with get_connection(wordbank_use_case.runtime.db_path) as conn:
            saved_rows = conn.execute(
                """
                SELECT
                    lm.id AS meaning_id,
                    lm.meaning_key AS meaning_key,
                    lm.english_translation AS english_translation,
                    lm.gloss AS gloss,
                    lm.pos_tag AS pos_tag
                FROM lexeme_meanings lm
                JOIN lexemes l ON l.id = lm.lexeme_id
                WHERE l.owner_user_id = ? AND l.lemma = ?
                """,
                (wordbank_use_case.runtime.owner_user_id, lemma),
            ).fetchall()
    except Exception:
        saved_rows = []

    if saved_rows:
        def clean_translation(t: str | None) -> str:
            if not t:
                return ""
            val = " ".join(t.strip().lower().split())
            if val.startswith("to "):
                return val[3:].strip()
            return val

        stamped_variants = []
        for variant in variants:
            matched_meaning_id = None
            var_key = clean_translation(variant.meaning_key)
            var_trans = clean_translation(variant.lemma_translation)
            var_gloss = clean_translation(variant.gloss)

            for row in saved_rows:
                row_key = clean_translation(row["meaning_key"])
                row_trans = clean_translation(row["english_translation"])
                row_gloss = clean_translation(row["gloss"])

                # Check exact or normalized matches
                if var_key and row_key and var_key == row_key:
                    matched_meaning_id = row["meaning_id"]
                    break
                if var_trans and row_trans and var_trans == row_trans:
                    matched_meaning_id = row["meaning_id"]
                    break
                if var_gloss and row_gloss and var_gloss == row_gloss:
                    matched_meaning_id = row["meaning_id"]
                    break

            if matched_meaning_id is not None:
                stamped_variants.append(variant.model_copy(update={"saved_meaning_id": matched_meaning_id}))
            else:
                stamped_variants.append(variant)
        variants = stamped_variants

    return variants


def build_verify_sentence_response(
    *,
    normalized_text: str,
    sentence_verification_service: SentenceVerificationService | None,
) -> VerifySentenceResponse:
    if sentence_verification_service is None:
        return VerifySentenceResponse(is_valid=True, errors=[], corrected_text=None, language="unknown")
    result = sentence_verification_service.verify_sentence(normalized_text)
    return VerifySentenceResponse(
        is_valid=result.is_valid,
        errors=[
            SentenceVerificationErrorItem(start=error.start, end=error.end, message=error.message)
            for error in result.errors
        ],
        corrected_text=result.corrected_text,
        language=result.language,
    )


def build_sentence_search_preview(
    *,
    normalized_query: str,
    translation_service: TranslationService | None,
    wordbank_use_case: WordbankUseCase | None,
    sentence_verification_service: SentenceVerificationService | None,
    fast: bool,
    language_mode: Literal["da", "en"] | None = None,
) -> SentenceSearchPreviewResponse:
    if fast:
        return build_sentence_search_preview_fast(
            normalized_query=normalized_query,
            translation_service=translation_service,
            wordbank_use_case=wordbank_use_case,
            language_mode=language_mode,
        )

    if language_mode == "en":
        return _english_sentence_preview(
            normalized_query=normalized_query,
            translation_service=translation_service,
            wordbank_use_case=wordbank_use_case,
            sentence_verification_service=sentence_verification_service,
        )

    try:
        initial_verification = verify_sentence_result(
            source_text=normalized_query,
            sentence_verification_service=sentence_verification_service,
        )
    except SentenceVerificationError:
        heuristic_correction = heuristic_danish_correction(normalized_query)
        if heuristic_correction is not None:
            initial_verification = heuristic_correction
        elif looks_mixed_language(normalized_query):
            return blocked_preview(
                query_language=detect_query_language_for_preview(
                    source_text=normalized_query,
                    translation_service=translation_service,
                ),
                message="This looks like mixed Danish and English. Search a Danish or English sentence.",
            )
        else:
            fallback_verification = _with_deterministic_mwe(
                SentenceVerificationResult(
                    is_valid=True,
                    errors=[],
                    corrected_text=None,
                    language=detect_query_language_for_preview(
                        source_text=normalized_query,
                        translation_service=translation_service,
                    ),
                ),
                source_text=normalized_query,
                wordbank_use_case=wordbank_use_case,
                translation_service=translation_service,
            )
            if fallback_verification.is_multi_word_expression:
                initial_verification = fallback_verification
            else:
                return blocked_preview(
                    query_language=fallback_verification.language,
                    message="Could not verify this sentence. Please try again.",
                )
    else:
        heuristic_correction = heuristic_danish_correction(normalized_query)
        if heuristic_correction is not None and initial_verification.is_valid and not initial_verification.corrected_text:
            initial_verification = heuristic_correction
    query_language = initial_verification.language
    if language_mode == "da":
        query_language = "da"
    if query_language == "unknown":
        query_language = detect_query_language_for_preview(
            source_text=normalized_query,
            translation_service=translation_service,
        )

    if looks_mixed_language(normalized_query) and not initial_verification.corrected_text:
        return blocked_preview(
            query_language=query_language,
            message="This looks like mixed Danish and English. Search a Danish or English sentence.",
        )

    if query_language == "en":
        return _english_sentence_preview(
            normalized_query=normalized_query,
            translation_service=translation_service,
            wordbank_use_case=wordbank_use_case,
            sentence_verification_service=sentence_verification_service,
            corrected_text=initial_verification.corrected_text,
        )

    initial_verification = _with_deterministic_mwe(
        initial_verification,
        source_text=initial_verification.corrected_text or normalized_query,
        wordbank_use_case=wordbank_use_case,
        translation_service=translation_service,
    )
    final_source_text = initial_verification.corrected_text or normalized_query

    mwe_meanings_variants: list[CORSearchVariant] = []
    mwe_cor_match: CORSearchVariant | None = None
    if wordbank_use_case is not None and initial_verification.is_multi_word_expression and initial_verification.mwe_lemma:
        mwe_meanings_variants = _build_mwe_meaning_variants(
            wordbank_use_case=wordbank_use_case,
            verification=initial_verification,
        )
        # Back-compat: the first meaning doubles as the single mwe_cor_match.
        mwe_cor_match = mwe_meanings_variants[0] if mwe_meanings_variants else None

    return SentenceSearchPreviewResponse(
        status="ready",
        query_language=query_language,
        source_text=final_source_text,
        english_translation=lookup_phrase_translation(
            source_text=final_source_text,
            translation_service=translation_service,
            wordbank_use_case=wordbank_use_case,
        ),
        is_valid=initial_verification.is_valid,
        errors=[
            SentenceVerificationErrorItem(start=error.start, end=error.end, message=error.message)
            for error in initial_verification.errors
        ],
        message=None,
        is_multi_word_expression=initial_verification.is_multi_word_expression,
        mwe_lemma=initial_verification.mwe_lemma,
        mwe_pos_tag=initial_verification.mwe_pos_tag,
        mwe_gloss=initial_verification.mwe_gloss,
        mwe_english_translation=initial_verification.mwe_english_translation,
        mwe_cor_match=mwe_cor_match,
        mwe_meanings=mwe_meanings_variants,
    )


def _english_sentence_preview(
    *,
    normalized_query: str,
    translation_service: TranslationService | None,
    wordbank_use_case: WordbankUseCase | None,
    sentence_verification_service: SentenceVerificationService | None,
    corrected_text: str | None = None,
) -> SentenceSearchPreviewResponse:
    english_for_translation = preserve_leading_letter_case(normalized_query, corrected_text) or normalized_query
    translated_danish = lookup_reverse_translation(
        source_text=english_for_translation,
        translation_service=translation_service,
    )
    if not translated_danish:
        return SentenceSearchPreviewResponse(
            status="blocked",
            query_language="en",
            source_text=None,
            english_translation=None,
            is_valid=False,
            errors=[],
            message="Could not translate this English sentence to Danish.",
        )

    try:
        danish_verification = verify_sentence_result(
            source_text=translated_danish,
            sentence_verification_service=sentence_verification_service,
        )
    except SentenceVerificationError:
        return blocked_preview(
            query_language="en",
            message="Could not verify the Danish translation. Please try again.",
        )
    danish_verification = _with_deterministic_mwe(
        danish_verification,
        source_text=translated_danish,
        wordbank_use_case=wordbank_use_case,
        translation_service=translation_service,
        english_query=english_for_translation,
    )

    final_danish_text = danish_verification.corrected_text or translated_danish
    mwe_meanings_variants: list[CORSearchVariant] = []
    mwe_cor_match: CORSearchVariant | None = None
    if wordbank_use_case is not None and danish_verification.is_multi_word_expression and danish_verification.mwe_lemma:
        mwe_meanings_variants = _build_mwe_meaning_variants(
            wordbank_use_case=wordbank_use_case,
            verification=danish_verification,
        )
        mwe_cor_match = mwe_meanings_variants[0] if mwe_meanings_variants else None

    return SentenceSearchPreviewResponse(
        status="ready",
        query_language="en",
        source_text=final_danish_text,
        english_translation=english_for_translation,
        is_valid=danish_verification.is_valid,
        errors=[
            SentenceVerificationErrorItem(start=error.start, end=error.end, message=error.message)
            for error in danish_verification.errors
        ],
        message=None,
        is_multi_word_expression=danish_verification.is_multi_word_expression,
        mwe_lemma=danish_verification.mwe_lemma,
        mwe_pos_tag=danish_verification.mwe_pos_tag,
        mwe_gloss=danish_verification.mwe_gloss,
        mwe_english_translation=danish_verification.mwe_english_translation,
        mwe_cor_match=mwe_cor_match,
        mwe_meanings=mwe_meanings_variants,
    )


def build_sentence_search_preview_fast(
    *,
    normalized_query: str,
    translation_service: TranslationService | None,
    wordbank_use_case: WordbankUseCase | None,
    language_mode: Literal["da", "en"] | None = None,
) -> SentenceSearchPreviewResponse:
    if looks_mixed_language(normalized_query):
        return SentenceSearchPreviewResponse(
            status="blocked",
            query_language="unknown",
            source_text=None,
            english_translation=None,
            is_valid=False,
            errors=[],
            message="This looks like mixed Danish and English. Search a Danish or English sentence.",
        )

    query_language = language_mode or detect_query_language_for_preview(
        source_text=normalized_query,
        translation_service=translation_service,
    )
    if query_language == "unknown":
        query_language = heuristic_detect_language(normalized_query)
    if query_language == "en":
        translated_danish = lookup_reverse_translation(
            source_text=normalized_query,
            translation_service=translation_service,
        )
        if not translated_danish:
            return SentenceSearchPreviewResponse(
                status="blocked",
                query_language="en",
                source_text=None,
                english_translation=None,
                is_valid=True,
                errors=[],
                message=None,
            )
        return SentenceSearchPreviewResponse(
            status="preview",
            query_language="en",
            source_text=translated_danish,
            english_translation=normalized_query,
            is_valid=True,
            errors=[],
            message=None,
        )

    effective_language: Literal["da", "en", "unknown"] = "da" if query_language == "da" else "unknown"
    return SentenceSearchPreviewResponse(
        status="preview",
        query_language=effective_language,
        source_text=normalized_query,
        english_translation=lookup_phrase_translation(
            source_text=normalized_query,
            translation_service=translation_service,
            wordbank_use_case=wordbank_use_case,
        ),
        is_valid=True,
        errors=[],
        message=None,
    )


def lookup_phrase_translation(
    *,
    source_text: str,
    translation_service: TranslationService | None,
    wordbank_use_case: WordbankUseCase | None,
) -> str | None:
    if wordbank_use_case is not None:
        try:
            payload = wordbank_use_case.generate_phrase_translation(source_text)
            if payload.english_translation:
                return capitalize_sentence_translation(
                    preserve_leading_letter_case(source_text, payload.english_translation)
                )
        except Exception:
            pass
    if translation_service is None:
        return None
    try:
        translated = translation_service.translate_da_to_en(source_text)
        if not isinstance(translated, str):
            return None
        cleaned = " ".join(translated.strip().split()) or None
        return capitalize_sentence_translation(preserve_leading_letter_case(source_text, cleaned))
    except Exception:
        return None


def _with_deterministic_mwe(
    verification: SentenceVerificationResult,
    *,
    source_text: str,
    wordbank_use_case: WordbankUseCase | None,
    translation_service: TranslationService | None,
    english_query: str | None = None,
) -> SentenceVerificationResult:
    if verification.is_multi_word_expression or wordbank_use_case is None:
        return verification
    normalized = normalize_sentence_text_without_terminal_period(source_text)
    
    is_danish_mwe = " " in normalized
    is_english_mwe = (
        english_query is not None
        and " " in normalize_sentence_text_without_terminal_period(english_query)
        and len(normalize_sentence_text_without_terminal_period(english_query).split()) <= 4
    )
    
    if not is_danish_mwe and not is_english_mwe:
        return verification
        
    try:
        if is_danish_mwe:
            local_entry = wordbank_use_case.runtime.cor.lookup_mwe_lemma(normalized)
        else:
            candidates = wordbank_use_case.runtime.cor.lookup_form(normalized)
            local_entry = None
            if candidates:
                for cand in candidates:
                    if cand.lemma == normalized:
                        local_entry = cand
                        break
                if not local_entry:
                    local_entry = candidates[0]
    except Exception:
        local_entry = None
        
    curated_meanings = [] if local_entry is not None else curated_mwe_meanings(normalized)
    
    if local_entry is None and not curated_meanings:
        if is_danish_mwe or not is_english_mwe:
            return verification
            
    english_translation = english_query or lookup_phrase_translation(
        source_text=normalized,
        translation_service=translation_service,
        wordbank_use_case=None,
    )
    
    lemma = local_entry.lemma if local_entry is not None else normalized
    pos_tag = local_entry.pos_tag if local_entry is not None else ("NOUN" if is_english_mwe else "VERB")
    gloss = local_entry.gloss if local_entry is not None else (curated_meanings[0].gloss if curated_meanings else None)
    
    meanings = curated_meanings or [
        SentenceMWEMeaning(
            gloss=gloss,
            english_translation=english_translation,
            pos_tag=pos_tag or "VERB",
            meaning_key=gloss or english_translation or lemma,
        )
    ]
    return SentenceVerificationResult(
        is_valid=verification.is_valid,
        errors=verification.errors,
        corrected_text=verification.corrected_text,
        language="da" if verification.language == "unknown" else verification.language,
        is_multi_word_expression=True,
        mwe_lemma=lemma,
        mwe_pos_tag=pos_tag or "VERB",
        mwe_gloss=gloss,
        mwe_english_translation=english_translation or meanings[0].english_translation,
        mwe_meanings=meanings,
    )
