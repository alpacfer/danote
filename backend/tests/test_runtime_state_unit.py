from fastapi.testclient import TestClient

from app.core.app_state import get_runtime_state, set_service_field
from app.main import create_app


def test_runtime_state_is_initialized_and_tracks_legacy_state(stub_nlp_adapter_factory) -> None:
    app = create_app(nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        runtime = get_runtime_state(client.app)
        assert runtime.settings.app_name
        assert runtime.db_ready is True

        client.app.state.translation_service = "stub-service"
        synced_runtime = get_runtime_state(client.app)
        assert synced_runtime.services.translation_service == "stub-service"

        set_service_field(client.app, "tts_service", "stub-tts")
        assert client.app.state.tts_service == "stub-tts"
