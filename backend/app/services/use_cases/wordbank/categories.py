from __future__ import annotations

from collections.abc import Iterable

STARTER_WORD_CATEGORY_LABELS: tuple[str, ...] = (
    "Animal",
    "Plant",
    "Food",
    "Drink",
    "Family",
    "Person",
    "Body",
    "Clothing",
    "Home",
    "Furniture",
    "Tool",
    "Container",
    "Nature",
    "Weather",
    "Place",
    "Building",
    "Vehicle",
    "Travel",
    "Work",
    "School",
    "Learning",
    "Health",
    "Medicine",
    "Time",
    "Emotion",
    "Feeling",
    "Thought",
    "Communication",
    "Movement",
    "Care",
    "Conflict",
    "Relationship",
    "Technology",
    "Money",
    "Law",
    "Art",
    "Music",
    "Sport",
    "Science",
    "Religion",
    "Politics",
    "Grammar",
    "Color",
    "Material",
    "Quantity",
    "Number",
    "Size",
    "Shape",
    "Sound",
    "Light",
    "Water",
    "Fire",
    "Earth",
    "Air",
    "Business",
    "Education",
    "Culture",
    "Community",
    "Media",
    "Writing",
    "Reading",
    "Cooking",
    "Cleaning",
    "Play",
    "Sleep",
    "Creation",
    "Change",
)

_STARTER_CATEGORY_LABELS_BY_KEY = {
    " ".join(label.strip().split()).casefold(): label for label in STARTER_WORD_CATEGORY_LABELS
}

_LEGACY_CATEGORY_LABELS_BY_KEY = {
    "animals": "Animal",
    "plants": "Plant",
    "drinks": "Drink",
    "people": "Person",
    "places": "Place",
    "transport": "Vehicle",
    "emotions": "Emotion",
    "household objects": "Furniture",
}

_BLOCKED_CATEGORY_KEYS = {
    "action",
    "actions",
    "thing",
    "things",
    "object",
    "objects",
    "misc",
    "miscellaneous",
    "other",
    "general",
    "noun",
    "nouns",
    "verb",
    "verbs",
    "adjective",
    "adjectives",
    "adverb",
    "adverbs",
    "pronoun",
    "pronouns",
    "preposition",
    "prepositions",
    "conjunction",
    "conjunctions",
    "singular",
    "plural",
    "definite",
    "indefinite",
    "masculine",
    "feminine",
    "neuter",
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
    legacy_match = _LEGACY_CATEGORY_LABELS_BY_KEY.get(key)
    if legacy_match is not None:
        return legacy_match
    if not is_allowed_word_category_label(key):
        return None
    starter_match = _STARTER_CATEGORY_LABELS_BY_KEY.get(key)
    if starter_match is not None:
        return starter_match
    words = key.split(" ")
    return " ".join(word[:1].upper() + word[1:] for word in words if word)


def is_allowed_word_category_label(label: str | None) -> bool:
    key = normalize_word_category_key(label)
    if key is None:
        return False
    words = key.split(" ")
    if len(words) > 3:
        return False
    if len(key) > 40:
        return False
    if key in _BLOCKED_CATEGORY_KEYS:
        return False
    return any(character.isalpha() for character in key)


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
