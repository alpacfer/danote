#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.migrations import apply_migrations
from app.db.seed import seed_starter_data
from app.main import create_app


ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT_DIR / "test-data" / "fixtures"
NOTES_DIR = FIXTURES_DIR / "notes"
EXPECTED_ANALYZE_DIR = FIXTURES_DIR / "expected" / "analyze"
CASES_FILE = FIXTURES_DIR / "analysis-cases.json"


def load_cases() -> list[dict[str, str]]:
    return json.loads(CASES_FILE.read_text(encoding="utf-8"))


def generate() -> None:
    cases = load_cases()
    EXPECTED_ANALYZE_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="danote-regression-") as temp_dir:
        db_path = Path(temp_dir) / "danote.sqlite3"
        apply_migrations(db_path)
        seed_starter_data(db_path)

        settings = Settings(
            environment="test",
            app_name="danote-regression-golden",
            host="127.0.0.1",
            port=8001,
            db_path=db_path,
            nlp_model="da_dacy_small_trf-0.2.0",
        )

        app = create_app(settings=settings)
        with TestClient(app) as client:
            for case in cases:
                note_path = NOTES_DIR / case["note_file"]
                expected_path = EXPECTED_ANALYZE_DIR / case["expected_file"]
                text = note_path.read_text(encoding="utf-8")

                response = client.post("/api/analyze", json={"text": text})
                if response.status_code != 200:
                    raise RuntimeError(
                        f"Failed to analyze fixture '{case['id']}' ({response.status_code}): {response.text}"
                    )

                expected_path.write_text(
                    json.dumps(response.json(), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                print(f"[golden] wrote {expected_path.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    generate()
