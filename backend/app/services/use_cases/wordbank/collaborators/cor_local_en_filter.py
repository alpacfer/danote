from __future__ import annotations

import logging

from app.api.schemas.v1.wordbank import CORSearchFormResponse, CORSearchGroup
from app.services.en_gemini_translation import ENGeminiTranslationService
from app.services.use_cases.wordbank.collaborators.cor_local_batch_filter import (
    filter_cor_form_responses_by_en_query_batch as filter_cor_form_responses_by_en_query_batch_with_runner,
)

logger = logging.getLogger(__name__)


def _danish_lemma_with_article(lemma: str, pos_tag: str | None) -> str:
    cleaned = (lemma or "").strip()
    if not cleaned:
        return cleaned
    pos = (pos_tag or "").upper()
    if pos == "VERB":
        return f"at {cleaned}"
    if pos == "NOUN":
        return f"et/en {cleaned}"
    return cleaned


def filter_cor_form_response_by_en_query(
    response: CORSearchFormResponse,
    *,
    en_query: str,
    en_pos_ud: str | None = None,
    en_gemini_translation_service: ENGeminiTranslationService | None,
) -> CORSearchFormResponse:
    if not response.groups or not en_query.strip():
        return response

    deterministic_response = _deterministic_en_query_filter(response, en_pos_ud=en_pos_ud)
    groups_for_gemini = deterministic_response.groups
    if en_gemini_translation_service is None:
        return deterministic_response

    choices: list[dict[str, object]] = [
        {
            "id": str(index),
            "danish_lemma": _danish_lemma_with_article(group.lemma, group.pos_tag),
            "danish_gloss": group.gloss or "",
            "pos": group.pos_tag or "",
        }
        for index, group in enumerate(groups_for_gemini)
    ]

    try:
        decisions = en_gemini_translation_service.select_translation_matches(
            query=en_query.strip(),
            choices=choices,
            en_pos_ud=(en_pos_ud or "").strip() or None,
        )
    except Exception:
        logger.exception(
            "cor_form_filter_gemini_failed",
            extra={"en_query": en_query, "form": response.form},
        )
        return _fallback_after_en_filter(deterministic_response, en_query=en_query, en_pos_ud=en_pos_ud)

    logger.info(
        "cor_form_filter_decision",
        extra={
            "en_query": en_query,
            "form": response.form,
            "choices": choices,
            "decisions": decisions,
        },
    )

    if not decisions:
        return _fallback_after_en_filter(deterministic_response, en_query=en_query, en_pos_ud=en_pos_ud)

    matching_indices: set[int] = set()
    for raw_id, matches in decisions.items():
        try:
            int_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if matches and 0 <= int_id < len(groups_for_gemini):
            matching_indices.add(int_id)

    if not matching_indices:
        return _fallback_after_en_filter(deterministic_response, en_query=en_query, en_pos_ud=en_pos_ud)

    filtered_groups = [
        group
        for index, group in enumerate(groups_for_gemini)
        if index in matching_indices
    ]
    filtered_groups = _prefer_gloss_matches(filtered_groups, en_query=en_query)
    return CORSearchFormResponse(
        form=response.form,
        groups=filtered_groups,
        did_you_mean=response.did_you_mean,
    )


def filter_cor_form_responses_by_en_query_batch(
    items: list[tuple[CORSearchFormResponse, str, str | None]],
    *,
    en_gemini_translation_service: ENGeminiTranslationService | None,
) -> list[CORSearchFormResponse]:
    return filter_cor_form_responses_by_en_query_batch_with_runner(
        items,
        en_gemini_translation_service=en_gemini_translation_service,
        single_filter=filter_cor_form_response_by_en_query,
    )


def _deterministic_en_query_filter(
    response: CORSearchFormResponse,
    *,
    en_pos_ud: str | None,
) -> CORSearchFormResponse:
    pos_hints = _parse_pos_hints(en_pos_ud)
    if not pos_hints:
        return response

    matching_pos_groups = [
        group
        for group in response.groups
        if (group.pos_tag or "").strip().upper() in pos_hints
    ]
    if not matching_pos_groups:
        return response
    return CORSearchFormResponse(
        form=response.form,
        groups=matching_pos_groups,
        did_you_mean=response.did_you_mean,
    )


def _fallback_after_en_filter(
    response: CORSearchFormResponse,
    *,
    en_query: str,
    en_pos_ud: str | None,
) -> CORSearchFormResponse:
    groups = _prefer_gloss_matches(response.groups, en_query=en_query)
    if not _parse_pos_hints(en_pos_ud) or len(groups) <= 1:
        return CORSearchFormResponse(form=response.form, groups=groups, did_you_mean=response.did_you_mean)
    return CORSearchFormResponse(
        form=response.form,
        groups=groups[:1],
        did_you_mean=response.did_you_mean,
    )


def _prefer_gloss_matches(groups: list[CORSearchGroup], *, en_query: str) -> list[CORSearchGroup]:
    markers = _english_query_gloss_markers(en_query)
    if not markers:
        return groups
    matched = [
        group
        for group in groups
        if any(marker in (group.gloss or "").casefold() for marker in markers)
    ]
    return matched or groups


def _english_query_gloss_markers(en_query: str) -> set[str]:
    words = {word.strip(".,!?;:()[]{}\"'").casefold() for word in en_query.split()}
    if words & {"book", "books"}:
        return {"læsning", "skrift", "trykt"}
    if words & {"house", "houses", "home"}:
        return {"bolig", "bygning", "hus"}
    if words & {"clothes", "clothing", "garment", "garments"}:
        return {"klæder", "tøj", "stof"}
    return set()


def _parse_pos_hints(value: str | None) -> set[str]:
    return {
        part.strip().upper()
        for part in (value or "").split(",")
        if part.strip()
    }
