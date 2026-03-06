from __future__ import annotations

from typing import Literal

from app.api.schemas.v1.wordbank import WordActionSuggestion
from app.db.migrations import get_connection
from app.services.cor import COREntry
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.shared import _CORAddOption, _normalize_action_value


class WordbankCorResolutionActionsMixin:
    def _find_saved_lemma(self, candidates: list[str]) -> str | None:
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
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT lemma
                FROM lexemes
                WHERE lemma IN ({placeholders})
                ORDER BY lemma COLLATE NOCASE
                """,
                tuple(normalized_candidates),
            ).fetchall()
        saved = {row["lemma"] for row in rows}
        for candidate in normalized_candidates:
            if candidate in saved:
                return candidate
        return None



    def _replace_danish_add_actions(
        self,
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



    def _build_cor_add_options(
        self,
        normalized_query: str,
        *,
        include_translations: bool,
    ) -> list[_CORAddOption]:
        if not normalized_query:
            return []

        entries = self._cor_entries_for_surface(normalized_query)
        if not entries:
            return []

        # One add-option per POS, not per lemma+sense, so search UI presents a clean POS choice.
        by_pos: dict[str | None, COREntry] = {}
        for entry in entries:
            if _normalize_action_value(entry.full_form) != _normalize_action_value(normalized_query):
                continue
            key = entry.pos_tag
            current = by_pos.get(key)
            if current is None:
                by_pos[key] = entry
                continue
            if self._cor_entry_priority(entry, normalized_query) < self._cor_entry_priority(current, normalized_query):
                by_pos[key] = entry

        options: list[_CORAddOption] = []
        for entry in sorted(
            by_pos.values(),
            key=lambda item: self._cor_entry_priority(item, normalized_query),
        ):
            translation_label = None
            if include_translations:
                translation_label = self._lookup_translation_for_cor_entry(entry, normalized_query)
            options.append(
                _CORAddOption(
                    surface=normalized_query,
                    lemma=entry.lemma,
                    pos_tag=entry.pos_tag,
                    morphology=entry.morphology,
                    translation_label=translation_label,
                )
            )

        return options



    def _lookup_translation_for_cor_entry(self, entry: COREntry, normalized_query: str) -> str | None:
        candidates: list[str] = []
        if entry.pos_tag == "VERB":
            infinitive_hint = f"at {entry.lemma}".strip()
            candidates.append(infinitive_hint)
        candidates.append(entry.lemma)
        candidates.append(normalized_query)

        seen: set[str] = set()
        for candidate in candidates:
            normalized_candidate = normalize_token(candidate)
            if not normalized_candidate or normalized_candidate in seen:
                continue
            seen.add(normalized_candidate)
            translated = self._lookup_translation(normalized_candidate)
            if translated:
                return translated
        return None



    def _cor_entries_for_surface(self, normalized_value: str) -> list[COREntry]:
        if self._cor_lexicon_service is None:
            return []
        return self._cor_lexicon_service.lookup_full_form(normalized_value)



    def _best_cor_entry(
        self,
        entries: list[COREntry],
        *,
        normalized_surface: str,
        preferred_pos_tag: str | None,
    ) -> COREntry | None:
        if not entries:
            return None
        filtered = entries
        if preferred_pos_tag:
            preferred = [entry for entry in entries if entry.pos_tag == preferred_pos_tag]
            if preferred:
                filtered = preferred
        return min(filtered, key=lambda entry: self._cor_entry_priority(entry, normalized_surface))



    def _cor_entry_priority(self, entry: COREntry, normalized_surface: str) -> tuple[int, int, int, int, str, str]:
        if entry.norm_status == "N":
            norm_rank = 0
        elif entry.norm_status == "K":
            norm_rank = 1
        elif entry.norm_status == "U":
            norm_rank = 2
        else:
            norm_rank = 3
        is_exact_surface = 0 if _normalize_action_value(entry.full_form) == _normalize_action_value(normalized_surface) else 1
        lemma_matches_surface = 0 if _normalize_action_value(entry.lemma) == _normalize_action_value(normalized_surface) else 1
        noun_number_rank = 2
        if entry.pos_tag == "NOUN":
            morphology = entry.morphology or ""
            if "Number=Sing" in morphology:
                noun_number_rank = 0
            elif "Number=Plur" in morphology:
                noun_number_rank = 1
        has_pos = 0 if entry.pos_tag else 1
        has_morph = 0 if entry.morphology else 1
        return (
            is_exact_surface,
            norm_rank,
            lemma_matches_surface,
            noun_number_rank,
            has_pos,
            has_morph,
            entry.lemma,
            entry.cor_id,
        )
