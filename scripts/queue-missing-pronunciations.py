#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.config import load_settings
from app.services.use_cases.wordbank.pronunciation_repair import queue_missing_pronunciations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Queue merged wordbank pronunciation repair jobs for missing lemma and surface-form audio.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional env file to load before resolving the default database path.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Optional database path override. Defaults to DANOTE_DB_PATH from env or .env.local.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the lemmas/forms that would be queued without mutating the background job table.",
    )
    args = parser.parse_args()

    settings = load_settings(env_file=args.env_file)
    db_path = args.db_path or settings.db_path
    summary = queue_missing_pronunciations(db_path, dry_run=args.dry_run)

    mode = "dry-run" if args.dry_run else "queued"
    print(
        f"{mode}: {summary.lemma_count} lemma(s), {summary.form_count} form(s), "
        f"{summary.enqueued_jobs} enqueued job(s), {summary.unchanged_jobs} unchanged job(s)"
    )
    for lemma, forms in summary.queued_forms_by_lemma.items():
        print(f"{lemma}: {', '.join(forms)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
