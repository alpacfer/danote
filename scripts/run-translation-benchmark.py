#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from app.services.translation import ArgosTranslationService, TranslationError
from benchmark_reporting import append_benchmark_report


ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT_DIR / "test-data" / "fixtures" / "translation" / "translation_words.da_en.v1.json"


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    source_word: str
    acceptable: tuple[str, ...]


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    source_word: str
    expected: tuple[str, ...]
    predicted: str | None
    matched: bool
    provider_error: str | None
    is_word_output: bool


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _is_single_word(text: str) -> bool:
    normalized = _normalize(text)
    if not normalized or " " in normalized:
        return False
    has_letter = False
    for char in normalized:
        if char == "-":
            continue
        if not char.isalpha():
            return False
        has_letter = True
    return has_letter


def _load_cases(path: Path) -> list[BenchmarkCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Translation fixture must be a list of case objects")

    cases: list[BenchmarkCase] = []
    seen_ids: set[str] = set()

    for idx, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Fixture item {idx} must be an object")

        case_id = str(item.get("id", "")).strip()
        da = str(item.get("da", "")).strip()
        acceptable_raw = item.get("acceptable", [])

        if not case_id:
            raise ValueError(f"Fixture item {idx} is missing non-empty 'id'")
        if case_id in seen_ids:
            raise ValueError(f"Duplicate fixture id: {case_id}")
        seen_ids.add(case_id)

        if not _is_single_word(da):
            raise ValueError(f"Fixture case {case_id} source is not a single word: {da!r}")

        if not isinstance(acceptable_raw, list) or not acceptable_raw:
            raise ValueError(f"Fixture case {case_id} must have non-empty 'acceptable' list")

        acceptable: list[str] = []
        for value in acceptable_raw:
            text = str(value).strip()
            normalized_target = _normalize(text)
            if not normalized_target:
                raise ValueError(f"Fixture case {case_id} has empty acceptable target")
            acceptable.append(normalized_target)

        cases.append(
            BenchmarkCase(
                case_id=case_id,
                source_word=_normalize(da),
                acceptable=tuple(dict.fromkeys(acceptable)),
            )
        )

    return cases


def run(*, max_failures: int) -> int:
    cases = _load_cases(FIXTURE_PATH)
    service = ArgosTranslationService()

    total = len(cases)
    exact_passed = 0
    word_output_passed = 0
    provider_errors = 0
    results: list[CaseResult] = []

    for case in cases:
        predicted: str | None = None
        provider_error: str | None = None
        try:
            predicted = service.translate_da_to_en(case.source_word)
        except TranslationError as exc:
            provider_error = str(exc)
            provider_errors += 1

        normalized_prediction = _normalize(predicted) if isinstance(predicted, str) else None
        is_word_output = bool(normalized_prediction and _is_single_word(normalized_prediction))
        matched = bool(normalized_prediction and normalized_prediction in case.acceptable)

        if is_word_output:
            word_output_passed += 1
        if matched:
            exact_passed += 1

        results.append(
            CaseResult(
                case_id=case.case_id,
                source_word=case.source_word,
                expected=case.acceptable,
                predicted=normalized_prediction,
                matched=matched,
                provider_error=provider_error,
                is_word_output=is_word_output,
            )
        )

    effective_total = total - provider_errors
    exact_accuracy = (exact_passed / total * 100.0) if total else 0.0
    exact_accuracy_effective = (exact_passed / effective_total * 100.0) if effective_total else 0.0
    word_output_rate = (word_output_passed / total * 100.0) if total else 0.0
    availability = (effective_total / total * 100.0) if total else 0.0

    failures = [
        result
        for result in results
        if (not result.matched) or result.provider_error
    ]

    print("Danote Translation Benchmark (word-only)")
    print(f"Fixture: {FIXTURE_PATH.relative_to(ROOT_DIR)}")
    print(f"Cases: {total}")
    print(f"Provider availability: {effective_total}/{total} ({availability:.1f}%)")
    print(f"Word-output rate: {word_output_passed}/{total} ({word_output_rate:.1f}%)")
    print(f"Exact match accuracy (all cases): {exact_passed}/{total} ({exact_accuracy:.1f}%)")
    print(
        "Exact match accuracy (successful provider responses): "
        f"{exact_passed}/{effective_total} ({exact_accuracy_effective:.1f}%)"
        if effective_total
        else "Exact match accuracy (successful provider responses): n/a"
    )

    if failures:
        print("")
        print(f"Top failures (max {max_failures}):")
        for result in failures[:max_failures]:
            expected = ", ".join(result.expected)
            if result.provider_error:
                print(
                    f"- {result.case_id} '{result.source_word}' -> provider_error="
                    f"{result.provider_error} (expected: {expected})"
                )
                continue

            predicted = result.predicted or "<none>"
            print(
                f"- {result.case_id} '{result.source_word}' -> '{predicted}' "
                f"(expected one of: {expected}; word_output={result.is_word_output})"
            )

    report_path = append_benchmark_report(
        benchmark="translation",
        run_data={
            "fixture": str(FIXTURE_PATH.relative_to(ROOT_DIR)),
            "summary": {
                "provider_availability": {
                    "available": effective_total,
                    "total": total,
                    "rate": round(availability, 2),
                },
                "word_output": {
                    "passed": word_output_passed,
                    "total": total,
                    "rate": round(word_output_rate, 2),
                },
                "exact_match": {
                    "passed": exact_passed,
                    "total": total,
                    "accuracy": round(exact_accuracy, 2),
                },
                "exact_match_successful_provider": {
                    "passed": exact_passed,
                    "total": effective_total,
                    "accuracy": round(exact_accuracy_effective, 2),
                },
            },
            "top_failures": [
                {
                    "id": result.case_id,
                    "source_word": result.source_word,
                    "expected": list(result.expected),
                    "predicted": result.predicted,
                    "is_word_output": result.is_word_output,
                    "provider_error": result.provider_error,
                }
                for result in failures[:max_failures]
            ],
        },
    )
    print(f"Report updated: {report_path.relative_to(ROOT_DIR)}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Danote word-only translation benchmark.")
    parser.add_argument(
        "--max-failures",
        type=int,
        default=20,
        help="Maximum number of failing cases to print.",
    )
    args = parser.parse_args()
    return run(max_failures=max(args.max_failures, 0))


if __name__ == "__main__":
    raise SystemExit(main())
