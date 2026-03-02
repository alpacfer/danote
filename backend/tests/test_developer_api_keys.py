from fastapi.testclient import TestClient

from app.main import create_app


def test_developer_api_keys_endpoint_updates_runtime_health(stub_nlp_adapter_factory) -> None:
    app = create_app(nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        response = client.post(
            "/api/developer/api-keys",
            json={
                "gemini_api_key": "",
                "deepl_api_key": "test-deepl-key",
                "word_verification_gemini_api_key": "",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "updated"
        assert payload["configured"]["deepl"] is True

        health = client.get("/api/health")
        assert health.status_code == 200
        health_payload = health.json()
        assert health_payload["apis"]["deepl"]["configured"] is True
