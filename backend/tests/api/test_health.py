from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_route_returns_expected_shape(stub_nlp_adapter_factory) -> None:
    app = create_app(nlp_adapter_factory=stub_nlp_adapter_factory)
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "backend"
    assert payload["components"]["database"] == "ok"
    assert payload["components"]["nlp"] == "disabled"
    assert payload["components"]["translation"] in {"degraded", "ok", "disabled"}
    assert payload["components"]["tts"] in {"degraded", "ok", "disabled"}
    assert payload["apis"]["backend"]["status"] == "ok"
    assert "deepl_translator" in payload["apis"]
    assert "azure_translator" in payload["apis"]
    assert "azure_speech" in payload["apis"]


def test_health_route_reports_missing_key_and_disabled_provider_statuses(stub_nlp_adapter_factory, tmp_path) -> None:
    settings = Settings(
        environment="test",
        app_name="danote-backend-test",
        host="127.0.0.1",
        port=8001,
        db_path=tmp_path / "danote.sqlite3",
        nlp_model="retired-dacy-disabled",
        translation_enabled=True,
        translation_provider="deepl",
        tts_enabled=False,
    )
    app = create_app(settings=settings, nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["apis"]["deepl_translator"]["status"] == "missing_key"
    assert payload["apis"]["azure_translator"]["status"] == "inactive"
    assert payload["apis"]["azure_speech"]["status"] == "disabled"


def test_cors_allows_configured_origin(tmp_path, stub_nlp_adapter_factory) -> None:
    settings = Settings(
        environment="test",
        app_name="danote-backend-test",
        host="127.0.0.1",
        port=8001,
        db_path=tmp_path / "danote.sqlite3",
        nlp_model="retired-dacy-disabled",
        cors_origins=("http://127.0.0.1:5173",),
    )
    app = create_app(settings=settings, nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
