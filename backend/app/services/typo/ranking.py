from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import math
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
    prior_score: float = 0.0
    error_likelihood: float = 0.0


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
        prior_score = _prior_score(candidate.frequency)
        error_likelihood = _error_likelihood(token, candidate.value)
        source_boost = 0.15 if "from_user_dict" in candidate.source_flags else 0.0
        frequency_score = prior_score * 0.1
        lemma_family_boost = 0.1 if candidate.value in known_lemmas else 0.0
        total = (
            (0.28 * distance_score)
            + (0.22 * similarity)
            + (0.20 * error_likelihood)
            + source_boost
            + frequency_score
            + lemma_family_boost
        )
        ranked.append(
            RankedCandidate(
                value=candidate.value,
                score=max(0.0, min(1.0, total)),
                source_flags=candidate.source_flags,
                distance=candidate.distance,
                prior_score=prior_score,
                error_likelihood=error_likelihood,
            )
        )

    return sorted(ranked, key=lambda item: (-item.score, item.distance, item.value))


def _similarity(a: str, b: str) -> float:
    if fuzz is not None:
        return float(fuzz.ratio(a, b)) / 100.0
    return SequenceMatcher(a=a, b=b).ratio()


def _prior_score(frequency: float) -> float:
    # Log-scale frequency so large dictionary counts do not dominate ranking.
    return max(0.0, min(1.0, math.log1p(max(frequency, 0.0)) / math.log1p(200.0)))


def _error_likelihood(observed: str, candidate: str) -> float:
    cost = _weighted_edit_cost(observed, candidate)
    scale = max(len(observed), len(candidate), 1)
    return max(0.0, min(1.0, math.exp(-(cost / scale))))


_DANISH_SUBSTITUTION_COSTS: dict[tuple[str, str], float] = {
    ("a", "å"): 0.35,
    ("å", "a"): 0.35,
    ("o", "ø"): 0.35,
    ("ø", "o"): 0.35,
    ("e", "æ"): 0.45,
    ("æ", "e"): 0.45,
}


def _weighted_edit_cost(observed: str, candidate: str) -> float:
    if observed == candidate:
        return 0.0
    a = observed.lower()
    b = candidate.lower()
    m = len(a)
    n = len(b)
    dp = [[0.0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        dp[i][0] = dp[i - 1][0] + 1.0
    for j in range(1, n + 1):
        dp[0][j] = dp[0][j - 1] + 1.0

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            replace_cost = 0.0 if a[i - 1] == b[j - 1] else _substitution_cost(a[i - 1], b[j - 1])
            best = min(
                dp[i - 1][j] + 1.0,
                dp[i][j - 1] + 1.0,
                dp[i - 1][j - 1] + replace_cost,
            )
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                best = min(best, dp[i - 2][j - 2] + 0.6)
            dp[i][j] = best

    return dp[m][n]


def _substitution_cost(source: str, target: str) -> float:
    if (source, target) in _DANISH_SUBSTITUTION_COSTS:
        return _DANISH_SUBSTITUTION_COSTS[(source, target)]
    return 1.0
