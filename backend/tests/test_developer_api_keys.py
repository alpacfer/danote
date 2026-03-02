from fastapi.testclient import TestClient

from app.main import create_app


def test_developer_api_keys_endpoint_updates_runtime_health(stub_nlp_adapter_factory) -> None:
    app = create_app(nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        response = client.post(
            "/api/developer/api-keys",
            json={
                "translation_azure_api_key": "translator-key",
                "translation_azure_region": "westeurope",
                "tts_azure_api_key": "speech-key",
                "tts_azure_region": "westeurope",
                "word_verification_gemini_api_key": "",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "updated"
        assert payload["configured"]["translation_azure"] is True
        assert payload["configured"]["tts_azure"] is True

        health = client.get("/api/health")
        assert health.status_code == 200
        health_payload = health.json()
        assert health_payload["apis"]["azure_translator"]["configured"] is True
        assert health_payload["apis"]["azure_speech"]["configured"] is True
