from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.migrations import apply_migrations, get_connection
from app.main import create_app


def _test_settings(db_path) -> Settings:
    return Settings(
        environment="test",
        app_name="danote-backend-test",
        host="127.0.0.1",
        port=8001,
        db_path=db_path,
        nlp_model="da_dacy_small_trf-0.2.0",
    )


def test_feedback_and_ignore_endpoints_persist_rows(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        ignore = client.post("/api/tokens/ignore", json={"token": "PLC", "scope": "global"})
        feedback = client.post(
            "/api/tokens/feedback",
            json={
                "raw_token": "spisr",
                "predicted_status": "typo_likely",
                "suggestions_shown": ["spiser"],
                "user_action": "replace",
                "chosen_value": "spiser",
            },
        )

    assert ignore.status_code == 200
    assert ignore.json()["status"] == "ignored"
    assert feedback.status_code == 200
    assert feedback.json()["status"] == "recorded"

    with get_connection(db_path) as conn:
        ignored = conn.execute("SELECT token FROM ignored_tokens WHERE token = ?", ("plc",)).fetchone()
        row = conn.execute("SELECT raw_token, user_action FROM typo_feedback").fetchone()
    assert ignored is not None
    assert row is not None
    assert row["raw_token"] == "spisr"
    assert row["user_action"] == "replace"
