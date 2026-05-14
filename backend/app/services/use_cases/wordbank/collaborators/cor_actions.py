from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from app.api.schemas.v1.wordbank import WordActionSuggestion
from app.db.migrations import get_connection
from app.services.cor import COREntry
from app.services.gemini_translation import ContextualWordTranslationInput
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.translation_word_frames import (
    cor_entry_word_translation_frame,
)
from app.services.use_cases.wordbank.collaborators.translation import TranslationCollaborator
from app.services.use_cases.wordbank.collaborators.translation_search_fallbacks import (
    build_search_translation_decision,
    evaluate_search_translation_candidate,
    invalid_search_translation,
)
from app.services.use_cases.wordbank.shared import (
    _CORAddOption,
    _cor_entry_priority,
    _normalize_action_value,
)

logger = logging.getLogger(__name__)


def find_saved_lemma(
    db_path: Path,
    candidates: list[str],
    *,
    owner_user_id: int = 1,
) -> str | None:
    normalized_candidates = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = normalize_token(candidate)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_candidates.append(normalized)
    if not normalized_candidates:
        return None

    placeholders = ", ".join("?" for _ in normalized_candidates)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT lemma
            FROM lexemes
            WHERE owner_user_id = ? AND lemma IN ({placeholders})
            ORDER BY lemma COLLATE NOCASE
            """,
            (owner_user_id, *normalized_candidates),
        ).fetchall()
    saved = {row["lemma"] for row in rows}
    for candidate in normalized_candidates:
        if candidate in saved:
            return candidate
    return None


def replace_danish_add_actions(
    actions: list[WordActionSuggestion],
    *,
    classification: Literal["known", "variation", "typo_likely", "uncertain", "new"],
    matched_lemma: str | None,
    cor_add_options: list[_CORAddOption],
    fallback_translation: str | None,
) -> list[WordActionSuggestion]:
    if classification in {"known", "variation"} or matched_lemma:
        return actions
    if not cor_add_options:
        return actions

    existing_da_actions = [
        action
        for action in actions
        if action.action_type == "add_as_new" and action.direction == "da_to_en"
    ]
    preserved_actions = [
        action
        for action in actions
        if not (action.action_type == "add_as_new" and action.direction == "da_to_en")
    ]
    default_direction_label = (
        existing_da_actions[0].direction_label
        if existing_da_actions and existing_da_actions[0].direction_label
        else "Danish -> English"
    )

    replaced_actions: list[WordActionSuggestion] = []
    seen_keys: set[tuple[str, str, str | None, str | None]] = set()
    for option in cor_add_options:
        comparable_surface = _normalize_action_value(option.surface)
        comparable_lemma = _normalize_action_value(option.lemma)
        key = (comparable_surface, comparable_lemma, option.pos_tag, option.morphology)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        label = option.translation_label or fallback_translation or option.surface
        replaced_actions.append(
            WordActionSuggestion(
                action_type="add_as_new",
                surface=option.surface,
                lemma=option.lemma,
                cor_id=option.cor_id,
                translation_label=label,
                direction="da_to_en",
                direction_label=default_direction_label,
                pos_tag=option.pos_tag,
                morphology=option.morphology,
                show_lemma=comparable_surface != comparable_lemma,
            )
        )

    if not replaced_actions:
        return actions
    return replaced_actions + preserved_actions


def build_cor_add_options(
    normalized_query: str,
    *,
    include_translations: bool,
    cor_entries_lookup,
    translation: TranslationCollaborator,
) -> list[_CORAddOption]:
    if not normalized_query:
        return []

    entries = cor_entries_lookup(normalized_query)
    if not entries:
        return []

    by_pos: dict[str | None, COREntry] = {}
    for entry in entries:
        if _normalize_action_value(entry.full_form) != _normalize_action_value(normalized_query):
            continue
        key = entry.pos_tag
        current = by_pos.get(key)
        if current is None:
            by_pos[key] = entry
            continue
        if _cor_entry_priority(entry, normalized_query) < _cor_entry_priority(
            current, normalized_query
        ):
            by_pos[key] = entry

    options: list[_CORAddOption] = []
    sorted_entries = sorted(
        by_pos.values(),
        key=lambda item: _cor_entry_priority(item, normalized_query),
    )
    translation_labels: list[str | None] = []
    if include_translations:
        translation_labels = _lookup_translation_labels_for_cor_entries(
            translation,
            sorted_entries,
            normalized_query,
        )

    for index, entry in enumerate(sorted_entries):
        translation_label = translation_labels[index] if index < len(translation_labels) else None
        options.append(
            _CORAddOption(
                surface=normalized_query,
                lemma=entry.lemma,
                cor_id=entry.cor_id,
                pos_tag=entry.pos_tag,
                morphology=entry.morphology,
                translation_label=translation_label,
            )
        )

    return options


def _lookup_translation_labels_for_cor_entries(
    translation: TranslationCollaborator,
    entries: list[COREntry],
    normalized_query: str,
) -> list[str | None]:
    if not entries:
        return []
    payloads = [
        ContextualWordTranslationInput(
            surface_form=normalized_query,
            lemma=entry.lemma,
            pos_tag=entry.pos_tag,
            morphology=entry.morphology,
            gloss=normalize_token(entry.glosse or "") or None,
        )
        for entry in entries
    ]
    contextual_results = translation.batch_lookup_contextual_word_translations(payloads)
    labels: list[str | None] = []
    for entry, contextual in zip(entries, contextual_results, strict=False):
        contextual_translation = _validated_search_label(
            entry,
            normalized_query,
            contextual.translation,
            provider=translation.contextual_provider_name(),
            rejection_reason="gemini_self_translation",
        )
        provider_translation = lookup_translation_for_cor_entry(
            translation,
            entry,
            normalized_query,
        )
        frame = cor_entry_word_translation_frame(entry)
        decision = build_search_translation_decision(
            provider_candidate=evaluate_search_translation_candidate(
                translation=provider_translation,
                lemma=entry.lemma,
                surface_form=normalized_query,
                frame_text=frame.text,
            ),
            provider_name=translation.provider_name(),
            contextual_candidate=evaluate_search_translation_candidate(
                translation=contextual_translation,
                lemma=entry.lemma,
                surface_form=normalized_query,
                frame_text=frame.text,
            ),
            contextual_provider_name=translation.contextual_provider_name(),
            contextual_attempted=True,
            gloss_fallback=_lookup_gloss_translation_for_cor_entry(translation, entry),
        )
        labels.append(decision.lemma_translation or decision.saveable_translation)
    if len(labels) < len(entries):
        labels.extend([None] * (len(entries) - len(labels)))
    return labels


def lookup_translation_for_cor_entry(
    translation: TranslationCollaborator,
    entry: COREntry,
    normalized_query: str,
) -> str | None:
    frame = cor_entry_word_translation_frame(entry)
    candidates: list[str] = [frame.text]
    candidates.append(entry.lemma)
    candidates.append(normalized_query)

    seen: set[str] = set()
    for candidate in candidates:
        normalized_candidate = normalize_token(candidate)
        if not normalized_candidate or normalized_candidate in seen:
            continue
        seen.add(normalized_candidate)
        translated = translation.lookup_translation(normalized_candidate)
        if translated:
            if normalized_candidate == normalize_token(frame.text):
                framed = translation.cleanup_framed_word_translation(frame, translated)
                if framed:
                    if (
                        entry.pos_tag == "VERB"
                        and framed.startswith("to ")
                        and not normalize_token(translated).startswith("to ")
                    ):
                        framed = framed[3:]
                    validated = _validated_search_label(
                        entry,
                        normalized_query,
                        framed,
                        provider=translation.provider_name(),
                        rejection_reason="azure_self_translation",
                    )
                    if validated:
                        return validated
                    continue
            validated = _validated_search_label(
                entry,
                normalized_query,
                translated,
                provider=translation.provider_name(),
                rejection_reason="azure_self_translation",
            )
            if validated:
                return validated
    return None


def _validated_search_label(
    entry: COREntry,
    normalized_query: str,
    candidate: str | None,
    *,
    provider: str,
    rejection_reason: str,
) -> str | None:
    frame = cor_entry_word_translation_frame(entry)
    invalid = invalid_search_translation(
        translation=candidate,
        lemma=entry.lemma,
        surface_form=normalized_query,
        frame_text=frame.text,
    )
    if invalid is None:
        return candidate
    logger.info(
        "wordbank_search_translation_rejected",
        extra={
            "provider": provider,
            "rejection_reason": rejection_reason,
            "matched_source": invalid.matched_source,
            "comparable_value": invalid.comparable_value,
            "lemma": entry.lemma,
            "surface_form": normalized_query,
            "frame_text": frame.text,
            "translation": normalize_token(candidate or "") or None,
        },
    )
    return None


def _lookup_gloss_translation_for_cor_entry(
    translation: TranslationCollaborator,
    entry: COREntry,
) -> str | None:
    normalized_gloss = normalize_token(entry.glosse or "")
    if not normalized_gloss:
        return None
    return translation.lookup_translation(normalized_gloss)
