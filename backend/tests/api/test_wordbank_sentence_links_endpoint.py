from __future__ import annotations

from fastapi.testclient import TestClient

from app.nlp.adapter import NLPToken
from tests.api.support import build_api_test_app


class SentenceLinkNLPAdapter:
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
        return {"adapter": "SentenceLinkNLPAdapter"}


def test_wordbank_lemma_details_include_linked_sentences(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    app = build_api_test_app(db_path, nlp_adapter_factory=lambda _settings: SentenceLinkNLPAdapter())

    with TestClient(app) as client:
        save_response = client.post("/api/sentencebank/sentences", json={"source_text": "Du og du"})
        details_response = client.get("/api/wordbank/lemmas/du")

    assert save_response.status_code == 200
    assert details_response.status_code == 200
    linked_sentences = details_response.json()["linked_sentences"]
    assert len(linked_sentences) == 1
    assert linked_sentences[0]["source_text"] == "Du og du"
    assert linked_sentences[0]["matched_token_indexes"] == [0, 2]
    assert [token["surface_form"] for token in linked_sentences[0]["tokens"]] == ["Du", "og", "du"]
