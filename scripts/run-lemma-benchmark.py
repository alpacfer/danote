#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.db.migrations import apply_migrations, get_connection
from app.nlp.danish import load_danish_nlp_adapter
from app.nlp.token_filter import is_wordlike_token
from app.services.token_classifier import LemmaAwareClassifier, normalize_token
from benchmark_reporting import append_benchmark_report


ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT_DIR / "test-data" / "fixtures" / "lemma"
TOKEN_FIXTURE = "lemma_tokens_by_category.extended.json"
CONTEXT_FIXTURE = "lemma_sentences_context.extended.json"
CLASSIFICATION_FIXTURE = "classification_impact_variation.extended.json"
ROBUSTNESS_FIXTURE = "lemma_robustness_noise.extended.json"
EDGE_PUNCT_PATTERN = re.compile(r"^[^\wæøåÆØÅ]+|[^\wæøåÆØÅ]+$", flags=re.UNICODE)
DEFAULT_MIN_LEMMA_ACCURACY = 95.0
DEFAULT_MIN_CLASSIFICATION_ACCURACY = 98.0
DEFAULT_MIN_ROBUSTNESS_ACCURACY = 95.0
DEFAULT_MAX_FALSE_VARIATION_RATE = 0.0


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    category: str
    passed: bool
    expected: str
    predicted: str


@dataclass(frozen=True)
class StatusResult:
    case_id: str
    category: str
    passed: bool
    expected: str
    predicted: str


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


def _metric(results: list[CaseResult] | list[StatusResult]) -> tuple[int, int, float]:
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    accuracy = (passed / total * 100.0) if total else 0.0
    return passed, total, accuracy


def _strip_edge_punctuation(token: str) -> str:
    cleaned = token.strip()
    while True:
        updated = EDGE_PUNCT_PATTERN.sub("", cleaned)
        if updated == cleaned:
            break
        cleaned = updated
    return cleaned


def _seed_lemmas(db_path: Path, lemmas: list[str]) -> None:
    apply_migrations(db_path)
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM surface_forms")
        conn.execute("DELETE FROM lexemes")
        for lemma in lemmas:
            conn.execute(
                "INSERT OR IGNORE INTO lexemes (lemma, source) VALUES (?, 'manual')",
                (normalize_token(lemma),),
            )


def run(
    *,
    enforce_targets: bool = False,
    allow_degraded_nlp: bool = False,
    min_lemma_accuracy: float = DEFAULT_MIN_LEMMA_ACCURACY,
    min_classification_accuracy: float = DEFAULT_MIN_CLASSIFICATION_ACCURACY,
    min_robustness_accuracy: float = DEFAULT_MIN_ROBUSTNESS_ACCURACY,
    max_false_variation_rate: float = DEFAULT_MAX_FALSE_VARIATION_RATE,
) -> int:
    token_cases = _load_json(FIXTURES_DIR / TOKEN_FIXTURE)
    context_cases = _load_json(FIXTURES_DIR / CONTEXT_FIXTURE)
    classification_cases = _load_json(FIXTURES_DIR / CLASSIFICATION_FIXTURE)
    robustness_cases = _load_json(FIXTURES_DIR / ROBUSTNESS_FIXTURE)

    with tempfile.TemporaryDirectory(prefix="danote-lemma-benchmark-") as tmp_dir:
        db_path = Path(tmp_dir) / "benchmark.sqlite3"
        apply_migrations(db_path)
        settings = Settings(
            environment="test",
            app_name="danote-lemma-benchmark",
            host="127.0.0.1",
            port=8001,
            db_path=db_path,
            nlp_model="da_dacy_small_trf-0.2.0",
        )
        adapter_warning: str | None = None
        try:
            adapter = load_danish_nlp_adapter(settings)
        except Exception as exc:  # pragma: no cover - environment fallback
            if not allow_degraded_nlp:
                print("Danote Lemma Benchmark (Checkpoint 18 MVB)")
                print(
                    "Failed to load Danish NLP adapter. "
                    "Enable model download/network access or run with --allow-degraded-nlp."
                )
                print(f"Error: {exc}")
                return 2
            adapter = _IdentityNLPAdapter()
            adapter_warning = f"NLP adapter unavailable; using identity fallback: {exc}"

        token_results: list[CaseResult] = []
        context_results: list[CaseResult] = []
        class_results: list[StatusResult] = []
        robust_results: list[StatusResult] = []
        failures: list[CaseResult | StatusResult] = []

        for case in token_cases:
            predicted = normalize_token(adapter.lemma_for_token(case["surface"]) or "")
            expected = normalize_token(case["expected_lemma"])
            result = CaseResult(
                case_id=case["id"],
                category=case["category"],
                passed=predicted == expected,
                expected=expected,
                predicted=predicted,
            )
            token_results.append(result)
            if not result.passed:
                failures.append(result)

        for case in context_cases:
            predicted = ""
            for token in adapter.tokenize(case["sentence"]):
                if normalize_token(token.text) == normalize_token(case["target_token"]):
                    predicted = normalize_token(token.lemma or "")
                    break
            if not predicted:
                predicted = normalize_token(adapter.lemma_for_token(case["target_token"]) or "")
            expected = normalize_token(case["expected_lemma"])
            result = CaseResult(
                case_id=case["id"],
                category=case["category"],
                passed=predicted == expected,
                expected=expected,
                predicted=predicted,
            )
            context_results.append(result)
            if not result.passed:
                failures.append(result)

        for case in classification_cases:
            _seed_lemmas(db_path, case["db_seed_lexemes"])
            classifier = LemmaAwareClassifier(db_path, nlp_adapter=adapter)
            status = classifier.classify(case["surface"]).classification
            result = StatusResult(
                case_id=case["id"],
                category=case["category"],
                passed=status == case["expected_status"],
                expected=case["expected_status"],
                predicted=status,
            )
            class_results.append(result)
            if not result.passed:
                failures.append(result)

        for case in robustness_cases:
            if case["mode"] == "single_token":
                _seed_lemmas(db_path, case["db_seed_lexemes"])
                classifier = LemmaAwareClassifier(db_path, nlp_adapter=adapter)
                cleaned_token = _strip_edge_punctuation(case["input_token"])
                status_result = classifier.classify(cleaned_token)
                expected_status = case["expected_status"]
                expected_lemma = normalize_token(case.get("expected_lemma", ""))
                predicted_lemma = normalize_token(status_result.lemma_candidate or status_result.matched_lemma or "")
                passed = status_result.classification == expected_status
                if expected_lemma:
                    passed = passed and predicted_lemma == expected_lemma

                result = StatusResult(
                    case_id=case["id"],
                    category=case["category"],
                    passed=passed,
                    expected=f"{expected_status}:{expected_lemma}",
                    predicted=f"{status_result.classification}:{predicted_lemma}",
                )
                robust_results.append(result)
                if not result.passed:
                    failures.append(result)
                continue

            if case["mode"] == "note_text":
                _seed_lemmas(db_path, case["db_seed_lexemes"])
                classifier = LemmaAwareClassifier(db_path, nlp_adapter=adapter)
                predicted_sequence: list[tuple[str, str]] = []
                for token in adapter.tokenize(case["input_text"]):
                    if not token.text.strip() or token.is_punctuation:
                        continue
                    if not is_wordlike_token(token.text):
                        continue
                    status_result = classifier.classify(token.text)
                    predicted_sequence.append((status_result.normalized_token, status_result.classification))

                expected_sequence = [
                    (item["normalized_token"], item["expected_status"])
                    for item in case["expected_sequence"]
                ]
                passed = predicted_sequence == expected_sequence
                result = StatusResult(
                    case_id=case["id"],
                    category=case["category"],
                    passed=passed,
                    expected=str(expected_sequence),
                    predicted=str(predicted_sequence),
                )
                robust_results.append(result)
                if not result.passed:
                    failures.append(result)
                continue

            unknown = StatusResult(
                case_id=case["id"],
                category=case["category"],
                passed=False,
                expected="recognized mode",
                predicted=str(case.get("mode")),
            )
            robust_results.append(unknown)
            failures.append(unknown)

        category_map: dict[str, list[CaseResult]] = defaultdict(list)
        for group in (token_results, context_results):
            for result in group:
                category_map[result.category].append(result)
        category_status_map: dict[str, list[StatusResult]] = defaultdict(list)
        for group in (class_results, robust_results):
            for result in group:
                category_status_map[result.category].append(result)

        lemma_passed, lemma_total, lemma_accuracy = _metric(token_results + context_results)
        lemma_coverage = sum(
            1
            for result in token_results + context_results
            if bool(result.predicted)
        )
        lemma_coverage_rate = (lemma_coverage / lemma_total * 100.0) if lemma_total else 0.0
        token_passed, token_total, token_accuracy = _metric(token_results)
        context_passed, context_total, context_accuracy = _metric(context_results)
        context_gain = context_accuracy - token_accuracy

        class_passed, class_total, class_accuracy = _metric(class_results)
        variation_cases = [result for result in class_results if result.expected == "variation"]
        variation_passed, variation_total, variation_accuracy = _metric(variation_cases)
        new_cases = [result for result in class_results if result.expected == "new"]
        false_variation = sum(1 for result in new_cases if result.predicted == "variation")
        false_variation_rate = (false_variation / len(new_cases) * 100.0) if new_cases else 0.0
        false_new = sum(1 for result in variation_cases if result.predicted == "new")
        false_new_rate = (false_new / len(variation_cases) * 100.0) if variation_cases else 0.0

        robust_passed, robust_total, robust_accuracy = _metric(robust_results)

        print("Danote Lemma Benchmark (Checkpoint 18 MVB)")
        print("Policies: case-insensitive DB lookup, edge punctuation stripped for single-token robustness tests")
        if adapter_warning:
            print(f"Warning: {adapter_warning}")
        print("")
        print(f"Lemma accuracy: {lemma_passed}/{lemma_total} ({lemma_accuracy:.1f}%)")
        print(f"Lemma coverage: {lemma_coverage}/{lemma_total} ({lemma_coverage_rate:.1f}%)")
        print(f"Token-only lemma accuracy: {token_passed}/{token_total} ({token_accuracy:.1f}%)")
        print(f"Sentence-context lemma accuracy: {context_passed}/{context_total} ({context_accuracy:.1f}%)")
        print(f"Context gain: {context_gain:+.1f} pp")
        print("")
        print(f"Classification impact accuracy: {class_passed}/{class_total} ({class_accuracy:.1f}%)")
        print(
            "Variation accuracy: "
            f"{variation_passed}/{variation_total} ({variation_accuracy:.1f}%)"
        )
        print(f"False variation rate (expected new -> predicted variation): {false_variation_rate:.1f}%")
        print(f"False new rate (expected variation -> predicted new): {false_new_rate:.1f}%")
        print("")
        print(f"Robustness pass rate: {robust_passed}/{robust_total} ({robust_accuracy:.1f}%)")
        print("")
        print("Per-category (lemma):")
        for category in sorted(category_map):
            passed, total, accuracy = _metric(category_map[category])
            print(f"- {category}: {passed}/{total} ({accuracy:.1f}%)")
        print("")
        print("Per-category (classification/robustness):")
        for category in sorted(category_status_map):
            passed, total, accuracy = _metric(category_status_map[category])
            print(f"- {category}: {passed}/{total} ({accuracy:.1f}%)")

        print("")
        print("Top failures (up to 20):")
        if not failures:
            print("- none")
        else:
            for result in failures[:20]:
                print(
                    f"- {result.case_id} [{result.category}] "
                    f"expected={result.expected} predicted={result.predicted}"
                )

        report_path = append_benchmark_report(
            benchmark="lemma",
            run_data={
                "summary": {
                    "lemma": {
                        "passed": lemma_passed,
                        "total": lemma_total,
                        "accuracy": round(lemma_accuracy, 2),
                        "coverage": {
                            "passed": lemma_coverage,
                            "total": lemma_total,
                            "rate": round(lemma_coverage_rate, 2),
                        },
                    },
                    "token": {
                        "passed": token_passed,
                        "total": token_total,
                        "accuracy": round(token_accuracy, 2),
                    },
                    "context": {
                        "passed": context_passed,
                        "total": context_total,
                        "accuracy": round(context_accuracy, 2),
                        "gain_pp": round(context_gain, 2),
                    },
                    "classification": {
                        "passed": class_passed,
                        "total": class_total,
                        "accuracy": round(class_accuracy, 2),
                        "variation_accuracy": round(variation_accuracy, 2),
                        "false_variation_rate": round(false_variation_rate, 2),
                        "false_new_rate": round(false_new_rate, 2),
                    },
                    "robustness": {
                        "passed": robust_passed,
                        "total": robust_total,
                        "accuracy": round(robust_accuracy, 2),
                    },
                },
                "per_category": {
                    "lemma": {
                        category: {
                            "passed": _metric(category_map[category])[0],
                            "total": _metric(category_map[category])[1],
                            "accuracy": round(_metric(category_map[category])[2], 2),
                        }
                        for category in sorted(category_map)
                    },
                    "classification_robustness": {
                        category: {
                            "passed": _metric(category_status_map[category])[0],
                            "total": _metric(category_status_map[category])[1],
                            "accuracy": round(_metric(category_status_map[category])[2], 2),
                        }
                        for category in sorted(category_status_map)
                    },
                },
                "top_failures": [
                    {
                        "id": result.case_id,
                        "category": result.category,
                        "expected": result.expected,
                        "predicted": result.predicted,
                    }
                    for result in failures[:20]
                ],
                "enforce_targets": enforce_targets,
                "adapter_warning": adapter_warning,
                "targets": {
                    "min_lemma_accuracy": min_lemma_accuracy,
                    "min_classification_accuracy": min_classification_accuracy,
                    "min_robustness_accuracy": min_robustness_accuracy,
                    "max_false_variation_rate": max_false_variation_rate,
                },
            },
        )
        print("")
        print(f"Report updated: {report_path.relative_to(ROOT_DIR)}")

        if not enforce_targets:
            return 0

        threshold_failures: list[str] = []
        if lemma_accuracy < min_lemma_accuracy:
            threshold_failures.append(
                f"lemma accuracy {lemma_accuracy:.1f}% < {min_lemma_accuracy:.1f}%"
            )
        if class_accuracy < min_classification_accuracy:
            threshold_failures.append(
                f"classification accuracy {class_accuracy:.1f}% < {min_classification_accuracy:.1f}%"
            )
        if robust_accuracy < min_robustness_accuracy:
            threshold_failures.append(
                f"robustness accuracy {robust_accuracy:.1f}% < {min_robustness_accuracy:.1f}%"
            )
        if false_variation_rate > max_false_variation_rate:
            threshold_failures.append(
                f"false variation rate {false_variation_rate:.1f}% > {max_false_variation_rate:.1f}%"
            )

        print("")
        print("Target checks:")
        if not threshold_failures:
            print("- passed")
            return 0

        for failure in threshold_failures:
            print(f"- failed: {failure}")
        return 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Danote lemma benchmark.")
    parser.add_argument(
        "--enforce-targets",
        action="store_true",
        help="Exit non-zero when accuracy thresholds are not met.",
    )
    parser.add_argument(
        "--allow-degraded-nlp",
        action="store_true",
        help="Allow identity NLP fallback when Danish model is unavailable.",
    )
    parser.add_argument(
        "--min-lemma-accuracy",
        type=float,
        default=DEFAULT_MIN_LEMMA_ACCURACY,
    )
    parser.add_argument(
        "--min-classification-accuracy",
        type=float,
        default=DEFAULT_MIN_CLASSIFICATION_ACCURACY,
    )
    parser.add_argument(
        "--min-robustness-accuracy",
        type=float,
        default=DEFAULT_MIN_ROBUSTNESS_ACCURACY,
    )
    parser.add_argument(
        "--max-false-variation-rate",
        type=float,
        default=DEFAULT_MAX_FALSE_VARIATION_RATE,
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    sys.exit(
        run(
            enforce_targets=args.enforce_targets,
            allow_degraded_nlp=args.allow_degraded_nlp,
            min_lemma_accuracy=args.min_lemma_accuracy,
            min_classification_accuracy=args.min_classification_accuracy,
            min_robustness_accuracy=args.min_robustness_accuracy,
            max_false_variation_rate=args.max_false_variation_rate,
        )
    )
