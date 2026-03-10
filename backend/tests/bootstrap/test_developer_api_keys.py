from fastapi.testclient import TestClient

from app.core.app_state import set_service_field
from app.core.config import load_settings
from app.main import create_app
from app.services.tts import PronunciationAudio


def test_developer_api_keys_endpoint_updates_runtime_health(stub_nlp_adapter_factory) -> None:
    app = create_app(nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        response = client.post(
            "/api/developer/api-keys",
            json={
                "gemini_api_key": "gemini-key",
                "translation_provider": "deepl",
                "translation_deepl_api_key": "deepl-key",
                "tts_azure_api_key": "speech-key",
                "tts_azure_region": "westeurope",
                "word_verification_gemini_api_key": "",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "updated"
        assert payload["configured"]["gemini"] is True
        assert payload["configured"]["translation_deepl"] is True
        assert payload["configured"]["tts_azure"] is True

        health = client.get("/api/health")
        assert health.status_code == 200
        health_payload = health.json()
        assert health_payload["apis"]["deepl_translator"]["configured"] is True
        assert health_payload["apis"]["azure_speech"]["configured"] is True
        assert health_payload["apis"]["gemini"]["configured"] is True


def test_developer_gemini_probe_endpoint_returns_result(stub_nlp_adapter_factory) -> None:
    app = create_app(nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubGeminiWordTranslationService:
        provider = "gemini_word_translation"

        def translate_word(self, payload) -> str | None:
            if payload.surface_form == "bogen" and payload.lemma == "bog" and payload.gloss == "book":
                return "the book"
            return None

    with TestClient(app) as client:
        set_service_field(client.app, "gemini_word_translation_service", StubGeminiWordTranslationService())
        response = client.post("/api/developer/gemini-probe")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "probe_input": "bogen",
        "result_text": "the book",
        "provider": "gemini_word_translation",
        "message": "Gemini probe completed successfully.",
    }


def test_developer_gemini_probe_endpoint_reports_missing_service(stub_nlp_adapter_factory, tmp_path) -> None:
    app = create_app(
        settings=load_settings(env_file=tmp_path / "missing.env"),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        response = client.post("/api/developer/gemini-probe")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["probe_input"] == "bogen"
    assert payload["result_text"] is None
    assert payload["provider"] is None


def test_developer_translation_probe_endpoint_returns_result(stub_nlp_adapter_factory) -> None:
    app = create_app(nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        provider = "azure_translator"

        def translate_da_to_en(self, text: str) -> str | None:
            return "the book" if text == "bogen" else None

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        response = client.post("/api/developer/translation-probe")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "probe_input": "bogen",
        "result_text": "the book",
        "provider": "azure_translator",
        "message": "Azure Translator probe completed successfully.",
    }


def test_developer_tts_probe_endpoint_returns_audio_summary(stub_nlp_adapter_factory) -> None:
    app = create_app(nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTtsService:
        provider = "azure_speech_tts"

        def synthesize(self, text: str) -> PronunciationAudio | None:
            if text != "bogen":
                return None
            return PronunciationAudio(audio_bytes=b"1234", mime_type="audio/wav")

    with TestClient(app) as client:
        set_service_field(client.app, "tts_service", StubTtsService())
        response = client.post("/api/developer/tts-probe")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "probe_input": "bogen",
        "result_text": "audio/wav (4 bytes)",
        "provider": "azure_speech_tts",
        "message": "Azure Speech probe completed successfully.",
    }
