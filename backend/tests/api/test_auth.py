from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _settings(tmp_path, *, auth_enabled: bool) -> Settings:
    return Settings(
        environment="test",
        app_name="danote-backend-test",
        host="127.0.0.1",
        port=8001,
        db_path=tmp_path / "danote.sqlite3",
        nlp_model="retired-dacy-disabled",
        auth_enabled=auth_enabled,
        clerk_issuer="https://example.clerk.accounts.dev",
        clerk_jwks_url="https://example.clerk.accounts.dev/.well-known/jwks.json",
    )


def test_me_returns_local_user_when_auth_disabled(tmp_path, stub_nlp_adapter_factory) -> None:
    app = create_app(
        settings=_settings(tmp_path, auth_enabled=False),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        response = client.get("/api/me")

    assert response.status_code == 200
    assert response.json()["auth_subject"] == "local-dev"


def test_protected_route_rejects_missing_bearer_token(tmp_path, stub_nlp_adapter_factory) -> None:
    app = create_app(
        settings=_settings(tmp_path, auth_enabled=True),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        response = client.get("/api/wordbank/lemmas")

    assert response.status_code == 401
