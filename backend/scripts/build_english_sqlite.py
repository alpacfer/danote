#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.en_local_builder import build_english_sqlite


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build local English SQLite database from JSONL.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("resources/dictionaries/english_wiki.jsonl"),
        help="Input English JSONL file path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("resources/dictionaries/english_wiki.sqlite"),
        help="Output SQLite file path.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10_000,
        help="Batch size for inserts.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    stats = build_english_sqlite(
        input_path=args.input,
        output_path=args.output,
        batch_size=args.batch_size,
    )
    print(
        json.dumps(
            {
                "input": str(args.input),
                "output": str(args.output),
                "total_rows": stats.total_rows,
                "inserted_entries": stats.inserted_entries,
                "inserted_forms": stats.inserted_forms,
                "skipped_rows": stats.skipped_rows,
                "skipped_multiword": stats.skipped_multiword,
                "skipped_non_english": stats.skipped_non_english,
                "skipped_empty": stats.skipped_empty,
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
