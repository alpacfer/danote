from __future__ import annotations

import json
import time

from fastapi.testclient import TestClient

from app.core.app_state import set_service_field
from app.db.migrations import apply_migrations, get_connection
from app.main import create_app
from tests.api.wordbank_test_support import build_test_settings


class _BlockingRelatedWordsService:
    provider = "gemini_related_words"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def find_related_words(self, *, lemma: str):
        self.calls.append(lemma)
        time.sleep(0.2)

        class Result:
            items = []

        return Result()


def test_add_word_saved_snapshot_includes_related_words_queued_status(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)
    related_words_service = _BlockingRelatedWordsService()

    with TestClient(app) as client:
        set_service_field(client.app, "gemini_related_words_service", related_words_service)
        response = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "legeplads", "lemma_candidate": "legeplads"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["saved_snapshot"]["related_words"]["status"] == "queued"
    assert payload["saved_snapshot"]["related_words"]["items"] == []

    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT dedupe_key, payload_json
            FROM wordbank_background_jobs
            WHERE job_type = 'resolve_related_words'
            LIMIT 1
            """
        ).fetchone()

    assert row is not None
    assert str(row["dedupe_key"]) == "resolve_related_words::legeplads"
    assert json.loads(str(row["payload_json"])) == {"stored_lemma": "legeplads"}
