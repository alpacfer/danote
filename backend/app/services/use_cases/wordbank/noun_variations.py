from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping

from app.services.cor_local import CORLocalEntry
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.cor import CorResolutionCollaborator

TARGET_NOUN_SLOTS = (
    ("singular_definite", "Sing", "Def"),
    ("plural_indefinite", "Plur", "Ind"),
    ("plural_definite", "Plur", "Def"),
)
NOUN_SLOT_ACTION_FIELDS = {
    "singular_definite": "singular_definite_form",
    "plural_indefinite": "plural_indefinite_form",
    "plural_definite": "plural_definite_form",
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
}


@dataclass(frozen=True, slots=True)
class NounVariationMeaningContext:
    lexeme_id: int
    lemma: str
    meaning_id: int
    gloss: str | None
    english_translation: str | None
    cor_lemma_idx: int


def noun_meaning_context_from_rows(
    *,
    source_lexeme,
    source_meaning,
) -> NounVariationMeaningContext:
    if source_meaning is None:
        raise ValueError("fix_variations requires a meaning-scoped entry.")
    pos_tag = str(source_meaning["pos_tag"] or source_lexeme["pos_tag"] or "").upper()
    if pos_tag != "NOUN":
        raise ValueError("fix_variations requires a noun meaning.")
    cor_lemma_idx = source_meaning["cor_lemma_idx"]
    if cor_lemma_idx is None:
        raise RuntimeError("fix_variations requires COR identity.")
    return NounVariationMeaningContext(
        lexeme_id=int(source_lexeme["id"]),
        lemma=str(source_lexeme["lemma"]),
        meaning_id=int(source_meaning["id"]),
        gloss=source_meaning["gloss"],
        english_translation=source_meaning["english_translation"] or source_lexeme["english_translation"],
        cor_lemma_idx=int(cor_lemma_idx),
    )


def resolve_target_noun_slot_entries(
    cor: CorResolutionCollaborator,
    *,
    context: NounVariationMeaningContext,
    allow_lemma_mismatch: bool = False,
) -> dict[str, CORLocalEntry]:
    preferred_lemma = context.lemma
    if allow_lemma_mismatch:
        canonical_entry = cor.best_cor_local_lemma_entry(
            lemma_idx=context.cor_lemma_idx,
            lemma=context.lemma,
            preferred_pos_tag="NOUN",
            allow_lemma_mismatch=True,
        )
        preferred_lemma = normalize_token(canonical_entry.lemma) if canonical_entry is not None else context.lemma
    entries = cor.cor_local_entries_for_lemma_idx(
        lemma_idx=context.cor_lemma_idx,
        lemma=preferred_lemma,
        preferred_pos_tag="NOUN",
    )
    if not entries and preferred_lemma != context.lemma:
        entries = cor.cor_local_entries_for_lemma_idx(
            lemma_idx=context.cor_lemma_idx,
            lemma=context.lemma,
            preferred_pos_tag="NOUN",
        )
    if not entries:
        return {}
    matching_lemma = [
        entry for entry in entries if normalize_token(entry.lemma) == preferred_lemma and entry.pos_tag == "NOUN"
    ]
    if not matching_lemma and preferred_lemma != context.lemma:
        matching_lemma = [
            entry for entry in entries if normalize_token(entry.lemma) == context.lemma and entry.pos_tag == "NOUN"
        ]
    if not matching_lemma:
        return {}
    normalized_gloss = normalize_token(context.gloss or "")
    if normalized_gloss:
        gloss_matches = [
            entry for entry in matching_lemma if normalize_token(entry.gloss or "") == normalized_gloss
        ]
        if gloss_matches:
            matching_lemma = gloss_matches
    by_slot: dict[str, CORLocalEntry] = {}
    for entry in matching_lemma:
        slot = noun_slot_from_features(entry.features or _morphology_features(entry.morphology))
        if slot is None or slot in by_slot:
            continue
        by_slot[slot] = entry
    return by_slot


def extract_fix_variations_action_slot_forms(action: Mapping[str, object]) -> dict[str, str]:
    slot_forms: dict[str, str] = {}
    for slot_name, field_name in NOUN_SLOT_ACTION_FIELDS.items():
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
    return slot_forms


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


def _morphology_features(morphology: str | None) -> dict[str, str]:
    if not morphology:
        return {}
    features: dict[str, str] = {}
    for item in morphology.split("|"):
        key, _, value = item.partition("=")
        if key and value and key not in features:
            features[key] = value
    return features
