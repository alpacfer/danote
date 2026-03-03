#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.cor_local_builder import build_cor_sqlite


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build local COR SQLite database from TSV.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("resources/dictionaries/cor1.5.1.0.tsv"),
        help="Input COR TSV file path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("resources/dictionaries/cor.sqlite"),
        help="Output SQLite file path.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50_000,
        help="Batch size for inserts.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    stats = build_cor_sqlite(
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
                "inserted_rows": stats.inserted_rows,
                "skipped_rows": stats.skipped_rows,
                "malformed_id_rows": stats.malformed_id_rows,
                "malformed_column_rows": stats.malformed_column_rows,
                "missing_required_rows": stats.missing_required_rows,
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
