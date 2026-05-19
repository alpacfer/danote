from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _settings(tmp_path, **overrides) -> Settings:
    base = dict(
        environment="test",
        app_name="danote-backend-test",
        host="127.0.0.1",
        port=8001,
        db_path=tmp_path / "danote.sqlite3",
        nlp_model="retired-dacy-disabled",
        auth_enabled=True,
        guest_daily_search_limit=20,
    )
    base.update(overrides)
    return Settings(**base)


def _create_guest(client: TestClient, browser_id: str = "browser-123456") -> str:
    response = client.post("/api/guest/sessions", json={"browser_id": browser_id})
    assert response.status_code == 200
    token = response.json()["token"]
    assert token.startswith("guest_")
    return token


def test_guest_session_token_can_access_scoped_routes(tmp_path, stub_nlp_adapter_factory) -> None:
    app = create_app(
        settings=_settings(tmp_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        token = _create_guest(client)
        me = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["auth_provider"] == "guest"

        lemmas = client.get("/api/wordbank/lemmas", headers={"Authorization": f"Bearer {token}"})
        assert lemmas.status_code == 200


def test_guest_session_starts_with_fresh_workspace(tmp_path, stub_nlp_adapter_factory) -> None:
    app = create_app(
        settings=_settings(tmp_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        first_token = _create_guest(client)
        second_token = _create_guest(client)

        first_headers = {"Authorization": f"Bearer {first_token}"}
        second_headers = {"Authorization": f"Bearer {second_token}"}
        add = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "hus", "lemma_candidate": "hus"},
            headers=first_headers,
        )
        assert add.status_code == 200

        first_list = client.get("/api/wordbank/lemmas", headers=first_headers)
        second_list = client.get("/api/wordbank/lemmas", headers=second_headers)
        assert [item["lemma"] for item in first_list.json()["items"]] == ["hus"]
        assert second_list.json()["items"] == []


def test_guest_api_key_mutation_is_forbidden(tmp_path, stub_nlp_adapter_factory) -> None:
    app = create_app(
        settings=_settings(tmp_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        token = _create_guest(client)
        response = client.put(
            "/api/account/api-keys/gemini",
            json={"value": "not-a-real-key"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "guest_api_keys_forbidden"


def test_invalid_guest_token_returns_401(tmp_path, stub_nlp_adapter_factory) -> None:
    app = create_app(
        settings=_settings(tmp_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/me",
            headers={"Authorization": "Bearer guest_missing"},
        )

    assert response.status_code == 401
