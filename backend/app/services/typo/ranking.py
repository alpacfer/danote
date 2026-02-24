from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable

from app.services.typo.candidates import Candidate

try:
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover - optional dependency
    fuzz = None


@dataclass(frozen=True)
class RankedCandidate:
    value: str
    score: float
    source_flags: tuple[str, ...]
    distance: int


def rank_candidates(
    *,
    token: str,
    candidates: Iterable[Candidate],
    known_lemmas: set[str],
) -> list[RankedCandidate]:
    ranked: list[RankedCandidate] = []
    for candidate in candidates:
        similarity = _similarity(token, candidate.value)
        distance_score = max(0.0, 1.0 - (candidate.distance / max(len(token), len(candidate.value), 1)))
        source_boost = 0.15 if "from_user_dict" in candidate.source_flags else 0.0
        frequency_score = min(candidate.frequency / 200.0, 1.0) * 0.1
        lemma_family_boost = 0.1 if candidate.value in known_lemmas else 0.0
        total = (0.45 * distance_score) + (0.3 * similarity) + source_boost + frequency_score + lemma_family_boost
        ranked.append(
            RankedCandidate(
                value=candidate.value,
                score=max(0.0, min(1.0, total)),
                source_flags=candidate.source_flags,
                distance=candidate.distance,
            )
        )

    return sorted(ranked, key=lambda item: (-item.score, item.distance, item.value))


def _similarity(a: str, b: str) -> float:
    if fuzz is not None:
        return float(fuzz.ratio(a, b)) / 100.0
    return SequenceMatcher(a=a, b=b).ratio()
