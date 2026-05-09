from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

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
VERB_DISPLAY_SLOT_ORDER = (
    "infinitive",
    "present",
    "past",
    "imperative",
    "past_participle",
)
VERB_SLOT_ACTION_LIST_FIELDS = {
    "infinitive": "infinitive_forms",
    "present": "present_forms",
    "past": "past_forms",
    "imperative": "imperative_forms",
    "past_participle": "past_participle_forms",
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
    "infinitive": (
        re.compile(rf"infinitive(?: form)?[^'\"`\n]*{_QUOTED_FORM}", re.IGNORECASE),
    ),
    "present": (
        re.compile(rf"present(?: form)?[^'\"`\n]*{_QUOTED_FORM}", re.IGNORECASE),
    ),
    "past": (
        re.compile(rf"past(?: form)?[^'\"`\n]*{_QUOTED_FORM}", re.IGNORECASE),
    ),
    "imperative": (
        re.compile(rf"imperative(?: form)?[^'\"`\n]*{_QUOTED_FORM}", re.IGNORECASE),
    ),
    "past_participle": (
        re.compile(rf"past participle(?: form)?[^'\"`\n]*{_QUOTED_FORM}", re.IGNORECASE),
        re.compile(rf"participle(?: form)?[^'\"`\n]*{_QUOTED_FORM}", re.IGNORECASE),
    ),
}


@dataclass(frozen=True, slots=True)
class ParadigmMeaningContext:
    lexeme_id: int
    lemma: str
    meaning_id: int
    gloss: str | None
    english_translation: str | None
    cor_lemma_idx: int | None
    paradigm_kind: ParadigmKind


def paradigm_kind_from_pos_tag(pos_tag: str | None) -> ParadigmKind | None:
    normalized = str(pos_tag or "").upper()
    if normalized == "NOUN":
        return "noun"
    if normalized == "ADJ":
        return "adjective"
    if normalized == "VERB":
        return "verb"
    return None


def meaning_context_from_rows(
    *,
    source_lexeme,
    source_meaning,
    allow_missing_cor_identity: bool = False,
) -> ParadigmMeaningContext:
    if source_meaning is None:
        raise ValueError("fix_variations requires a meaning-scoped entry.")
    paradigm_kind = paradigm_kind_from_pos_tag(source_meaning["pos_tag"] or source_lexeme["pos_tag"])
    if paradigm_kind is None:
        raise ValueError("fix_variations requires a noun, adjective, or verb meaning.")
    cor_lemma_idx = source_meaning["cor_lemma_idx"]
    if cor_lemma_idx is None and not allow_missing_cor_identity:
        raise RuntimeError("fix_variations requires COR identity.")
    return ParadigmMeaningContext(
        lexeme_id=int(source_lexeme["id"]),
        lemma=str(source_lexeme["lemma"]),
        meaning_id=int(source_meaning["id"]),
        gloss=source_meaning["gloss"],
        english_translation=source_meaning["english_translation"] or source_lexeme["english_translation"],
        cor_lemma_idx=int(cor_lemma_idx) if cor_lemma_idx is not None else None,
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
    if context.cor_lemma_idx is None:
        return {}
    preferred_lemma = context.lemma
    preferred_pos_tag = _preferred_pos_tag_for_kind(context.paradigm_kind)
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
    return {
        slot_name: _preferred_slot_entries(context.paradigm_kind, slot_name, entries)
        for slot_name, entries in by_slot.items()
        if entries
    }


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
    elif context.paradigm_kind == "adjective":
        slot_order = list(ADJECTIVE_TARGET_SLOT_ORDER)
    else:
        slot_order = list(VERB_DISPLAY_SLOT_ORDER)

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
    for slot_name, field_name in VERB_SLOT_ACTION_LIST_FIELDS.items():
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


def verb_slot_from_morphology(morphology: str | None) -> str | None:
    return verb_slot_from_features(_morphology_features(morphology))


def verb_slot_from_features(features: dict[str, str]) -> str | None:
    verb_form = features.get("VerbForm")
    mood = features.get("Mood")
    tense = features.get("Tense")
    if verb_form == "Part":
        return "past_participle"
    if verb_form == "Inf":
        return "infinitive"
    if mood == "Imp":
        return "imperative"
    if tense == "Past" and verb_form == "Fin":
        return "past"
    if tense == "Pres" and verb_form == "Fin":
        return "present"
    return None


def slots_for_gram_raw_and_morphology(
    paradigm_kind: ParadigmKind,
    *,
    gram_raw: str | None,
    morphology: str | None,
) -> tuple[str, ...]:
    slots: list[str] = []
    features = _morphology_features(morphology)
    if paradigm_kind == "noun":
        feature_slot = noun_slot_from_features(features)
    elif paradigm_kind == "adjective":
        feature_slot = adjective_slot_from_features(features)
    else:
        feature_slot = verb_slot_from_features(features)
    if feature_slot is not None:
        slots.append(feature_slot)

    for gram in _split_gram_parts(gram_raw):
        gram_slot = _slot_from_gram(paradigm_kind, gram)
        if gram_slot is not None and gram_slot not in slots:
            slots.append(gram_slot)
    return tuple(slots)


def slots_for_entry(paradigm_kind: ParadigmKind, entry: CORLocalEntry) -> tuple[str, ...]:
    if entry.features:
        if paradigm_kind == "noun":
            feature_slot = noun_slot_from_features(entry.features)
        elif paradigm_kind == "adjective":
            feature_slot = adjective_slot_from_features(entry.features)
        else:
            feature_slot = verb_slot_from_features(entry.features)
        gram_slots = [
            _slot_from_gram(paradigm_kind, gram)
            for gram in _split_gram_parts(entry.gram_raw)
        ]
        ordered_slots = [feature_slot, *gram_slots]
        return tuple(slot for slot in dict.fromkeys(slot for slot in ordered_slots if slot is not None))
    return slots_for_gram_raw_and_morphology(
        paradigm_kind,
        gram_raw=entry.gram_raw,
        morphology=entry.morphology,
    )


def action_slot_labels_for_kind(paradigm_kind: ParadigmKind) -> tuple[str, ...]:
    if paradigm_kind == "noun":
        return tuple(slot_name for slot_name, _number, _definite in ALL_NOUN_SLOTS)
    if paradigm_kind == "adjective":
        return ADJECTIVE_DISPLAY_SLOT_ORDER
    return VERB_DISPLAY_SLOT_ORDER


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
    if paradigm_kind == "verb" and "vb" in parts:
        if "imp" in parts:
            return "imperative"
        if "inf" in parts:
            return "infinitive"
        if "perf" in parts and "part" in parts:
            return "past_participle"
        if {"præs"} <= parts or {"prs"} <= parts:
            return "present"
        if "præt" in parts:
            return "past"
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


def _preferred_pos_tag_for_kind(paradigm_kind: ParadigmKind) -> str:
    if paradigm_kind == "noun":
        return "NOUN"
    if paradigm_kind == "adjective":
        return "ADJ"
    return "VERB"


def _preferred_slot_entries(
    paradigm_kind: ParadigmKind,
    slot_name: str,
    entries: list[CORLocalEntry],
) -> list[CORLocalEntry]:
    if paradigm_kind != "verb":
        return entries
    ranked = sorted(
        entries,
        key=lambda entry: (_verb_entry_preference_key(slot_name, entry), normalize_token(entry.form) or entry.form),
    )
    if not ranked:
        return []
    best_form = normalize_token(ranked[0].form) or ranked[0].form
    return [
        entry
        for entry in ranked
        if (normalize_token(entry.form) or entry.form) == best_form
    ]


def _verb_entry_preference_key(slot_name: str, entry: CORLocalEntry) -> tuple[int, int, int]:
    gram_parts = _verb_gram_tags(entry.gram_raw)
    voice = (entry.features or _morphology_features(entry.morphology)).get("Voice")
    passive_penalty = 1 if "pass" in gram_parts or voice == "Pass" else 0
    active_penalty = 0 if "akt" in gram_parts or voice == "Act" else 1
    if slot_name != "past_participle":
        return passive_penalty, active_penalty, 0
    inflection_penalty = sum(
        1
        for tag in ("sg", "pl", "fk", "itk", "best")
        if tag in gram_parts
    )
    bare_participle_penalty = 0 if "perf" in gram_parts and "part" in gram_parts else 1
    return bare_participle_penalty, inflection_penalty, passive_penalty


def _verb_gram_tags(gram_raw: str | None) -> set[str]:
    tags: set[str] = set()
    for gram in _split_gram_parts(gram_raw):
        tags.update(part.strip() for part in gram.split(".") if part.strip())
    return tags
