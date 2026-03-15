from __future__ import annotations

import re

from app.api.schemas.v1.wordbank import LemmaDetailsResponse
from app.services.token_classifier import normalize_token

_GRAM_SLOT_PATTERNS = {
    "singular_definite": re.compile(r"(^|[.|])sg[.|]best($|[.|])"),
    "plural_indefinite": re.compile(r"(^|[.|])pl[.|]ubest($|[.|])"),
    "plural_definite": re.compile(r"(^|[.|])pl[.|]best($|[.|])"),
}
_SLOT_ORDER = {
    "singular_definite": 0,
    "plural_indefinite": 1,
    "plural_definite": 2,
}


def order_surface_form_details(
    forms: list[LemmaDetailsResponse.SurfaceFormDetails],
) -> list[LemmaDetailsResponse.SurfaceFormDetails]:
    if len(forms) < 2:
        return forms
    return sorted(forms, key=_surface_form_sort_key)


def _surface_form_sort_key(
    detail: LemmaDetailsResponse.SurfaceFormDetails,
) -> tuple[int, int, str]:
    slot = _noun_variation_slot(detail)
    normalized_form = normalize_token(detail.form) or detail.form.casefold()
    if slot is None:
        return (0, 0, normalized_form)
    return (1, _SLOT_ORDER[slot], normalized_form)


def _noun_variation_slot(
    detail: LemmaDetailsResponse.SurfaceFormDetails,
) -> str | None:
    morphology = detail.morphology or ""
    if _is_noun_candidate(detail):
        if "Number=Sing" in morphology and "Definite=Def" in morphology:
            return "singular_definite"
        if "Number=Plur" in morphology and "Definite=Ind" in morphology:
            return "plural_indefinite"
        if "Number=Plur" in morphology and "Definite=Def" in morphology:
            return "plural_definite"

    normalized_gram = re.sub(r"\s+", "", (detail.gram_raw or "").lower())
    if not normalized_gram.startswith("sb"):
        return None
    for slot, pattern in _GRAM_SLOT_PATTERNS.items():
        if pattern.search(normalized_gram):
            return slot
    return None


def _is_noun_candidate(detail: LemmaDetailsResponse.SurfaceFormDetails) -> bool:
    if (detail.pos_tag or "").upper() == "NOUN":
        return True
    if "Number=" in (detail.morphology or "") and "Definite=" in (detail.morphology or ""):
        return True
    normalized_gram = re.sub(r"\s+", "", (detail.gram_raw or "").lower())
    return normalized_gram.startswith("sb")
