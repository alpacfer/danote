from __future__ import annotations

import json
from pathlib import Path


FIXTURES_DIR = Path(__file__).resolve().parents[2] / "test-data" / "fixtures"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_fixture_pack_structure_and_seed_baseline() -> None:
    assert (FIXTURES_DIR / "analysis-cases.json").exists()
    assert (FIXTURES_DIR / "notes").is_dir()
    assert (FIXTURES_DIR / "expected" / "analyze").is_dir()
    assert (FIXTURES_DIR / "lemma").is_dir()

    seed = _load_json(FIXTURES_DIR / "seed" / "starter_seed.json")
    lemmas = {item["lemma"] for item in seed["lexemes"]}
    assert {"bog", "kan", "lide"}.issubset(lemmas)


def test_analysis_cases_reference_existing_files() -> None:
    cases = _load_json(FIXTURES_DIR / "analysis-cases.json")

    for case in cases:
        note_path = FIXTURES_DIR / "notes" / case["note_file"]
        expected_path = FIXTURES_DIR / "expected" / "analyze" / case["expected_file"]
        assert note_path.exists(), f"missing note fixture: {note_path}"
        assert expected_path.exists(), f"missing expected fixture: {expected_path}"


def test_lemma_mvb_fixture_sizes_and_basic_schema() -> None:
    token_cases = _load_json(FIXTURES_DIR / "lemma" / "lemma_tokens_by_category.extended.json")
    context_cases = _load_json(FIXTURES_DIR / "lemma" / "lemma_sentences_context.extended.json")
    class_cases = _load_json(FIXTURES_DIR / "lemma" / "classification_impact_variation.extended.json")
    robust_cases = _load_json(FIXTURES_DIR / "lemma" / "lemma_robustness_noise.extended.json")

    assert len(token_cases) == 379
    assert len(context_cases) == 102
    assert len(class_cases) == 391
    assert len(robust_cases) == 75

    assert all({"id", "category", "surface", "expected_lemma"}.issubset(case) for case in token_cases)
    assert all(
        {"id", "category", "sentence", "target_token", "expected_lemma"}.issubset(case)
        for case in context_cases
    )
    assert all(
        {"id", "category", "db_seed_lexemes", "surface", "expected_status"}.issubset(case)
        for case in class_cases
    )
    assert all({"id", "category", "mode", "db_seed_lexemes"}.issubset(case) for case in robust_cases)
