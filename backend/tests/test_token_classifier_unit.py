from __future__ import annotations

from pathlib import Path

from app.services import token_classifier
from app.services.token_classifier import LemmaAwareClassifier, normalize_token


class _StubNLPAdapter:
    def __init__(self, mapping: dict[str, str | None]):
        self.mapping = mapping

    def tokenize(self, text: str):
        return []

    def lemma_for_token(self, token: str) -> str | None:
        return self.mapping.get(token, token)

    def metadata(self) -> dict[str, str]:
        return {"adapter": "stub"}


class _DummyConn:
    def __init__(self, responses: dict[tuple[str, str], dict[str, str] | None]):
        self.responses = responses
        self._result = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def execute(self, sql, params):
        key = ("surface" if "FROM surface_forms" in sql else "lexeme", params[0])
        self._result = self.responses.get(key)
        return self

    def fetchone(self):
        return self._result


def test_normalize_token_trims_collapses_whitespace_and_lowercases() -> None:
    assert normalize_token("  BoG   ") == "bog"
    assert normalize_token("  kan   lide  ") == "kan lide"


def test_exact_match_priority_beats_lemma_match(monkeypatch) -> None:
    responses = {
        ("surface", "bogen"): {"lemma": "bog", "form": "bogen"},
    }
    monkeypatch.setattr(token_classifier, "get_connection", lambda _db_path: _DummyConn(responses))
    classifier = LemmaAwareClassifier(
        Path("/tmp/does-not-matter.sqlite3"),
        nlp_adapter=_StubNLPAdapter({"bogen": "bog"}),
    )
    result = classifier.classify("bogen")
    assert result.classification == "known"
    assert result.match_source == "exact"
    assert result.normalized_token == "bogen"
    assert result.matched_lemma == "bog"


def test_lemma_match_returns_variation(monkeypatch) -> None:
    responses = {
        ("surface", "bogen"): None,
        ("lexeme", "bogen"): None,
        ("lexeme", "bog"): {"lemma": "bog"},
    }
    monkeypatch.setattr(token_classifier, "get_connection", lambda _db_path: _DummyConn(responses))
    classifier = LemmaAwareClassifier(
        Path("/tmp/does-not-matter.sqlite3"),
        nlp_adapter=_StubNLPAdapter({"bogen": "bog"}),
    )
    result = classifier.classify("bogen")
    assert result.classification == "variation"
    assert result.match_source == "lemma"
    assert result.lemma_candidate == "bog"
    assert result.matched_lemma == "bog"


def test_unknown_returns_new(monkeypatch) -> None:
    responses = {
        ("surface", "kat"): None,
        ("lexeme", "kat"): None,
    }
    monkeypatch.setattr(token_classifier, "get_connection", lambda _db_path: _DummyConn(responses))
    classifier = LemmaAwareClassifier(
        Path("/tmp/does-not-matter.sqlite3"),
        nlp_adapter=_StubNLPAdapter({"kat": "kat"}),
    )
    result = classifier.classify("kat")
    assert result.classification == "new"
    assert result.match_source == "none"
    assert result.normalized_token == "kat"
    assert result.matched_lemma is None
