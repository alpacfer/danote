from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from app.api.schemas.v1.wordbank import WordActionSuggestion
from app.db.migrations import get_connection
from app.services.cor import COREntry
from app.services.gemini_sense_discovery import (
    DiscoveredSense,
    SenseDiscoveryCorCandidate,
    SenseDiscoveryInput,
    is_sense_discoverable_pos,
)
from app.services.gemini_translation import ContextualWordTranslationInput
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.translation import TranslationCollaborator
from app.services.use_cases.wordbank.collaborators.translation_search_fallbacks import (
    build_search_translation_decision,
    evaluate_search_translation_candidate,
    invalid_search_translation,
)
from app.services.use_cases.wordbank.collaborators.translation_word_frames import (
    cor_entry_word_translation_frame,
)
from app.services.use_cases.wordbank.shared import (
    _cor_entry_priority,
    _CORAddOption,
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
    if not cor_add_options:
        return actions

    existing_da_actions = [
        action
        for action in actions
        if action.action_type == "add_as_new" and action.direction == "da_to_en"
    ]
    # Drop the lemma-level open_wordbank action when we have COR add options:
    # per-sense cards below render their own open_wordbank entry for any sense
    # that's already saved, so the lemma-level one would be a redundant duplicate.
    preserved_actions = [
        action
        for action in actions
        if not (action.action_type == "add_as_new" and action.direction == "da_to_en")
        and not (action.action_type == "open_wordbank" and action.direction == "known")
    ]
    default_direction_label = (
        existing_da_actions[0].direction_label
        if existing_da_actions and existing_da_actions[0].direction_label
        else "Danish -> English"
    )

    replaced_actions: list[WordActionSuggestion] = []
    seen_keys: set[tuple[str, str, str | None, str | None, str | None]] = set()
    for option in cor_add_options:
        comparable_surface = _normalize_action_value(option.surface)
        comparable_lemma = _normalize_action_value(option.lemma)
        key = (comparable_surface, comparable_lemma, option.pos_tag, option.morphology, option.meaning_key)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        label = option.translation_label or fallback_translation or option.surface
        action_type: Literal["open_wordbank", "add_as_new", "add_variation"] = (
            "open_wordbank" if option.saved_meaning_id is not None else "add_as_new"
        )
        direction: Literal["da_to_en", "en_to_da", "variation", "known"] = (
            "known" if option.saved_meaning_id is not None else "da_to_en"
        )
        direction_label = "Wordbank" if option.saved_meaning_id is not None else default_direction_label
        replaced_actions.append(
            WordActionSuggestion(
                action_type=action_type,
                surface=option.surface,
                lemma=option.lemma,
                cor_id=option.cor_id,
                translation_label=label,
                direction=direction,
                direction_label=direction_label,
                pos_tag=option.pos_tag,
                morphology=option.morphology,
                show_lemma=comparable_surface != comparable_lemma,
                meaning_key=option.meaning_key,
                gloss=option.gloss,
                english_translation=option.english_translation,
                alternative_translations=list(option.alternative_translations),
                cor_lemma_idx=option.cor_lemma_idx,
                saved_meaning_id=option.saved_meaning_id,
                example_da=option.example_da,
                example_en=option.example_en,
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
    db_path: Path | None = None,
    owner_user_id: int = 1,
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

    expanded_options = expand_options_with_senses(
        options,
        sorted_entries,
        translation=translation,
    )
    saved_meanings = (
        load_saved_meanings_for_lemmas(
            db_path,
            [option.lemma for option in expanded_options],
            owner_user_id=owner_user_id,
        )
        if db_path is not None
        else {}
    )
    return [_attach_saved_meaning(option, saved_meanings) for option in expanded_options]


def expand_options_with_senses(
    options: list[_CORAddOption],
    cor_entries: list[COREntry],
    *,
    translation: TranslationCollaborator,
) -> list[_CORAddOption]:
    expanded: list[_CORAddOption] = []
    candidates_by_lemma_pos = _group_cor_candidates(cor_entries)
    for option in options:
        senses = _discover_senses_for_option(
            option,
            translation=translation,
            candidates_by_lemma_pos=candidates_by_lemma_pos,
        )
        if not senses or len(senses) <= 1:
            expanded.append(_option_from_single_sense(option, senses[0] if senses else None))
            continue
        for sense in senses:
            expanded.append(_option_from_sense(option, sense))
    return expanded


def _discover_senses_for_option(
    option: _CORAddOption,
    *,
    translation: TranslationCollaborator,
    candidates_by_lemma_pos: dict[tuple[str, str | None], list[SenseDiscoveryCorCandidate]],
) -> list[DiscoveredSense]:
    if not is_sense_discoverable_pos(option.pos_tag):
        return []
    discover = getattr(translation, "discover_senses", None)
    if not callable(discover):
        return []
    candidates = candidates_by_lemma_pos.get(
        (option.lemma, (option.pos_tag or "").upper() or None),
        [],
    )
    payload = SenseDiscoveryInput(
        lemma=option.lemma,
        pos_tag=option.pos_tag,
        cor_gloss=None,
        cor_candidates=candidates,
    )
    result = discover(payload)
    if result is None:
        return []
    return list(result.senses)


def _option_from_single_sense(
    option: _CORAddOption,
    sense: DiscoveredSense | None,
) -> _CORAddOption:
    if sense is None:
        return option
    return _option_from_sense(option, sense)


def _option_from_sense(option: _CORAddOption, sense: DiscoveredSense) -> _CORAddOption:
    return _CORAddOption(
        surface=option.surface,
        lemma=option.lemma,
        cor_id=option.cor_id,
        pos_tag=option.pos_tag,
        morphology=option.morphology,
        translation_label=sense.english_translation or option.translation_label,
        meaning_key=sense.meaning_key,
        gloss=sense.gloss,
        english_translation=sense.english_translation,
        alternative_translations=tuple(sense.alternative_translations),
        cor_lemma_idx=sense.cor_lemma_idx,
        saved_meaning_id=option.saved_meaning_id,
        example_da=sense.example_da,
        example_en=sense.example_en,
    )


def _group_cor_candidates(
    cor_entries: list[COREntry],
) -> dict[tuple[str, str | None], list[SenseDiscoveryCorCandidate]]:
    grouped: dict[tuple[str, str | None], list[SenseDiscoveryCorCandidate]] = {}
    for entry in cor_entries:
        pos_key = (entry.pos_tag or "").upper() or None
        bucket = grouped.setdefault((entry.lemma, pos_key), [])
        bucket.append(
            SenseDiscoveryCorCandidate(
                cor_id=entry.cor_id,
                lemma=entry.lemma,
                gloss=normalize_token(entry.glosse or "") or None,
                pos_tag=entry.pos_tag,
                lemma_idx=getattr(entry, "lemma_idx", None),
            )
        )
    return grouped


def load_saved_meanings_for_lemmas(
    db_path: Path,
    lemmas: list[str],
    *,
    owner_user_id: int = 1,
) -> dict[str, dict[str, int]]:
    normalized: list[str] = []
    seen: set[str] = set()
    for lemma in lemmas:
        cleaned = normalize_token(lemma or "")
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    if not normalized:
        return {}
    placeholders = ", ".join("?" for _ in normalized)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT l.lemma AS lemma, lm.id AS meaning_id, lm.meaning_key AS meaning_key
            FROM lexeme_meanings lm
            JOIN lexemes l ON l.id = lm.lexeme_id
            WHERE l.owner_user_id = ? AND l.lemma IN ({placeholders})
            """,
            (owner_user_id, *normalized),
        ).fetchall()
    saved: dict[str, dict[str, int]] = {}
    for row in rows:
        saved.setdefault(row["lemma"], {})[row["meaning_key"]] = row["meaning_id"]
    return saved


def _attach_saved_meaning(
    option: _CORAddOption,
    saved_meanings: dict[str, dict[str, int]],
) -> _CORAddOption:
    if option.saved_meaning_id is not None:
        return option
    by_key = saved_meanings.get(option.lemma)
    if not by_key:
        return option
    saved_id = None
    if option.meaning_key is not None:
        saved_id = by_key.get(option.meaning_key)
    if saved_id is None and len(by_key) == 1 and option.meaning_key is None:
        saved_id = next(iter(by_key.values()))
    if saved_id is None:
        return option
    return _CORAddOption(
        surface=option.surface,
        lemma=option.lemma,
        cor_id=option.cor_id,
        pos_tag=option.pos_tag,
        morphology=option.morphology,
        translation_label=option.translation_label,
        meaning_key=option.meaning_key,
        gloss=option.gloss,
        english_translation=option.english_translation,
        alternative_translations=option.alternative_translations,
        cor_lemma_idx=option.cor_lemma_idx,
        saved_meaning_id=saved_id,
        example_da=option.example_da,
        example_en=option.example_en,
    )


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
