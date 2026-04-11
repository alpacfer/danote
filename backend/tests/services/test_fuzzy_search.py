from __future__ import annotations

import pytest

from app.services.fuzzy_search import levenshtein, fuzzy_suggest


def test_levenshtein_identical():
    assert levenshtein("hus", "hus") == 0


def test_levenshtein_single_insert():
    assert levenshtein("hus", "huse") == 1


def test_levenshtein_single_delete():
    assert levenshtein("huse", "hus") == 1


def test_levenshtein_single_replace():
    assert levenshtein("huse", "huke") == 1


def test_levenshtein_empty_a():
    assert levenshtein("", "hus") == 3


def test_levenshtein_empty_b():
    assert levenshtein("hus", "") == 3


def test_levenshtein_two_edits():
    assert levenshtein("biler", "bilen") == 1


def test_fuzzy_suggest_returns_closest():
    result = fuzzy_suggest("huse", ["hus", "bil", "huse"], max_distance=2)
    assert "hus" in result


def test_fuzzy_suggest_excludes_exact_match():
    result = fuzzy_suggest("huse", ["hus", "huse"])
    assert "huse" not in result


def test_fuzzy_suggest_excludes_by_length_prefilter():
    result = fuzzy_suggest("ab", ["abcdefgh"], max_distance=2)
    assert result == []


def test_fuzzy_suggest_respects_max_results():
    candidates = ["kat", "kar", "kan", "kab", "kas"]
    result = fuzzy_suggest("kaf", candidates, max_distance=1, max_results=3)
    assert len(result) <= 3


def test_fuzzy_suggest_case_insensitive():
    result = fuzzy_suggest("Huse", ["HUS", "Bil"], max_distance=2)
    assert "hus" in result


def test_fuzzy_suggest_no_match_returns_empty():
    result = fuzzy_suggest("xyz", ["abc", "def"], max_distance=1)
    assert result == []


def test_fuzzy_suggest_deduplicates_case_variants():
    result = fuzzy_suggest("huse", ["HUS", "hus"], max_distance=2)
    assert result.count("hus") == 1
