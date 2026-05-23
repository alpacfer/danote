"""Smoke tests for the Gemini related-words prompt.

The prompt is structurally different for single-word lemmas (compound
decomposition) versus multi-word expressions (constituent words + near-synonym
MWEs). The lemma-aware branch is the change made during the MWE feature review.
"""

from __future__ import annotations

from app.services.related_words import GeminiCompoundRelatedWordsService


def _make_service() -> GeminiCompoundRelatedWordsService:
    """Instantiate the real service for prompt/parse testing. Tests never call
    `find_related_words`, so no Gemini client is initialized."""
    return GeminiCompoundRelatedWordsService(api_key="test-key", model="gemini-test")


def test_prompt_for_single_word_lemma_asks_for_compound_decomposition_only() -> None:
    svc = _make_service()
    prompt = svc._prompt("badeværelse")
    assert "ONLY for compound decomposition" in prompt
    # No MWE-specific instructions for single-word lemmas.
    assert "near-synonym" not in prompt
    assert "constituent" not in prompt


def test_prompt_for_multi_word_lemma_asks_for_constituents_and_near_synonyms() -> None:
    svc = _make_service()
    prompt = svc._prompt("passe på")

    # Multi-word lemma → MWE-branch prompt.
    assert "multi-word expression" in prompt
    assert "constituent" in prompt
    assert "reading order" in prompt
    assert "near-synonym" in prompt
    # The example demonstrates the expected decomposition shape.
    assert "passe" in prompt
    # ADP must be in the allowed POS list so prepositions like "på" survive parsing.
    assert "ADP" in prompt


def test_parse_response_accepts_adp_for_mwe_lemma() -> None:
    """For MWE lemmas the parser must accept ADP/CCONJ/SCONJ/PART, otherwise
    constituents like "på" (preposition) get silently dropped."""
    svc = _make_service()
    raw = (
        '{"is_compound": true, "items": ['
        '{"lemma": "passe", "english_translation": "to take care", "pos_tag": "VERB"},'
        '{"lemma": "på", "english_translation": "on", "pos_tag": "ADP"}'
        "]}"
    )
    result = svc._parse_response(raw, lemma="passe på")
    lemmas = {item.lemma for item in result.items}
    assert lemmas == {"passe", "på"}


def test_parse_response_rejects_adp_for_single_word_lemma() -> None:
    """Single-word compound decomposition should keep the strict POS allowlist —
    a preposition isn't a meaningful compound component for a single Danish word."""
    svc = _make_service()
    raw = (
        '{"is_compound": true, "items": ['
        '{"lemma": "bord", "english_translation": "table", "pos_tag": "NOUN"},'
        '{"lemma": "på", "english_translation": "on", "pos_tag": "ADP"}'
        "]}"
    )
    result = svc._parse_response(raw, lemma="bordlampe")
    lemmas = {item.lemma for item in result.items}
    assert lemmas == {"bord"}, "ADP must not appear in single-word compound decomposition"
