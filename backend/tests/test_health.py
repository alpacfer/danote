from fastapi.testclient import TestClient

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
