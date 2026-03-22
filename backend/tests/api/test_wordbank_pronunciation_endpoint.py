from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.app_state import set_service_field
from app.db.migrations import apply_migrations, get_connection
from app.main import create_app
from app.services.tts import PronunciationAudio
from tests.api.wordbank_test_support import build_test_settings


def test_get_pronunciation_audio_returns_stored_audio(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTTSService:
        def synthesize(self, text: str) -> PronunciationAudio | None:
            if text == "katten":
                return PronunciationAudio(audio_bytes=b"wav-bytes", mime_type="audio/wav")
            return None

    with TestClient(app) as client:
        set_service_field(client.app, "tts_service", StubTTSService())
        add_response = client.post("/api/wordbank/lexemes", json={"surface_token": "Katten", "lemma_candidate": "kat"})
        assert add_response.status_code == 200
        response = client.get("/api/wordbank/pronunciation", params={"form": "katten"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.content == b"wav-bytes"


def test_get_pronunciation_audio_normalizes_l16_to_wav(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTTSService:
        def synthesize(self, text: str) -> PronunciationAudio | None:
            if text == "katten":
                return PronunciationAudio(audio_bytes=(b"\x00\x00" * 2400), mime_type="audio/l16;codec=pcm;rate=24000")
            return None

    with TestClient(app) as client:
        set_service_field(client.app, "tts_service", StubTTSService())
        add_response = client.post("/api/wordbank/lexemes", json={"surface_token": "Katten", "lemma_candidate": "kat"})
        assert add_response.status_code == 200
        response = client.get("/api/wordbank/pronunciation", params={"form": "katten"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.content[:4] == b"RIFF"


def test_apply_verification_changes_endpoint_updates_word_fields(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        add_response = client.post("/api/wordbank/lexemes", json={"surface_token": "Bogen", "lemma_candidate": "bog"})
        assert add_response.status_code == 200
        meaning_id = add_response.json()["meaning"]["id"]
        apply_response = client.post(
            "/api/wordbank/lexemes/apply-verification-changes",
            json={
                "stored_lemma": "bog",
                "stored_surface_form": None,
                "meaning_id": meaning_id,
                "provider": "gemini",
                "action": {
                    "action_type": "fix_translation",
                    "english_translation": "book",
                },
            },
        )

    assert apply_response.status_code == 200
    assert apply_response.json()["applied_action_type"] == "fix_translation"
    with get_connection(db_path) as conn:
        meaning_row = conn.execute(
            "SELECT english_translation FROM lexeme_meanings WHERE id = ?",
            (meaning_id,),
        ).fetchone()
    assert meaning_row is not None
    assert meaning_row["english_translation"] == "book"


def test_add_word_does_not_block_on_pronunciation_for_new_surface_form(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTTSService:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def synthesize(self, text: str) -> PronunciationAudio | None:
            self.calls.append(text)
            return PronunciationAudio(audio_bytes=b"wav-bytes", mime_type="audio/wav") if text == "katten" else None

    stub_tts = StubTTSService()
    with TestClient(app) as client:
        set_service_field(client.app, "tts_service", stub_tts)
        add_response = client.post("/api/wordbank/lexemes", json={"surface_token": "Katten", "lemma_candidate": "kat"})
        assert add_response.status_code == 200
        details_response = client.get("/api/wordbank/lemmas/kat")

    assert details_response.status_code == 200
    forms = details_response.json()["meaning_sections"][0]["surface_forms"]
    assert forms[0]["has_pronunciation"] is False
    assert stub_tts.calls == []


def test_generate_pronunciation_endpoint_generates_for_recently_added_word(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTTSService:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def synthesize(self, text: str) -> PronunciationAudio | None:
            self.calls.append(text)
            return PronunciationAudio(audio_bytes=b"wav-bytes", mime_type="audio/wav") if text == "katten" else None

    stub_tts = StubTTSService()
    with TestClient(app) as client:
        set_service_field(client.app, "tts_service", stub_tts)
        add_response = client.post("/api/wordbank/lexemes", json={"surface_token": "Katten", "lemma_candidate": "kat"})
        assert add_response.status_code == 200
        pronunciation_response = client.post("/api/wordbank/lexemes/pronunciation", json={"stored_lemma": "kat", "stored_surface_form": "katten"})
        details_response = client.get("/api/wordbank/lemmas/kat")

    assert pronunciation_response.status_code == 200
    pronounced_surface = next(
        item for item in details_response.json()["meaning_sections"][0]["surface_forms"] if item["form"] == "katten"
    )
    assert pronounced_surface["has_pronunciation"] is True
    assert "kat" in stub_tts.calls
    assert "katten" in stub_tts.calls


def test_generate_pronunciation_endpoint_force_regenerates_existing_audio(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTTSService:
        def __init__(self) -> None:
            self.calls: list[str] = []
            self._counter = 0

        def synthesize(self, text: str) -> PronunciationAudio | None:
            self.calls.append(text)
            if text != "katten":
                return None
            self._counter += 1
            return PronunciationAudio(audio_bytes=f"wav-{self._counter}".encode(), mime_type="audio/wav")

    stub_tts = StubTTSService()
    with TestClient(app) as client:
        set_service_field(client.app, "tts_service", stub_tts)
        add_response = client.post("/api/wordbank/lexemes", json={"surface_token": "Katten", "lemma_candidate": "kat"})
        assert add_response.status_code == 200
        first_response = client.post("/api/wordbank/lexemes/pronunciation", json={"stored_lemma": "kat", "stored_surface_form": "katten"})
        second_response = client.post("/api/wordbank/lexemes/pronunciation", json={"stored_lemma": "kat", "stored_surface_form": "katten", "force": True})
        audio_response = client.get("/api/wordbank/pronunciation", params={"form": "katten"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert audio_response.content == b"wav-2"
    assert stub_tts.calls == ["kat", "katten", "kat", "katten"]


def test_get_pronunciation_audio_returns_service_unavailable_when_tts_not_configured(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        add_response = client.post("/api/wordbank/lexemes", json={"surface_token": "Katten", "lemma_candidate": "kat"})
        assert add_response.status_code == 200
        response = client.get("/api/wordbank/pronunciation", params={"form": "katten"})

    assert response.status_code == 503
    assert "Text-to-speech is unavailable" in response.json()["detail"]
