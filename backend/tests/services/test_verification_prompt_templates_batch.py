from __future__ import annotations

from app.services.verification_prompt_templates import build_batch_verification_prompt


def test_batch_prompt_includes_sentence_context():
    entries = [{"word_id": 0, "lemma": "hus"}]
    prompt = build_batch_verification_prompt(entries=entries, sentence_context="Jeg har et hus")

    assert "sentence_context" in prompt
    assert "Jeg har et hus" in prompt


def test_batch_prompt_includes_multiple_entries():
    entries = [
        {"word_id": 0, "current_entry": {"lemma": "hus"}},
        {"word_id": 1, "current_entry": {"lemma": "kat"}},
    ]
    prompt = build_batch_verification_prompt(entries=entries, sentence_context="Hus og kat")

    assert '"word_id": 0' in prompt
    assert '"word_id": 1' in prompt
    assert '"lemma": "hus"' in prompt
    assert '"lemma": "kat"' in prompt


def test_batch_prompt_requests_results_array():
    entries = [{"word_id": 0, "current_entry": {"lemma": "hus"}}]
    prompt = build_batch_verification_prompt(entries=entries, sentence_context="hus")

    assert '"results"' in prompt
    assert '"word_id"' in prompt
    assert "JSON only" in prompt


def test_batch_prompt_includes_verification_rules():
    entries = [{"word_id": 0, "current_entry": {"lemma": "hus"}}]
    prompt = build_batch_verification_prompt(entries=entries, sentence_context="hus")

    assert "Translations belong to the lemma or meaning section only" in prompt
    assert "Surface forms do not have independent translations" in prompt
    assert "Never suggest editing a gloss" in prompt
    assert "idiomatic English" in prompt
