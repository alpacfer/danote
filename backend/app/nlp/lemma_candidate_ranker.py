from __future__ import annotations

from collections.abc import Iterable


_INFLECTION_SUFFIXES = (
    "ens",
    "ets",
    "es",
    "en",
    "et",
    "erne",
    "ene",
    "er",
    "est",
    "st",
    "ede",
    "te",
    "s",
    "t",
)
_LOW_CONFIDENCE_TAGS = {"", "X", "PUNCT", "SYM"}
_VERB_LIKE_TAGS = {"VERB", "AUX"}

# Tuned deterministic weights for the extended Danish benchmark.
_SOURCE_PRIMARY_BONUS = -0.50
_SOURCE_FALLBACK_PENALTY = 1.10
_SURFACE_MATCH_BONUS = -1.10
_LENGTH_WEIGHT = 0.25
_LENGTH_DELTA_WEIGHT = -1.10
_INFLECTION_SUFFIX_PENALTY = 1.90
_VERY_SHORT_BONUS = -0.80
_LOW_CONFIDENCE_TAG_PENALTY = 0.90
_VERB_TAG_BONUS = -1.00
_INDEX_WEIGHT = 0.14
_PREFIX_REDUCTION_BONUS = -0.12


def normalize_candidate(text: str) -> str:
    return " ".join(text.strip().split()).lower()


def merge_candidates(primary_tag_candidates: Iterable[str], fallback_candidates: Iterable[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()

    for raw in list(primary_tag_candidates) + list(fallback_candidates):
        candidate = normalize_candidate(raw)
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        merged.append(candidate)

    return merged


def rank_candidates(
    surface: str,
    tag: str | None,
    candidates: Iterable[str],
    primary_tag_candidates: Iterable[str] | None = None,
) -> list[str]:
    normalized_surface = normalize_candidate(surface)
    normalized_tag = (tag or "").upper()
    normalized_candidates = []
    for raw_candidate in candidates:
        candidate = normalize_candidate(raw_candidate)
        if candidate:
            normalized_candidates.append(candidate)
    if not normalized_candidates:
        return []

    primary_set = {
        normalize_candidate(candidate)
        for candidate in (primary_tag_candidates or [])
        if normalize_candidate(candidate)
    }

    scored: list[tuple[float, int, str]] = []
    for index, candidate in enumerate(normalized_candidates):
        score = 0.0
        if normalized_tag not in _LOW_CONFIDENCE_TAGS:
            score += _SOURCE_PRIMARY_BONUS if candidate in primary_set else _SOURCE_FALLBACK_PENALTY
        if candidate == normalized_surface:
            score += _SURFACE_MATCH_BONUS
        score += _LENGTH_WEIGHT * len(candidate)
        score += _LENGTH_DELTA_WEIGHT * abs(len(normalized_surface) - len(candidate))
        if candidate.endswith(_INFLECTION_SUFFIXES):
            score += _INFLECTION_SUFFIX_PENALTY
        if len(candidate) <= 2:
            score += _VERY_SHORT_BONUS
        if normalized_tag in _LOW_CONFIDENCE_TAGS:
            score += _LOW_CONFIDENCE_TAG_PENALTY
        if normalized_tag in _VERB_LIKE_TAGS:
            score += _VERB_TAG_BONUS
        if len(normalized_surface) > len(candidate) and normalized_surface.startswith(candidate):
            score += _PREFIX_REDUCTION_BONUS
        score += _INDEX_WEIGHT * index
        scored.append((score, index, candidate))

    scored.sort(key=lambda item: (item[0], item[1], item[2]))
    ranked = [candidate for _, _, candidate in scored]

    # Very short Danish nouns can over-collapse (e.g. "hus" -> "hu").
    if normalized_tag == "NOUN" and len(normalized_surface) <= 3 and normalized_surface in ranked:
        return [normalized_surface] + [candidate for candidate in ranked if candidate != normalized_surface]

    return ranked


def pick_best_candidate(
    surface: str,
    tag: str | None,
    primary_tag_candidates: Iterable[str],
    fallback_candidates: Iterable[str],
) -> str | None:
    merged = merge_candidates(primary_tag_candidates, fallback_candidates)
    ranked = rank_candidates(
        surface=surface,
        tag=tag,
        candidates=merged,
        primary_tag_candidates=primary_tag_candidates,
    )
    return ranked[0] if ranked else None


def pick_best_candidate_in_lexicon(
    surface: str,
    tag: str | None,
    primary_tag_candidates: Iterable[str],
    fallback_candidates: Iterable[str],
    lexeme_set: set[str],
) -> str | None:
    merged = merge_candidates(primary_tag_candidates, fallback_candidates)
    ranked = rank_candidates(
        surface=surface,
        tag=tag,
        candidates=merged,
        primary_tag_candidates=primary_tag_candidates,
    )
    for candidate in ranked:
        if candidate in lexeme_set:
            return candidate
    return None
