from __future__ import annotations

import httpx

from app.services.gemini_translation import (
    AlternativeTranslationsInput,
    GeminiTranslationError,
    MeaningSectionCandidateInput,
    MeaningSectionSelectionInput,
)
from app.services.use_cases.wordbank.collaborators.translation_models import (
    AlternativeTranslationsLookupResult,
)
from app.services.use_cases.wordbank.collaborators.translation_failures import (
    ProviderFailureReason,
)
from app.services.use_cases.wordbank.collaborators.translation_helpers import (
    contextual_provider_name,
    log_provider_failure,
    normalize_translation_value,
)


def find_alternative_translations(
    collaborator,
    *,
    surface_form: str,
    lemma: str,
    pos_tag: str | None,
    morphology: str | None,
    gloss: str | None,
    current_translation: str | None,
    existing_additional_translations: list[str],
) -> AlternativeTranslationsLookupResult:
    if collaborator._gemini_word_translation_service is None:
        return AlternativeTranslationsLookupResult(
            primary_translation=None,
            alternative_translations=[],
            provider=None,
        )
    finder = getattr(collaborator._gemini_word_translation_service, "find_alternative_translations", None)
    if not callable(finder):
        return AlternativeTranslationsLookupResult(
            primary_translation=None,
            alternative_translations=[],
            provider=None,
        )

    payload = AlternativeTranslationsInput(
        surface_form=surface_form,
        lemma=lemma,
        pos_tag=pos_tag,
        morphology=morphology,
        gloss=normalize_translation_value(gloss),
        current_translation=normalize_translation_value(current_translation),
        existing_additional_translations=[
            normalized
            for value in existing_additional_translations
            if (normalized := normalize_translation_value(value)) is not None
        ],
    )
    try:
        result = finder(payload)
    except (GeminiTranslationError, httpx.HTTPError, TimeoutError, ValueError, TypeError) as exc:
        log_provider_failure(
            logger=collaborator._logger,
            provider=contextual_provider_name(collaborator._gemini_word_translation_service),
            operation="find_alternative_translations",
            reason=ProviderFailureReason.PROVIDER,
            retryable=False,
            exc=exc,
        )
        return AlternativeTranslationsLookupResult(
            primary_translation=None,
            alternative_translations=[],
            provider=contextual_provider_name(collaborator._gemini_word_translation_service),
        )
    return AlternativeTranslationsLookupResult(
        primary_translation=normalize_translation_value(result.primary_translation),
        alternative_translations=[
            normalized
            for value in result.alternative_translations
            if (normalized := normalize_translation_value(value)) is not None
        ],
        provider=contextual_provider_name(collaborator._gemini_word_translation_service),
    )


def select_meaning_section(
    collaborator,
    *,
    surface_form: str,
    lemma: str,
    pos_tag: str | None,
    morphology: str | None,
    gloss: str | None,
    english_translation: str | None,
    sentence_context: str | None = None,
    meaning_candidates: list[object],
) -> int | None:
    if collaborator._gemini_word_translation_service is None or not meaning_candidates:
        return None
    selector = getattr(collaborator._gemini_word_translation_service, "select_meaning_section", None)
    if not callable(selector):
        return None

    candidate_payloads: list[MeaningSectionCandidateInput] = []
    valid_ids: set[int] = set()
    for candidate in meaning_candidates:
        candidate_id = getattr(candidate, "id", None)
        if not isinstance(candidate_id, int):
            continue
        valid_ids.add(candidate_id)
        candidate_payloads.append(
            MeaningSectionCandidateInput(
                id=candidate_id,
                lemma=str(getattr(candidate, "lemma", "")).strip(),
                meaning_key=str(getattr(candidate, "meaning_key", "")),
                cor_lemma_idx=getattr(candidate, "cor_lemma_idx", None),
                gloss=normalize_translation_value(getattr(candidate, "gloss", None)),
                english_translation=normalize_translation_value(
                    getattr(candidate, "english_translation", None)
                ),
                pos_tag=getattr(candidate, "pos_tag", None),
                morphology=getattr(candidate, "morphology", None),
            )
        )
    if not candidate_payloads:
        return None

    payload = MeaningSectionSelectionInput(
        surface_form=surface_form,
        lemma=lemma,
        pos_tag=pos_tag,
        morphology=morphology,
        gloss=normalize_translation_value(gloss),
        english_translation=normalize_translation_value(english_translation),
        sentence_context=" ".join(sentence_context.strip().split())
        if isinstance(sentence_context, str) and sentence_context.strip()
        else None,
        meaning_candidates=candidate_payloads,
    )
    try:
        selected = selector(payload)
    except (GeminiTranslationError, httpx.HTTPError, TimeoutError, ValueError, TypeError) as exc:
        log_provider_failure(
            logger=collaborator._logger,
            provider=contextual_provider_name(collaborator._gemini_word_translation_service),
            operation="select_meaning_section",
            reason=ProviderFailureReason.PARSE,
            retryable=False,
            exc=exc,
        )
        return None
    if not isinstance(selected, int) or selected not in valid_ids:
        return None
    return selected


def select_meaning_sections_batch(collaborator, payloads: list[dict[str, object]]) -> list[int | None]:
    if collaborator._gemini_word_translation_service is None or not payloads:
        return [None] * len(payloads)
    selector = getattr(collaborator._gemini_word_translation_service, "select_meaning_sections_batch", None)
    if not callable(selector):
        return [
            select_meaning_section(
                collaborator,
                surface_form=str(payload.get("surface_form", "")),
                lemma=str(payload.get("lemma", "")),
                pos_tag=payload.get("pos_tag") if isinstance(payload.get("pos_tag"), str) else None,
                morphology=payload.get("morphology") if isinstance(payload.get("morphology"), str) else None,
                gloss=payload.get("gloss") if isinstance(payload.get("gloss"), str) else None,
                english_translation=payload.get("english_translation")
                if isinstance(payload.get("english_translation"), str)
                else None,
                sentence_context=payload.get("sentence_context")
                if isinstance(payload.get("sentence_context"), str)
                else None,
                meaning_candidates=list(payload.get("meaning_candidates") or []),
            )
            for payload in payloads
        ]

    normalized_payloads: list[MeaningSectionSelectionInput] = []
    for payload in payloads:
        candidate_payloads: list[MeaningSectionCandidateInput] = []
        for candidate in list(payload.get("meaning_candidates") or []):
            candidate_id = getattr(candidate, "id", None)
            if not isinstance(candidate_id, int):
                continue
            candidate_payloads.append(
                MeaningSectionCandidateInput(
                    id=candidate_id,
                    lemma=str(getattr(candidate, "lemma", "")).strip(),
                    meaning_key=str(getattr(candidate, "meaning_key", "")),
                    cor_lemma_idx=getattr(candidate, "cor_lemma_idx", None),
                    gloss=normalize_translation_value(getattr(candidate, "gloss", None)),
                    english_translation=normalize_translation_value(
                        getattr(candidate, "english_translation", None)
                    ),
                    pos_tag=getattr(candidate, "pos_tag", None),
                    morphology=getattr(candidate, "morphology", None),
                )
            )
        normalized_payloads.append(
            MeaningSectionSelectionInput(
                surface_form=str(payload.get("surface_form", "")).strip(),
                lemma=str(payload.get("lemma", "")).strip(),
                pos_tag=payload.get("pos_tag") if isinstance(payload.get("pos_tag"), str) else None,
                morphology=payload.get("morphology") if isinstance(payload.get("morphology"), str) else None,
                gloss=normalize_translation_value(
                    payload.get("gloss") if isinstance(payload.get("gloss"), str) else None
                ),
                english_translation=normalize_translation_value(
                    payload.get("english_translation")
                    if isinstance(payload.get("english_translation"), str)
                    else None
                ),
                sentence_context=" ".join(str(payload.get("sentence_context", "")).strip().split()) or None,
                meaning_candidates=candidate_payloads,
            )
        )

    try:
        selected = selector(normalized_payloads)
    except (GeminiTranslationError, httpx.HTTPError, TimeoutError, ValueError, TypeError) as exc:
        log_provider_failure(
            logger=collaborator._logger,
            provider=contextual_provider_name(collaborator._gemini_word_translation_service),
            operation="select_meaning_sections_batch",
            reason=ProviderFailureReason.PARSE,
            retryable=False,
            exc=exc,
        )
        return [None] * len(payloads)
    return [value if isinstance(value, int) else None for value in selected[: len(payloads)]] + [
        None
    ] * max(0, len(payloads) - len(selected))
