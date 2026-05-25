from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.api.schemas.v1.wordbank import CORSearchFormResponse
from app.services.en_gemini_translation import ENGeminiTranslationService

logger = logging.getLogger(__name__)


def filter_cor_form_responses_by_en_query_batch(
    items: list[tuple[CORSearchFormResponse, str, str | None]],
    *,
    en_gemini_translation_service: ENGeminiTranslationService | None,
    single_filter,
) -> list[CORSearchFormResponse]:
    if not items:
        return []
    if _flag_enabled("DANOTE_SEARCH_BATCHED_GEMINI", default=True):
        batched = _filter_cor_form_responses_with_single_gemini_call(
            items,
            en_gemini_translation_service=en_gemini_translation_service,
        )
        if batched is not None:
            return batched
    if not _flag_enabled("DANOTE_SEARCH_PARALLEL", default=True) or len(items) < 2:
        return [
            single_filter(
                response,
                en_query=en_query,
                en_pos_ud=en_pos_ud,
                en_gemini_translation_service=en_gemini_translation_service,
            )
            for response, en_query, en_pos_ud in items
        ]

    ordered: list[CORSearchFormResponse | None] = [None] * len(items)
    with ThreadPoolExecutor(max_workers=min(4, len(items))) as executor:
        futures = {
            executor.submit(
                single_filter,
                response,
                en_query=en_query,
                en_pos_ud=en_pos_ud,
                en_gemini_translation_service=en_gemini_translation_service,
            ): index
            for index, (response, en_query, en_pos_ud) in enumerate(items)
        }
        for future in as_completed(futures):
            ordered[futures[future]] = future.result()
    return [item for item in ordered if item is not None]


def _filter_cor_form_responses_with_single_gemini_call(
    items: list[tuple[CORSearchFormResponse, str, str | None]],
    *,
    en_gemini_translation_service: ENGeminiTranslationService | None,
) -> list[CORSearchFormResponse] | None:
    if en_gemini_translation_service is None:
        return [response for response, _en_query, _en_pos_ud in items]
    batch_matcher = getattr(en_gemini_translation_service, "select_translation_matches_batch", None)
    if not callable(batch_matcher):
        return None

    choices: list[dict[str, object]] = []
    id_to_group: dict[str, tuple[int, int]] = {}
    query = ""
    pos_hints: set[str] = set()
    for item_index, (response, en_query, en_pos_ud) in enumerate(items):
        query = query or en_query.strip()
        for pos in (en_pos_ud or "").split(","):
            normalized_pos = pos.strip().upper()
            if normalized_pos:
                pos_hints.add(normalized_pos)
        groups = _deterministic_groups_for_en_query(response, en_pos_ud)
        for group_index, group in enumerate(groups):
            choice_id = f"{item_index}:{group_index}"
            id_to_group[choice_id] = (item_index, group_index)
            choices.append(
                {
                    "id": choice_id,
                    "danish_lemma": _danish_lemma_with_article(group.lemma, group.pos_tag),
                    "danish_gloss": group.gloss or "",
                    "pos": group.pos_tag or "",
                    "source_form": response.form,
                }
            )
    if not choices or not query:
        return [response for response, _en_query, _en_pos_ud in items]

    try:
        decisions = batch_matcher(
            query=query,
            en_pos_ud=",".join(sorted(pos_hints)) or None,
            lemma_choices=choices,
        )
    except Exception:
        logger.exception("cor_form_batch_filter_gemini_failed", extra={"en_query": query})
        return None
    if not decisions:
        return [response for response, _en_query, _en_pos_ud in items]

    matching_by_item: dict[int, set[int]] = {}
    for choice_id, matches in decisions.items():
        if not matches or choice_id not in id_to_group:
            continue
        item_index, group_index = id_to_group[choice_id]
        matching_by_item.setdefault(item_index, set()).add(group_index)

    filtered: list[CORSearchFormResponse] = []
    for item_index, (response, _en_query, _en_pos_ud) in enumerate(items):
        deterministic_groups = _deterministic_groups_for_en_query(response, _en_pos_ud)
        matching_indices = matching_by_item.get(item_index)
        if not matching_indices:
            fallback_groups = _fallback_groups_after_en_filter(deterministic_groups, _en_query, _en_pos_ud)
            filtered.append(CORSearchFormResponse(
                form=response.form,
                groups=fallback_groups,
                did_you_mean=response.did_you_mean,
            ))
            continue
        filtered_groups = [
            group
            for group_index, group in enumerate(deterministic_groups)
            if group_index in matching_indices
        ]
        filtered_groups = _prefer_gloss_matches(filtered_groups, en_query=_en_query)
        filtered.append(
            CORSearchFormResponse(
                form=response.form,
                groups=filtered_groups,
                did_you_mean=response.did_you_mean,
            )
        )
    return filtered


def _deterministic_groups_for_en_query(
    response: CORSearchFormResponse,
    en_pos_ud: str | None,
) -> list:
    pos_hints = {
        part.strip().upper()
        for part in (en_pos_ud or "").split(",")
        if part.strip()
    }
    if not pos_hints:
        return list(response.groups)
    matching = [
        group
        for group in response.groups
        if (group.pos_tag or "").strip().upper() in pos_hints
    ]
    return matching or list(response.groups)


def _fallback_groups_after_en_filter(groups: list, en_query: str, en_pos_ud: str | None) -> list:
    groups = _prefer_gloss_matches(groups, en_query=en_query)
    pos_hints = {
        part.strip().upper()
        for part in (en_pos_ud or "").split(",")
        if part.strip()
    }
    if pos_hints and len(groups) > 1:
        return groups[:1]
    return groups


def _prefer_gloss_matches(groups: list, *, en_query: str) -> list:
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


def _flag_enabled(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no"}
