from __future__ import annotations

import re
from dataclasses import dataclass


EDGE_PUNCT_PATTERN = re.compile(r"^[^\wæøåÆØÅ]+|[^\wæøåÆØÅ]+$", flags=re.UNICODE)


def normalize_apostrophes(token: str) -> str:
    return token.replace("’", "'").replace("`", "'")


def normalize_for_typo_compare(token: str) -> str:
    cleaned = normalize_apostrophes(token.strip().lower())
    while True:
        updated = EDGE_PUNCT_PATTERN.sub("", cleaned)
        if updated == cleaned:
            break
        cleaned = updated
    return cleaned


@dataclass(frozen=True)
class ComparisonForms:
    normalized: str
    alternates: tuple[str, ...]


def comparison_forms(token: str) -> ComparisonForms:
    normalized = normalize_for_typo_compare(token)
    alternates: set[str] = {normalized}
    if not normalized:
        return ComparisonForms(normalized="", alternates=())

    for source, target in (("ae", "æ"), ("oe", "ø"), ("aa", "å")):
        if source in normalized:
            alternates.add(normalized.replace(source, target))
        if target in normalized:
            alternates.add(normalized.replace(target, source))

    return ComparisonForms(
        normalized=normalized,
        alternates=tuple(sorted(value for value in alternates if value)),
    )
