from __future__ import annotations

from typing import Iterable


def levenshtein(a: str, b: str) -> int:
    """Wagner-Fischer dynamic programming Levenshtein distance."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            curr.append(min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + (0 if ca == cb else 1)))
        prev = curr
    return prev[-1]


def fuzzy_suggest(
    query: str,
    candidates: Iterable[str],
    *,
    max_distance: int = 2,
    max_results: int = 3,
) -> list[str]:
    """Return up to max_results candidates within Levenshtein distance of query.

    - Comparison is case-insensitive; results are returned lowercased.
    - Exact matches (distance 0) are excluded — callers use this for typo correction only.
    - Pre-filters by length diff to keep scans fast over large vocabularies.
    """
    query_lower = query.lower()
    scored: list[tuple[int, str]] = []
    for candidate in candidates:
        candidate_lower = candidate.lower()
        if abs(len(query_lower) - len(candidate_lower)) > max_distance:
            continue
        dist = levenshtein(query_lower, candidate_lower)
        if 0 < dist <= max_distance:
            scored.append((dist, candidate_lower))
    scored.sort(key=lambda x: (x[0], x[1]))
    seen: set[str] = set()
    result: list[str] = []
    for _, word in scored:
        if word not in seen:
            seen.add(word)
            result.append(word)
        if len(result) >= max_results:
            break
    return result
