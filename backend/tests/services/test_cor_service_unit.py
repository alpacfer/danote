from __future__ import annotations

import httpx

from app.services.cor import CORLexiconService


def _service_with_payload(payload: object) -> CORLexiconService:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json=payload)

    service = CORLexiconService(timeout_seconds=1.0)
    service._client = httpx.Client(base_url="https://ordregister.dk", transport=httpx.MockTransport(handler), timeout=1.0)
    return service


def test_cor_service_parses_entries_and_maps_ud_metadata() -> None:
    service = _service_with_payload(
        {
            "status": "ok",
            "svar": [
                {
                    "COR-id": "COR.49213.110.01",
                    "lemma": "gift",
                    "glosse": "",
                    "ordklasse": "sb",
                    "grammatisk function": "sb.fk.sg.ubest",
                    "fuldform": "gift",
                    "normeret": "N",
                },
                {
                    "COR-id": "COR.30548.209.01",
                    "lemma": "gifte",
                    "glosse": "",
                    "ordklasse": "vb",
                    "grammatisk function": "vb.imp",
                    "fuldform": "gift",
                    "normeret": "N",
                },
            ],
        }
    )

    entries = service.lookup_full_form("gift")

    assert len(entries) == 2
    noun_entry = entries[0]
    assert noun_entry.lemma == "gift"
    assert noun_entry.pos_tag == "NOUN"
    assert noun_entry.morphology == "Gender=Com|Number=Sing|Definite=Ind"
    verb_entry = entries[1]
    assert verb_entry.lemma == "gifte"
    assert verb_entry.pos_tag == "VERB"
    assert verb_entry.morphology == "Mood=Imp|VerbForm=Fin"


def test_cor_service_returns_empty_for_invalid_payload_shape() -> None:
    service = _service_with_payload({"status": "ok", "svar": "unexpected"})

    assert service.lookup_full_form("gift") == []
