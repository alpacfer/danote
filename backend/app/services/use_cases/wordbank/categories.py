from __future__ import annotations

from collections.abc import Iterable


STARTER_WORD_CATEGORY_LABELS: tuple[str, ...] = (
    "Animals",
    "Plants",
    "Food",
    "Drinks",
    "Family",
    "People",
    "Body",
    "Clothing",
    "Home",
    "Household Objects",
    "Nature",
    "Weather",
    "Places",
    "Transport",
    "Work",
    "School",
    "Health",
    "Time",
    "Actions",
    "Emotions",
)

_STARTER_CATEGORY_LABELS_BY_KEY = {
    " ".join(label.strip().split()).casefold(): label for label in STARTER_WORD_CATEGORY_LABELS
}


def normalize_word_category_key(label: str | None) -> str | None:
    if not isinstance(label, str):
        return None
    cleaned = " ".join(label.strip().split())
    if not cleaned:
        return None
    return cleaned.casefold()


def canonicalize_word_category_label(label: str | None) -> str | None:
    key = normalize_word_category_key(label)
    if key is None:
        return None
    starter_match = _STARTER_CATEGORY_LABELS_BY_KEY.get(key)
    if starter_match is not None:
        return starter_match
    words = key.split(" ")
    return " ".join(word[:1].upper() + word[1:] for word in words if word)


def normalize_word_category_labels(labels: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for label in labels:
        canonical = canonicalize_word_category_label(label)
        key = normalize_word_category_key(canonical)
        if canonical is None or key is None or key in seen:
            continue
        seen.add(key)
        normalized.append(canonical)
    return normalized
