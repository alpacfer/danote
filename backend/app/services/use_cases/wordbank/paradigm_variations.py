from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Mapping

from app.services.cor_local import CORLocalEntry
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.cor import CorResolutionCollaborator

ParadigmKind = str

ALL_NOUN_SLOTS = (
    ("singular_indefinite", "Sing", "Ind"),
    ("singular_definite", "Sing", "Def"),
    ("plural_indefinite", "Plur", "Ind"),
    ("plural_definite", "Plur", "Def"),
)
TARGET_NOUN_SLOTS = tuple(slot for slot in ALL_NOUN_SLOTS if slot[0] != "singular_indefinite")
NOUN_SLOT_ACTION_LIST_FIELDS = {
    "singular_indefinite": "singular_indefinite_forms",
    "singular_definite": "singular_definite_forms",
    "plural_indefinite": "plural_indefinite_forms",
    "plural_definite": "plural_definite_forms",
}
LEGACY_NOUN_SLOT_ACTION_FIELDS = {
    "singular_definite": "singular_definite_form",
    "plural_indefinite": "plural_indefinite_form",
    "plural_definite": "plural_definite_form",
}

ADJECTIVE_TARGET_SLOT_ORDER = (
    "singular_indefinite_n_word",
    "singular_indefinite_t_word",
    "singular_definite",
    "plural_shared",
)
ADJECTIVE_DISPLAY_SLOT_ORDER = (
    "singular_indefinite_n_word",
    "singular_indefinite_t_word",
    "singular_definite",
    "plural_indefinite",
    "plural_definite",
)
ADJECTIVE_SLOT_ACTION_LIST_FIELDS = {
    "singular_indefinite_n_word": "singular_indefinite_n_word_forms",
    "singular_indefinite_t_word": "singular_indefinite_t_word_forms",
    "singular_definite": "singular_definite_forms",
    "plural_indefinite": "plural_indefinite_forms",
    "plural_definite": "plural_definite_forms",
}

_QUOTED_FORM = r"['\"`]([^'\"`]+)['\"`]"
_SLOT_TEXT_PATTERNS = {
    "singular_definite": (
        re.compile(rf"singular definite(?: form)?[^'\"`\n]*{_QUOTED_FORM}", re.IGNORECASE),
        re.compile(rf"definite singular(?: form)?[^'\"`\n]*{_QUOTED_FORM}", re.IGNORECASE),
    ),
    "plural_indefinite": (
        re.compile(rf"plural indefinite(?: form)?[^'\"`\n]*{_QUOTED_FORM}", re.IGNORECASE),
        re.compile(rf"indefinite plural(?: form)?[^'\"`\n]*{_QUOTED_FORM}", re.IGNORECASE),
    ),
    "plural_definite": (
        re.compile(rf"plural definite(?: form)?[^'\"`\n]*{_QUOTED_FORM}", re.IGNORECASE),
        re.compile(rf"definite plural(?: form)?[^'\"`\n]*{_QUOTED_FORM}", re.IGNORECASE),
    ),
    "singular_indefinite_n_word": (
        re.compile(rf"singular indefinite n-word(?: form)?[^'\"`\n]*{_QUOTED_FORM}", re.IGNORECASE),
        re.compile(rf"n-word(?: form)?[^'\"`\n]*{_QUOTED_FORM}", re.IGNORECASE),
    ),
    "singular_indefinite_t_word": (
        re.compile(rf"singular indefinite t-word(?: form)?[^'\"`\n]*{_QUOTED_FORM}", re.IGNORECASE),
        re.compile(rf"t-word(?: form)?[^'\"`\n]*{_QUOTED_FORM}", re.IGNORECASE),
    ),
}


@dataclass(frozen=True, slots=True)
class ParadigmMeaningContext:
    lexeme_id: int
    lemma: str
    meaning_id: int
    gloss: str | None
    english_translation: str | None
    cor_lemma_idx: int
    paradigm_kind: ParadigmKind


def paradigm_kind_from_pos_tag(pos_tag: str | None) -> ParadigmKind | None:
    normalized = str(pos_tag or "").upper()
    if normalized == "NOUN":
        return "noun"
    if normalized == "ADJ":
        return "adjective"
    return None


def meaning_context_from_rows(
    *,
    source_lexeme,
    source_meaning,
) -> ParadigmMeaningContext:
    if source_meaning is None:
        raise ValueError("fix_variations requires a meaning-scoped entry.")
    paradigm_kind = paradigm_kind_from_pos_tag(source_meaning["pos_tag"] or source_lexeme["pos_tag"])
    if paradigm_kind is None:
        raise ValueError("fix_variations requires a noun or adjective meaning.")
    cor_lemma_idx = source_meaning["cor_lemma_idx"]
    if cor_lemma_idx is None:
        raise RuntimeError("fix_variations requires COR identity.")
    return ParadigmMeaningContext(
        lexeme_id=int(source_lexeme["id"]),
        lemma=str(source_lexeme["lemma"]),
        meaning_id=int(source_meaning["id"]),
        gloss=source_meaning["gloss"],
        english_translation=source_meaning["english_translation"] or source_lexeme["english_translation"],
        cor_lemma_idx=int(cor_lemma_idx),
        paradigm_kind=paradigm_kind,
    )


def noun_meaning_context_from_rows(*, source_lexeme, source_meaning) -> ParadigmMeaningContext:
    context = meaning_context_from_rows(source_lexeme=source_lexeme, source_meaning=source_meaning)
    if context.paradigm_kind != "noun":
        raise ValueError("fix_variations requires a noun meaning.")
    return context


def resolve_target_slot_entries(
    cor: CorResolutionCollaborator,
    *,
    context: ParadigmMeaningContext,
    allow_lemma_mismatch: bool = False,
) -> dict[str, list[CORLocalEntry]]:
    preferred_lemma = context.lemma
    preferred_pos_tag = "NOUN" if context.paradigm_kind == "noun" else "ADJ"
    if allow_lemma_mismatch:
        canonical_entry = cor.best_cor_local_lemma_entry(
            lemma_idx=context.cor_lemma_idx,
            lemma=context.lemma,
            preferred_pos_tag=preferred_pos_tag,
            allow_lemma_mismatch=True,
        )
        preferred_lemma = normalize_token(canonical_entry.lemma) if canonical_entry is not None else context.lemma

    entries = cor.cor_local_entries_for_lemma_idx(
        lemma_idx=context.cor_lemma_idx,
        lemma=preferred_lemma,
        preferred_pos_tag=preferred_pos_tag,
    )
    if not entries and preferred_lemma != context.lemma:
        entries = cor.cor_local_entries_for_lemma_idx(
            lemma_idx=context.cor_lemma_idx,
            lemma=context.lemma,
            preferred_pos_tag=preferred_pos_tag,
        )
    if not entries:
        return {}

    matching_lemma = [
        entry
        for entry in entries
        if normalize_token(entry.lemma) in {preferred_lemma, context.lemma} and entry.pos_tag == preferred_pos_tag
    ]
    if not matching_lemma:
        return {}

    normalized_gloss = normalize_token(context.gloss or "")
    if normalized_gloss:
        gloss_matches = [entry for entry in matching_lemma if normalize_token(entry.gloss or "") == normalized_gloss]
        if gloss_matches:
            matching_lemma = gloss_matches

    by_slot: dict[str, list[CORLocalEntry]] = {}
    for entry in matching_lemma:
        for slot in slots_for_entry(context.paradigm_kind, entry):
            by_slot.setdefault(slot, []).append(entry)
    return by_slot


def resolve_target_noun_slot_entries(
    cor: CorResolutionCollaborator,
    *,
    context: ParadigmMeaningContext,
    allow_lemma_mismatch: bool = False,
) -> dict[str, list[CORLocalEntry]]:
    return resolve_target_slot_entries(cor, context=context, allow_lemma_mismatch=allow_lemma_mismatch)


def build_completion_candidate_entries(
    *,
    context: ParadigmMeaningContext,
    slot_entries: dict[str, list[CORLocalEntry]],
) -> list[tuple[str, list[CORLocalEntry]]]:
    ordered: list[tuple[str, list[CORLocalEntry]]] = []
    seen: set[str] = set()
    if context.paradigm_kind == "noun":
        slot_order = [slot_name for slot_name, _number, _definite in TARGET_NOUN_SLOTS]
    else:
        slot_order = list(ADJECTIVE_TARGET_SLOT_ORDER)

    for slot_name in slot_order:
        for entry in slot_entries.get(slot_name, []):
            normalized_form = normalize_token(entry.form)
            if not normalized_form or normalized_form in seen:
                continue
            same_form_entries = [
                candidate
                for candidates in slot_entries.values()
                for candidate in candidates
                if normalize_token(candidate.form) == normalized_form
            ]
            seen.add(normalized_form)
            ordered.append((normalized_form, same_form_entries or [entry]))
    return ordered


def extract_fix_variations_action_slot_form_lists(action: Mapping[str, object]) -> dict[str, list[str]]:
    slot_forms: dict[str, list[str]] = {}
    for slot_name, field_name in NOUN_SLOT_ACTION_LIST_FIELDS.items():
        slot_values = _clean_string_list(action.get(field_name))
        if slot_values:
            slot_forms[slot_name] = slot_values
    for slot_name, field_name in ADJECTIVE_SLOT_ACTION_LIST_FIELDS.items():
        slot_values = _clean_string_list(action.get(field_name))
        if slot_values:
            slot_forms[slot_name] = slot_values
    return _expand_adjective_plural_lists(slot_forms)


def extract_fix_variations_action_slot_forms(action: Mapping[str, object]) -> dict[str, str]:
    slot_forms: dict[str, str] = {}
    for slot_name, field_name in LEGACY_NOUN_SLOT_ACTION_FIELDS.items():
        raw_value = action.get(field_name)
        if not isinstance(raw_value, str):
            continue
        cleaned = " ".join(raw_value.strip().split())
        if cleaned:
            slot_forms[slot_name] = cleaned
    return slot_forms


def parse_fix_variations_text_slot_forms(text: str | None) -> dict[str, str]:
    if not isinstance(text, str):
        return {}
    cleaned_text = " ".join(text.strip().split())
    if not cleaned_text:
        return {}
    slot_forms: dict[str, str] = {}
    for slot_name, patterns in _SLOT_TEXT_PATTERNS.items():
        for pattern in patterns:
            match = pattern.search(cleaned_text)
            if match is None:
                continue
            form = " ".join(match.group(1).strip().split())
            if form:
                slot_forms[slot_name] = form
            break
    return _expand_adjective_plural_scalars(slot_forms)


def noun_slot_from_morphology(morphology: str | None) -> str | None:
    return noun_slot_from_features(_morphology_features(morphology))


def noun_slot_from_features(features: dict[str, str]) -> str | None:
    number = features.get("Number")
    definite = features.get("Definite")
    if number == "Sing" and definite == "Ind":
        return "singular_indefinite"
    if number == "Sing" and definite == "Def":
        return "singular_definite"
    if number == "Plur" and definite == "Ind":
        return "plural_indefinite"
    if number == "Plur" and definite == "Def":
        return "plural_definite"
    return None


def adjective_slot_from_morphology(morphology: str | None) -> str | None:
    return adjective_slot_from_features(_morphology_features(morphology))


def adjective_slot_from_features(features: dict[str, str]) -> str | None:
    number = features.get("Number")
    definite = features.get("Definite")
    gender = features.get("Gender")
    if number == "Sing" and definite == "Ind":
        if gender == "Neut":
            return "singular_indefinite_t_word"
        if gender in {"Com", "Masc", "Fem"}:
            return "singular_indefinite_n_word"
    if number == "Sing" and definite == "Def":
        return "singular_definite"
    if number == "Plur":
        return "plural_shared"
    return None


def slots_for_entry(paradigm_kind: ParadigmKind, entry: CORLocalEntry) -> tuple[str, ...]:
    slots: list[str] = []
    feature_slot = (
        noun_slot_from_features(entry.features or _morphology_features(entry.morphology))
        if paradigm_kind == "noun"
        else adjective_slot_from_features(entry.features or _morphology_features(entry.morphology))
    )
    if feature_slot is not None:
        slots.append(feature_slot)

    for gram in _split_gram_parts(entry.gram_raw):
        gram_slot = _slot_from_gram(paradigm_kind, gram)
        if gram_slot is not None and gram_slot not in slots:
            slots.append(gram_slot)
    return tuple(slots)


def action_slot_labels_for_kind(paradigm_kind: ParadigmKind) -> tuple[str, ...]:
    if paradigm_kind == "noun":
        return tuple(slot_name for slot_name, _number, _definite in ALL_NOUN_SLOTS)
    return ADJECTIVE_DISPLAY_SLOT_ORDER


def _split_gram_parts(gram_raw: str | None) -> list[str]:
    if not gram_raw:
        return []
    return [part.strip().lower() for part in gram_raw.split("|") if part.strip()]


def _slot_from_gram(paradigm_kind: ParadigmKind, gram: str) -> str | None:
    parts = {part.strip() for part in gram.split(".") if part.strip()}
    if paradigm_kind == "noun" and "sb" in parts:
        if {"sg", "ubest"} <= parts:
            return "singular_indefinite"
        if {"sg", "best"} <= parts:
            return "singular_definite"
        if {"pl", "ubest"} <= parts:
            return "plural_indefinite"
        if {"pl", "best"} <= parts:
            return "plural_definite"
    if paradigm_kind == "adjective" and "adj" in parts:
        if {"sg", "ubest", "fk"} <= parts:
            return "singular_indefinite_n_word"
        if {"sg", "ubest", "itk"} <= parts:
            return "singular_indefinite_t_word"
        if {"sg", "best"} <= parts:
            return "singular_definite"
        if "pl" in parts:
            return "plural_shared"
    return None


def _morphology_features(morphology: str | None) -> dict[str, str]:
    if not morphology:
        return {}
    features: dict[str, str] = {}
    for item in morphology.split("|"):
        key, _, value = item.partition("=")
        if key and value and key not in features:
            features[key] = value
    return features


def _clean_string_list(raw_value: object) -> list[str]:
    if not isinstance(raw_value, list):
        return []
    cleaned_values: list[str] = []
    seen: set[str] = set()
    for item in raw_value:
        if not isinstance(item, str):
            continue
        cleaned = " ".join(item.strip().split())
        normalized = normalize_token(cleaned)
        if not cleaned or normalized in seen:
            continue
        seen.add(normalized)
        cleaned_values.append(cleaned)
    return cleaned_values


def _expand_adjective_plural_lists(slot_forms: dict[str, list[str]]) -> dict[str, list[str]]:
    if "plural_shared" in slot_forms:
        shared = list(slot_forms["plural_shared"])
        if shared:
            slot_forms.setdefault("plural_indefinite", shared)
            slot_forms.setdefault("plural_definite", shared)
    return slot_forms


def _expand_adjective_plural_scalars(slot_forms: dict[str, str]) -> dict[str, str]:
    if "plural_shared" in slot_forms:
        shared = slot_forms["plural_shared"]
        slot_forms.setdefault("plural_indefinite", shared)
        slot_forms.setdefault("plural_definite", shared)
    return slot_forms
