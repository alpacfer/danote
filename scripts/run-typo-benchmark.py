#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.core.config import Settings
from app.db.migrations import apply_migrations, get_connection
from app.nlp.danish import load_danish_nlp_adapter
from app.services.token_classifier import LemmaAwareClassifier, normalize_token
from app.services.typo.typo_engine import TypoEngine


ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT_DIR / "test-data" / "fixtures" / "typo"
DICTIONARY_PATH = ROOT_DIR / "backend" / "resources" / "dictionaries" / "da_words.txt"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _seed_lemmas(db_path: Path, lemmas: list[str]) -> None:
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM surface_forms")
        conn.execute("DELETE FROM lexemes")
        for lemma in lemmas:
            conn.execute(
                "INSERT OR IGNORE INTO lexemes (lemma, source) VALUES (?, 'manual')",
                (normalize_token(lemma),),
            )


def main() -> int:
    token_cases = _load_json(FIXTURES_DIR / "typo_tokens_by_error_type.extended.json")
    class_cases = _load_json(FIXTURES_DIR / "typo_classification_impact.extended.json")
    edge_cases = _load_json(FIXTURES_DIR / "typo_on_new_word_edge_cases.extended.json")

    with tempfile.TemporaryDirectory(prefix="danote-typo-benchmark-") as tmp_dir:
        db_path = Path(tmp_dir) / "benchmark.sqlite3"
        apply_migrations(db_path)
        settings = Settings(
            environment="test",
            app_name="danote-typo-benchmark",
            host="127.0.0.1",
            port=8001,
            db_path=db_path,
            nlp_model="da_dacy_small_tft-0.0.0",
        )
        adapter = load_danish_nlp_adapter(settings)
        typo_engine = TypoEngine(db_path=db_path, dictionary_path=DICTIONARY_PATH)
        classifier = LemmaAwareClassifier(db_path, nlp_adapter=adapter, typo_engine=typo_engine)

        total = 0
        passed = 0
        top1_passed = 0

        for case in token_cases:
            _seed_lemmas(db_path, case["db_seed_lexemes"])
            result = classifier.classify(case["input_token"])
            total += 1
            if result.classification == case["expected_status"]:
                passed += 1
            expected_top = case.get("expected_top_candidate") or ""
            predicted_top = result.suggestions[0].value if result.suggestions else ""
            if not expected_top or expected_top == predicted_top:
                top1_passed += 1

        for case in class_cases + edge_cases:
            _seed_lemmas(db_path, case["db_seed_lexemes"])
            result = classifier.classify(case["surface"])
            total += 1
            if result.classification == case["expected_status"]:
                passed += 1

        accuracy = (passed / total * 100.0) if total else 0.0
        top1 = (top1_passed / len(token_cases) * 100.0) if token_cases else 0.0
        print("Danote Typo Benchmark (v1 scaffold)")
        print(f"Cases: {total}")
        print(f"Status accuracy: {passed}/{total} ({accuracy:.1f}%)")
        print(f"Top-1 accuracy (token set): {top1_passed}/{len(token_cases)} ({top1:.1f}%)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
