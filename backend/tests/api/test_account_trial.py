from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from app.api.auth import CurrentUser
from app.api.routes import wordbank_search
from app.core.config import Settings
from app.db.migrations import apply_migrations, get_connection
from app.main import create_app

_TEST_ENCRYPTION_SECRET = base64.b64encode(bytes(32)).decode()


def _settings(tmp_path, **overrides) -> Settings:
    base = dict(
        environment="test",
        app_name="danote-backend-test",
        host="127.0.0.1",
        port=8001,
        db_path=tmp_path / "danote.sqlite3",
        nlp_model="retired-dacy-disabled",
    )
    base.update(overrides)
    return Settings(**base)


def test_status_includes_trial_block(tmp_path, stub_nlp_adapter_factory) -> None:
    app = create_app(
        settings=_settings(tmp_path, key_encryption_secret=_TEST_ENCRYPTION_SECRET),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        response = client.get("/api/account/status")

    assert response.status_code == 200
    body = response.json()
    assert body["keys_configured"] is False
    trial = body["trial"]
    assert trial["enabled"] is True
    assert trial["keys_configured"] is False
    assert trial["opted_in"] is False
    assert trial["limit"] == 50
    assert trial["used"] == 0
    assert trial["remaining"] == 50


def test_opt_in_marks_opted_in(tmp_path, stub_nlp_adapter_factory) -> None:
    app = create_app(
        settings=_settings(tmp_path, key_encryption_secret=_TEST_ENCRYPTION_SECRET),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        opt_in = client.post("/api/account/trial/opt-in")
        assert opt_in.status_code == 200
        assert opt_in.json()["trial"]["opted_in"] is True

        status = client.get("/api/account/status")
        assert status.json()["trial"]["opted_in"] is True


def test_fresh_start_clears_learning_data_but_keeps_keys_and_usage(tmp_path, stub_nlp_adapter_factory) -> None:
    settings = _settings(tmp_path, key_encryption_secret=_TEST_ENCRYPTION_SECRET)
    app = create_app(settings=settings, nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        client.put("/api/account/api-keys/gemini", json={"value": "test-gemini-key"})
        client.post("/api/wordbank/lexemes", json={"surface_token": "bogen", "lemma_candidate": "bog"})
        client.post(
            "/api/sentencebank/sentences",
            json={"source_text": "bogen er her", "english_translation": "the book is here"},
        )
        with get_connection(settings.db_path) as conn:
            conn.execute(
                """
                INSERT INTO user_search_usage (owner_user_id, usage_date, query_key)
                VALUES (1, '2026-05-20', 'bog')
                """,
            )
            lexeme = conn.execute("SELECT id FROM lexemes WHERE lemma = ?", ("bog",)).fetchone()
            assert lexeme is not None
            conn.execute(
                """
                INSERT INTO wordbank_categories (label, normalized_label)
                VALUES ('Pirate Lore', 'pirate lore')
                """
            )
            category = conn.execute(
                "SELECT id FROM wordbank_categories WHERE normalized_label = 'pirate lore'"
            ).fetchone()
            assert category is not None
            conn.execute(
                """
                INSERT INTO wordbank_category_assignments (lexeme_id, meaning_id, category_id)
                VALUES (?, NULL, ?)
                """,
                (int(lexeme["id"]), int(category["id"])),
            )

        response = client.delete("/api/account/data")

    assert response.status_code == 200
    assert response.json()["status"] == "reset"

    with get_connection(settings.db_path) as conn:
        lexemes = conn.execute("SELECT COUNT(*) AS count FROM lexemes").fetchone()
        sentences = conn.execute("SELECT COUNT(*) AS count FROM sentence_bank").fetchone()
        keys = conn.execute("SELECT COUNT(*) AS count FROM user_api_keys").fetchone()
        usage = conn.execute("SELECT COUNT(*) AS count FROM user_search_usage").fetchone()
        custom_categories = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM wordbank_categories
            WHERE normalized_label = 'pirate lore'
            """
        ).fetchone()
        starter_categories = conn.execute("SELECT COUNT(*) AS count FROM wordbank_categories").fetchone()

    assert lexemes["count"] == 0
    assert sentences["count"] == 0
    assert keys["count"] == 1
    assert usage["count"] == 1
    assert custom_categories["count"] == 0
    assert starter_categories["count"] == 67


def test_search_returns_429_when_trial_limit_exceeded(
    tmp_path, stub_nlp_adapter_factory, monkeypatch
) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)

    fake_user = CurrentUser(
        id=1,
        email="trial@danote.local",
        auth_provider="clerk",
        auth_subject="clerk-trial",
        display_name="Trial User",
        created_at="",
        last_seen_at="",
    )
    monkeypatch.setattr(wordbank_search, "require_current_user", lambda _request: fake_user)

    app = create_app(
        settings=_settings(
            tmp_path,
            auth_enabled=True,
            clerk_jwks_url="https://example.clerk.accounts.dev/.well-known/jwks.json",
            trial_daily_search_limit=0,
        ),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        response = client.get("/api/wordbank/search/en-form", params={"form": "house"})

    assert response.status_code == 429
    assert response.json()["detail"] == "trial_daily_limit_reached"
