#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.db.migrations import apply_migrations, get_connection
from app.nlp.danish import load_danish_nlp_adapter
from app.services.token_classifier import LemmaAwareClassifier, normalize_token


ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT_DIR / "test-data" / "fixtures" / "lemma"


@dataclass(frozen=True)
class CaseResult:
    category: str
    passed: bool


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _metric(results: list[CaseResult]) -> tuple[int, int, float]:
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    accuracy = (passed / total * 100.0) if total else 0.0
    return passed, total, accuracy


def run() -> None:
    token_cases = _load_json(FIXTURES_DIR / "lemma_tokens_by_category.json")
    context_cases = _load_json(FIXTURES_DIR / "lemma_sentences_context.json")
    classification_cases = _load_json(FIXTURES_DIR / "classification_impact_variation.json")
    robustness_cases = _load_json(FIXTURES_DIR / "lemma_robustness_noise.json")

    with tempfile.TemporaryDirectory(prefix="danote-lemma-benchmark-") as tmp_dir:
        db_path = Path(tmp_dir) / "benchmark.sqlite3"
        apply_migrations(db_path)
        settings = Settings(
            environment="test",
            app_name="danote-lemma-benchmark",
            host="127.0.0.1",
            port=8001,
            db_path=db_path,
            nlp_model="da_dacy_small_tft-0.0.0",
        )
        adapter = load_danish_nlp_adapter(settings)

        token_results: list[CaseResult] = []
        context_results: list[CaseResult] = []
        class_results: list[CaseResult] = []
        robust_results: list[CaseResult] = []

        for case in token_cases:
            predicted = normalize_token(adapter.lemma_for_token(case["surface"]) or "")
            expected = normalize_token(case["expected_lemma"])
            token_results.append(CaseResult(case["category"], predicted == expected))

        for case in context_cases:
            predicted = ""
            for token in adapter.tokenize(case["sentence"]):
                if normalize_token(token.text) == normalize_token(case["target_token"]):
                    predicted = normalize_token(token.lemma or "")
                    break
            if not predicted:
                predicted = normalize_token(adapter.lemma_for_token(case["target_token"]) or "")
            expected = normalize_token(case["expected_lemma"])
            context_results.append(CaseResult(case["category"], predicted == expected))

        for case in classification_cases:
            apply_migrations(db_path)
            with get_connection(db_path) as conn:
                conn.execute("DELETE FROM surface_forms")
                conn.execute("DELETE FROM lexemes")
                for lemma in case["db_seed_lexemes"]:
                    conn.execute(
                        "INSERT OR IGNORE INTO lexemes (lemma, source) VALUES (?, 'manual')",
                        (normalize_token(lemma),),
                    )
            classifier = LemmaAwareClassifier(db_path, nlp_adapter=adapter)
            status = classifier.classify(case["surface"]).classification
            class_results.append(CaseResult(case["category"], status == case["expected_status"]))

        for case in robustness_cases:
            ok = True
            try:
                _ = adapter.tokenize(case["text"])
                _ = adapter.lemma_for_token(case["text"])
            except Exception:
                ok = False
            robust_results.append(CaseResult(case["category"], ok))

        category_map: dict[str, list[CaseResult]] = defaultdict(list)
        for group in (token_results, context_results, class_results, robust_results):
            for result in group:
                category_map[result.category].append(result)

        lemma_passed, lemma_total, lemma_accuracy = _metric(token_results + context_results)
        class_passed, class_total, class_accuracy = _metric(class_results)
        robust_passed, robust_total, robust_accuracy = _metric(robust_results)

        print("Danote Lemma Benchmark (Checkpoint 18)")
        print(f"Lemma accuracy: {lemma_passed}/{lemma_total} ({lemma_accuracy:.1f}%)")
        print(f"Classification impact accuracy: {class_passed}/{class_total} ({class_accuracy:.1f}%)")
        print(f"Robustness pass rate: {robust_passed}/{robust_total} ({robust_accuracy:.1f}%)")
        print("")
        print("Per-category:")
        for category in sorted(category_map):
            passed, total, accuracy = _metric(category_map[category])
            print(f"- {category}: {passed}/{total} ({accuracy:.1f}%)")


if __name__ == "__main__":
    run()
