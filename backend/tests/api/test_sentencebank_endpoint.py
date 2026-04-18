from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.core.app_state import set_service_field
from app.db.sqlite import get_connection
from app.nlp.adapter import NLPToken
from app.services.tts import PronunciationAudio
from tests.api.support import build_api_test_app


def test_add_sentence_inserts_and_returns_translation_from_provider(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    app = build_api_test_app(db_path, nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        def translate_da_to_en(self, text: str) -> str | None:
            if text == "Jeg elsker kaffe":
                return "i love coffee"
            return None

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        response = client.post("/api/sentencebank/sentences", json={"source_text": "Jeg elsker kaffe"})

    assert response.status_code == 200
    assert response.json()["status"] == "inserted"
    assert response.json()["source_text"] == "Jeg elsker kaffe"
    assert response.json()["english_translation"] == "I love coffee"
    assert response.json()["message"] == 'Added "Jeg elsker kaffe" to sentencebank.'
    assert response.json()["tokens"] == []


def test_add_sentence_duplicate_is_graceful(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    app = build_api_test_app(db_path, nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        first = client.post("/api/sentencebank/sentences", json={"source_text": "Jeg laeser hver dag"})
        second = client.post("/api/sentencebank/sentences", json={"source_text": "  jeg   laeser hver dag "})

    assert first.status_code == 200
    assert first.json()["status"] == "inserted"
    assert second.status_code == 200
    assert second.json()["status"] == "exists"
    assert "already" in second.json()["message"].lower()


def test_list_sentences_returns_newest_first(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    app = build_api_test_app(db_path, nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        client.post("/api/sentencebank/sentences", json={"source_text": "Jeg laeser en bog"})
        client.post("/api/sentencebank/sentences", json={"source_text": "Vi spiser nu"})
        response = client.get("/api/sentencebank/sentences")

    assert response.status_code == 200
    assert [item["source_text"] for item in response.json()["items"]] == ["Vi spiser nu", "Jeg laeser en bog"]


def test_sentencebank_post_and_get_include_nested_token_cards(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"

    class SentenceNLPAdapter:
        def tokenize(self, text: str) -> list[NLPToken]:
            if text != "Du og du":
                return []
            return [
                NLPToken(text="Du", lemma="du", pos="PRON", morphology="PronType=Prs", is_punctuation=False),
                NLPToken(text="og", lemma="og", pos="CCONJ", morphology=None, is_punctuation=False),
                NLPToken(text="du", lemma="du", pos="PRON", morphology="PronType=Prs", is_punctuation=False),
            ]

        def lemma_candidates_for_token(self, token: str) -> list[str]:
            return [token.lower()]

        def lemma_for_token(self, token: str) -> str | None:
            return token.lower()

        def metadata(self) -> dict[str, str]:
            return {"adapter": "SentenceNLPAdapter"}

    app = build_api_test_app(db_path, nlp_adapter_factory=lambda _settings: SentenceNLPAdapter())

    with TestClient(app) as client:
        post_response = client.post("/api/sentencebank/sentences", json={"source_text": "Du og du"})
        list_response = client.get("/api/sentencebank/sentences")

    assert post_response.status_code == 200
    post_payload = post_response.json()
    assert [token["surface_form"] for token in post_payload["tokens"]] == ["Du", "og", "du"]
    assert [token["stored_lemma"] for token in post_payload["tokens"]] == ["du", "og", "du"]
    assert post_payload["tokens"][1]["pos_tag"] == "CCONJ"

    assert list_response.status_code == 200
    assert [token["surface_form"] for token in list_response.json()["items"][0]["tokens"]] == ["Du", "og", "du"]


def test_add_sentence_queues_background_pronunciation_and_persists_audio(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    app = build_api_test_app(db_path, nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTTSService:
        provider = "gemini_tts"
        model = "gemini-2.5-flash-preview-tts"

        def __init__(self) -> None:
            self.calls: list[str] = []

        def synthesize(self, text: str) -> PronunciationAudio:
            self.calls.append(text)
            return PronunciationAudio(audio_bytes=f"{text}-wav".encode(), mime_type="audio/wav")

    tts_service = StubTTSService()

    with TestClient(app) as client:
        set_service_field(client.app, "tts_service", tts_service)
        response = client.post("/api/sentencebank/sentences", json={"source_text": "Jeg elsker kaffe"})

        deadline = time.time() + 5
        while time.time() < deadline:
            with get_connection(db_path) as conn:
                jobs = conn.execute(
                    """
                    SELECT status
                    FROM wordbank_background_jobs
                    WHERE job_type = 'generate_sentence_pronunciation'
                    ORDER BY id ASC
                    """
                ).fetchall()
                row = conn.execute(
                    """
                    SELECT pronunciation_audio
                    FROM sentence_bank
                    WHERE normalized_sentence = ?
                    """,
                    ("jeg elsker kaffe",),
                ).fetchone()
            if jobs and all(str(job["status"]) == "completed" for job in jobs) and row and row["pronunciation_audio"]:
                break
            time.sleep(0.05)

    assert response.status_code == 200
    payload = response.json()
    assert payload["pronunciation"] == {"status": "queued", "sentence_id": payload["id"]}
    assert tts_service.calls == ["Jeg elsker kaffe"]


def test_generate_sentence_pronunciation_endpoint_regenerates_audio(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    app = build_api_test_app(db_path, nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTTSService:
        provider = "gemini_tts"
        model = "gemini-2.5-flash-preview-tts"

        def __init__(self) -> None:
            self.calls: list[str] = []

        def synthesize(self, text: str) -> PronunciationAudio:
            self.calls.append(text)
            return PronunciationAudio(audio_bytes=f"{len(self.calls)}:{text}".encode(), mime_type="audio/wav")

    tts_service = StubTTSService()

    with TestClient(app) as client:
        save_response = client.post("/api/sentencebank/sentences", json={"source_text": "Jeg elsker kaffe"})
        sentence_id = int(save_response.json()["id"])
        set_service_field(client.app, "tts_service", tts_service)
        first_response = client.post(
            "/api/sentencebank/sentences/pronunciation",
            json={"sentence_id": sentence_id},
        )
        second_response = client.post(
            "/api/sentencebank/sentences/pronunciation",
            json={"sentence_id": sentence_id, "force": True},
        )
        audio_response = client.get("/api/sentencebank/pronunciation", params={"sentence_id": sentence_id})

    assert save_response.status_code == 200
    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["status"] == "generated"
    assert second_response.json()["status"] == "generated"
    assert audio_response.status_code == 200
    assert audio_response.content == b"2:Jeg elsker kaffe"
    assert tts_service.calls == ["Jeg elsker kaffe", "Jeg elsker kaffe"]
