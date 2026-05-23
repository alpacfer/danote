from __future__ import annotations

from typing import Literal

from app.api.schemas.v1.sentencebank import (
    SentenceSearchPreviewResponse,
    SentenceVerificationErrorItem,
    VerifySentenceResponse,
)
from app.api.schemas.v1.wordbank import CORSearchVariant
from app.services.sentence_verification import (
    SentenceVerificationResult,
    SentenceVerificationService,
)
from app.services.translation import TranslationService
from app.services.use_cases.sentencebank_text import (
    heuristic_detect_language,
    normalize_query_language,
    normalize_sentence_text_without_terminal_period,
    preserve_leading_letter_case,
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

    local_entry = wordbank_use_case.runtime.cor.lookup_mwe_lemma(lemma)
    variants: list[CORSearchVariant] = []
    for index, meaning in enumerate(meanings):
        pos_tag = meaning.pos_tag or verification.mwe_pos_tag
        translation = meaning.english_translation or verification.mwe_english_translation
        gloss = meaning.gloss
        sense_suffix = _meaning_id_suffix(meaning, fallback_index=index)
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
            ))
    return variants


def _meaning_id_suffix(meaning, *, fallback_index: int) -> str:
    """Pick a stable suffix for the synthesized cor_id of an MWE meaning.

    Prefer Gemini's meaning_key; fall back to the english_translation (snake);
    last resort is the position. Always normalized to uppercase ASCII-safe form
    so it slots into a cor_id-like string.
    """
    candidate = (meaning.meaning_key or meaning.english_translation or meaning.gloss or "").strip()
    if not candidate:
        return f"SENSE_{fallback_index}"
    # Compact + safe for use inside a cor_id-like identifier.
    normalized = "_".join(candidate.upper().split())
    safe = "".join(ch for ch in normalized if ch.isalnum() or ch in {"_", "-"})
    return safe or f"SENSE_{fallback_index}"


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
) -> SentenceSearchPreviewResponse:
    if fast:
        return build_sentence_search_preview_fast(
            normalized_query=normalized_query,
            translation_service=translation_service,
            wordbank_use_case=wordbank_use_case,
        )

    initial_verification = verify_sentence_result(
        source_text=normalized_query,
        sentence_verification_service=sentence_verification_service,
    )
    query_language = initial_verification.language
    if query_language == "unknown":
        query_language = detect_query_language(
            source_text=normalized_query,
            translation_service=translation_service,
        )

    if query_language == "en":
        english_for_translation = (
            preserve_leading_letter_case(normalized_query, initial_verification.corrected_text)
            or normalized_query
        )
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
        return SentenceSearchPreviewResponse(
            status="ready",
            query_language="en",
            source_text=translated_danish,
            english_translation=english_for_translation,
            is_valid=True,
            errors=[],
            message=None,
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


def build_sentence_search_preview_fast(
    *,
    normalized_query: str,
    translation_service: TranslationService | None,
    wordbank_use_case: WordbankUseCase | None,
) -> SentenceSearchPreviewResponse:
    query_language = detect_query_language(
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
                return preserve_leading_letter_case(source_text, payload.english_translation)
        except Exception:
            pass
    if translation_service is None:
        return None
    try:
        translated = translation_service.translate_da_to_en(source_text)
        if not isinstance(translated, str):
            return None
        cleaned = " ".join(translated.strip().split()) or None
        return preserve_leading_letter_case(source_text, cleaned)
    except Exception:
        return None


def lookup_reverse_translation(
    *,
    source_text: str,
    translation_service: TranslationService | None,
) -> str | None:
    if translation_service is None:
        return None
    translate_en_to_da = getattr(translation_service, "translate_en_to_da", None)
    if not callable(translate_en_to_da):
        return None
    try:
        translated = translate_en_to_da(source_text)
        return (
            normalize_sentence_text_without_terminal_period(translated)
            if isinstance(translated, str) and translated.strip()
            else None
        )
    except Exception:
        return None


def detect_query_language(
    *,
    source_text: str,
    translation_service: TranslationService | None,
) -> Literal["da", "en", "unknown"]:
    if translation_service is None:
        return "unknown"
    detect_source_language = getattr(translation_service, "detect_source_language", None)
    if not callable(detect_source_language):
        return "unknown"
    try:
        return normalize_query_language(detect_source_language(source_text))
    except Exception:
        return "unknown"


def verify_sentence_result(
    *,
    source_text: str,
    sentence_verification_service: SentenceVerificationService | None,
) -> SentenceVerificationResult:
    if sentence_verification_service is None:
        return SentenceVerificationResult(
            is_valid=True,
            errors=[],
            corrected_text=None,
            language="unknown",
        )
    try:
        return sentence_verification_service.verify_sentence(source_text)
    except Exception:
        return SentenceVerificationResult(
            is_valid=True,
            errors=[],
            corrected_text=None,
            language="unknown",
        )


def translation_provider_name(translation_service: TranslationService | None) -> str:
    provider = getattr(translation_service, "provider", None)
    if isinstance(provider, str):
        cleaned = provider.strip().lower()
        if cleaned:
            return cleaned
    return "translation"
