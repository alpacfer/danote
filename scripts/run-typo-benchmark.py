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
from benchmark_reporting import append_benchmark_report


ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT_DIR / "test-data" / "fixtures" / "typo"
DICTIONARY_DIR = ROOT_DIR / "backend" / "resources" / "dictionaries"
BASE_DICTIONARY_PATH = DICTIONARY_DIR / "da_words.txt"
DSDO_DICTIONARY_PATH = DICTIONARY_DIR / "dsdo.txt"


def _resolve_dictionary_paths(mode: str) -> tuple[Path, ...]:
    if mode == "base":
        return (BASE_DICTIONARY_PATH,)
    if mode == "combined":
        return (BASE_DICTIONARY_PATH, DSDO_DICTIONARY_PATH)
    raise ValueError(f"Unsupported dictionary mode: {mode}")


class _IdentityNLPAdapter:
    def tokenize(self, text: str):
        return []

    def lemma_candidates_for_token(self, token: str) -> list[str]:
        normalized = normalize_token(token)
        return [normalized] if normalized else []

    def lemma_for_token(self, token: str) -> str | None:
        normalized = normalize_token(token)
        return normalized or None

    def metadata(self) -> dict[str, str]:
        return {"adapter": "identity_fallback", "degraded": "true"}


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


def main(*, allow_degraded_nlp: bool = False, dictionary_mode: str = "combined") -> int:
    token_cases = _load_json(FIXTURES_DIR / "typo_tokens_by_error_type.extended.json")
    context_cases = _load_json(FIXTURES_DIR / "typo_sentences_context.extended.json")
    class_cases = _load_json(FIXTURES_DIR / "typo_classification_impact.extended.json")
    robustness_cases = _load_json(FIXTURES_DIR / "typo_robustness_noise.extended.json")
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
        adapter_warning: str | None = None
        try:
            adapter = load_danish_nlp_adapter(settings)
        except Exception as exc:  # pragma: no cover - environment fallback
            if not allow_degraded_nlp:
                print("Danote Typo Benchmark (v1 scaffold)")
                print(
                    "Failed to load Danish NLP adapter. "
                    "Enable model download/network access or run with --allow-degraded-nlp."
                )
                print(f"Error: {exc}")
                return 2
            adapter = _IdentityNLPAdapter()
            adapter_warning = f"NLP adapter unavailable; using identity fallback: {exc}"
        dictionary_paths = _resolve_dictionary_paths(dictionary_mode)
        typo_engine = TypoEngine(db_path=db_path, dictionary_paths=dictionary_paths)
        classifier = LemmaAwareClassifier(db_path, nlp_adapter=adapter, typo_engine=typo_engine)

        total = 0
        passed = 0
        top1_passed = 0
        failures: list[dict[str, str]] = []

        for case in token_cases:
            _seed_lemmas(db_path, case["db_seed_lexemes"])
            result = classifier.classify(case["input_token"])
            total += 1
            if result.classification == case["expected_status"]:
                passed += 1
            else:
                failures.append(
                    {
                        "id": case["id"],
                        "category": case["category"],
                        "expected": case["expected_status"],
                        "predicted": result.classification,
                    }
                )
            expected_top = case.get("expected_top_candidate") or ""
            predicted_top = result.suggestions[0].value if result.suggestions else ""
            if not expected_top or expected_top == predicted_top:
                top1_passed += 1

        for case in context_cases:
            _seed_lemmas(db_path, case["db_seed_lexemes"])
            result = classifier.classify(case["target_token"])
            total += 1
            if result.classification == case["expected_status"]:
                passed += 1
            else:
                failures.append(
                    {
                        "id": case["id"],
                        "category": case["category"],
                        "expected": case["expected_status"],
                        "predicted": result.classification,
                    }
                )

        for case in class_cases + edge_cases:
            _seed_lemmas(db_path, case["db_seed_lexemes"])
            result = classifier.classify(case["surface"])
            total += 1
            if result.classification == case["expected_status"]:
                passed += 1
            else:
                failures.append(
                    {
                        "id": case["id"],
                        "category": case["category"],
                        "expected": case["expected_status"],
                        "predicted": result.classification,
                    }
                )

        robustness_total = 0
        robustness_passed = 0
        for case in robustness_cases:
            if case.get("mode") != "single_token":
                continue
            _seed_lemmas(db_path, case["db_seed_lexemes"])
            result = classifier.classify(case["input_token"])
            robustness_total += 1
            if result.classification == case["expected_status"]:
                robustness_passed += 1

        accuracy = (passed / total * 100.0) if total else 0.0
        top1 = (top1_passed / len(token_cases) * 100.0) if token_cases else 0.0
        print("Danote Typo Benchmark (v1 scaffold)")
        if adapter_warning:
            print(f"Warning: {adapter_warning}")
        print(f"Cases: {total}")
        print(f"Status accuracy: {passed}/{total} ({accuracy:.1f}%)")
        print(f"Top-1 accuracy (token set): {top1_passed}/{len(token_cases)} ({top1:.1f}%)")
        print(f"Dictionary mode: {dictionary_mode} ({len(dictionary_paths)} source files)")

        report_path = append_benchmark_report(
            benchmark="typo",
            run_data={
                "dictionary_mode": dictionary_mode,
                "dictionary_paths": [str(path.relative_to(ROOT_DIR)) for path in dictionary_paths],
                "summary": {
                    "status_accuracy": {
                        "passed": passed,
                        "total": total,
                        "accuracy": round(accuracy, 2),
                    },
                    "top1_token_accuracy": {
                        "passed": top1_passed,
                        "total": len(token_cases),
                        "accuracy": round(top1, 2),
                    },
                    "robustness_single_token_accuracy": {
                        "passed": robustness_passed,
                        "total": robustness_total,
                        "accuracy": round(
                            (robustness_passed / robustness_total * 100.0) if robustness_total else 0.0,
                            2,
                        ),
                    },
                    "case_counts": {
                        "token": len(token_cases),
                        "context": len(context_cases),
                        "classification": len(class_cases),
                        "edge": len(edge_cases),
                    },
                },
                "adapter_warning": adapter_warning,
                "top_failures": failures[:20],
            },
        )
        print(f"Report updated: {report_path.relative_to(ROOT_DIR)}")

    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the Danote typo benchmark.")
    parser.add_argument(
        "--allow-degraded-nlp",
        action="store_true",
        help="Allow identity NLP fallback when Danish model is unavailable.",
    )
    parser.add_argument(
        "--dictionary-mode",
        choices=["base", "combined"],
        default="combined",
        help="Dictionary set to benchmark: base (da_words) or combined (da_words + dsdo).",
    )
    args = parser.parse_args()
    raise SystemExit(
        main(
            allow_degraded_nlp=args.allow_degraded_nlp,
            dictionary_mode=args.dictionary_mode,
        )
    )
