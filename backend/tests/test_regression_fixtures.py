from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.migrations import apply_migrations
from app.db.seed import seed_starter_data
from app.main import create_app


FIXTURES_DIR = Path(__file__).resolve().parents[2] / "test-data" / "fixtures"
NOTES_DIR = FIXTURES_DIR / "notes"
EXPECTED_ANALYZE_DIR = FIXTURES_DIR / "expected" / "analyze"
CASES_FILE = FIXTURES_DIR / "analysis-cases.json"
MODEL = "da_dacy_small_trf-0.2.0"


def _load_cases() -> list[dict[str, str]]:
    return json.loads(CASES_FILE.read_text(encoding="utf-8"))


CASES = _load_cases()


@pytest.fixture(scope="module")
def regression_client(tmp_path_factory) -> TestClient:
    tmp_dir = tmp_path_factory.mktemp("regression-fixtures")
    db_path = tmp_dir / "danote.sqlite3"

    apply_migrations(db_path)
    seed_starter_data(db_path)

    settings = Settings(
        environment="test",
        app_name="danote-backend-regression",
        host="127.0.0.1",
        port=8001,
        db_path=db_path,
        nlp_model=MODEL,
    )

    app = create_app(settings=settings)
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_analysis_fixture_matches_golden(case: dict[str, str], regression_client: TestClient) -> None:
    note_path = NOTES_DIR / case["note_file"]
    expected_path = EXPECTED_ANALYZE_DIR / case["expected_file"]

    assert note_path.exists(), f"missing note fixture: {note_path}"
    assert expected_path.exists(), f"missing expected fixture: {expected_path}"

    note_text = note_path.read_text(encoding="utf-8")
    expected_payload = json.loads(expected_path.read_text(encoding="utf-8"))

    response = regression_client.post("/api/analyze", json={"text": note_text})
    assert response.status_code == 200
    assert response.json() == expected_payload
