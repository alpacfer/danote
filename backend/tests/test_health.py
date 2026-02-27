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
    assert payload["components"] == {"database": "ok", "nlp": "ok"}


def test_cors_allows_configured_origin(tmp_path, stub_nlp_adapter_factory) -> None:
    settings = Settings(
        environment="test",
        app_name="danote-backend-test",
        host="127.0.0.1",
        port=8001,
        db_path=tmp_path / "danote.sqlite3",
        nlp_model="da_dacy_small_trf-0.2.0",
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
