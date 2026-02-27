from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import load_settings
from app.nlp.danish import load_danish_nlp_adapter

DEFAULT_DATASET_PATH = ROOT_DIR / "resources" / "benchmarks" / "pos_gold_dataset.json"


def _load_dataset(dataset_path: Path) -> list[dict[str, str]]:
    dataset = json.loads(dataset_path.read_text())
    return [item for item in dataset if item.get("word") and item.get("pos")]


def _predict_pos(adapter, word: str) -> str | None:
    for token in adapter.tokenize(word):
        if token.is_punctuation:
            continue
        return token.pos
    return None


def run_benchmark(iterations: int, warmup: int, dataset_path: Path) -> dict[str, object]:
    settings = load_settings()
    adapter = load_danish_nlp_adapter(settings)
    samples = _load_dataset(dataset_path)

    for _ in range(warmup):
        for sample in samples:
            _predict_pos(adapter, sample["word"])

    timings_ms: list[float] = []
    total_tokens = 0
    total_with_pos = 0

    for _ in range(iterations):
        started = time.perf_counter()
        for sample in samples:
            predicted = _predict_pos(adapter, sample["word"])
            total_tokens += 1
            if predicted:
                total_with_pos += 1
        timings_ms.append((time.perf_counter() - started) * 1000.0)

    predicted_by_word: dict[str, str | None] = {}
    mismatches: list[dict[str, str | None]] = []
    correct = 0
    gold_counter: Counter[str] = Counter()
    predicted_counter: Counter[str] = Counter()

    for sample in samples:
        word = sample["word"]
        gold = sample["pos"]
        predicted = _predict_pos(adapter, word)
        predicted_by_word[word] = predicted
        gold_counter[gold] += 1
        predicted_counter[predicted or "<none>"] += 1
        if predicted == gold:
            correct += 1
        else:
            mismatches.append({"word": word, "gold": gold, "predicted": predicted})

    accuracy = (correct / len(samples)) * 100.0 if samples else 0.0
    total_time_s = sum(timings_ms) / 1000.0

    return {
        "dataset_path": str(dataset_path.relative_to(ROOT_DIR)),
        "dataset_size": len(samples),
        "accuracy": {
            "correct": correct,
            "total": len(samples),
            "accuracy_pct": round(accuracy, 2),
            "mismatch_count": len(mismatches),
            "mismatches": mismatches,
        },
        "timing": {
            "iterations": iterations,
            "warmup": warmup,
            "mean_ms": round(statistics.mean(timings_ms), 3),
            "median_ms": round(statistics.median(timings_ms), 3),
            "min_ms": round(min(timings_ms), 3),
            "max_ms": round(max(timings_ms), 3),
            "tokens_per_second": round((total_tokens / total_time_s) if total_time_s > 0 else 0.0, 2),
            "pos_coverage_pct": round((total_with_pos / total_tokens) * 100.0, 2) if total_tokens else 0.0,
        },
        "class_distribution": {
            "gold": dict(sorted(gold_counter.items())),
            "predicted": dict(sorted(predicted_counter.items())),
        },
        "metadata": adapter.metadata(),
        "predictions": predicted_by_word,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark POS model speed and tagging accuracy")
    parser.add_argument("--iterations", type=int, default=50, help="Number of benchmark iterations")
    parser.add_argument("--warmup", type=int, default=3, help="Number of warmup iterations")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="Path to JSON dataset with [{word, pos}] entries",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.iterations < 1:
        raise SystemExit("--iterations must be >= 1")
    if args.warmup < 0:
        raise SystemExit("--warmup must be >= 0")
    if not args.dataset.exists():
        raise SystemExit(f"dataset not found: {args.dataset}")

    print(json.dumps(run_benchmark(args.iterations, args.warmup, args.dataset), ensure_ascii=True))
