from __future__ import annotations

from pathlib import Path

from app.services import token_classifier
from app.services.token_classifier import LemmaAwareClassifier, normalize_token
from app.services.typo.typo_engine import TypoResult, TypoSuggestion


class _StubNLPAdapter:
    def __init__(self, mapping: dict[str, list[str] | str | None]):
        self.mapping = mapping

    def tokenize(self, text: str):
        return []

    def lemma_candidates_for_token(self, token: str) -> list[str]:
        value = self.mapping.get(token)
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def lemma_for_token(self, token: str) -> str | None:
        candidates = self.lemma_candidates_for_token(token)
        return candidates[0] if candidates else token

    def metadata(self) -> dict[str, str]:
        return {"adapter": "stub"}


class _DummyConn:
    def __init__(
        self,
        responses: dict[
            tuple[str, str] | tuple[str, tuple[str, ...]],
            dict[str, str] | list[dict[str, str]] | None,
        ],
    ):
        self.responses = responses
        self._result = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def execute(self, sql, params):
        if "FROM surface_forms" in sql:
            key = ("surface", params[0])
        elif "WHERE lemma IN" in sql:
            key = ("lexeme_many", tuple(params))
        else:
            key = ("lexeme", params[0])
        self._result = self.responses.get(key)
        return self

    def fetchone(self):
        if isinstance(self._result, list):
            return self._result[0] if self._result else None
        return self._result

    def fetchall(self):
        if isinstance(self._result, list):
            return self._result
        if self._result is None:
            return []
        return [self._result]


class _StubTypoEngine:
    def classify_unknown(self, *, token: str, sentence_start: bool = False) -> TypoResult:
        if token == "spisr":
            return TypoResult(
                status="typo_likely",
                normalized="spisr",
                suggestions=(TypoSuggestion(value="spiser", score=0.9, source_flags=("from_symspell",)),),
                confidence=0.9,
                reason_tags=("candidate_high_confidence",),
                latency_ms=1.2,
            )
        return TypoResult(
            status="new",
            normalized=token,
            suggestions=(),
            confidence=0.0,
            reason_tags=("weak_candidate_evidence",),
            latency_ms=0.8,
        )


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
        ("lexeme_many", ("bog",)): [{"lemma": "bog"}],
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


def test_lemma_match_uses_best_db_candidate_from_ranked_list(monkeypatch) -> None:
    responses = {
        ("surface", "bogen"): None,
        ("lexeme", "bogen"): None,
        ("lexeme_many", ("wrong", "bog")): [{"lemma": "bog"}],
    }
    monkeypatch.setattr(token_classifier, "get_connection", lambda _db_path: _DummyConn(responses))
    classifier = LemmaAwareClassifier(
        Path("/tmp/does-not-matter.sqlite3"),
        nlp_adapter=_StubNLPAdapter({"bogen": ["wrong", "bog"]}),
    )
    result = classifier.classify("bogen")
    assert result.classification == "variation"
    assert result.match_source == "lemma"
    assert result.lemma_candidate == "wrong"
    assert result.matched_lemma == "bog"


def test_unknown_returns_new(monkeypatch) -> None:
    responses = {
        ("surface", "kat"): None,
        ("lexeme", "kat"): None,
        ("lexeme_many", ("kat",)): [],
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


def test_unknown_can_fallback_to_typo_engine(monkeypatch) -> None:
    responses = {
        ("surface", "spisr"): None,
        ("lexeme", "spisr"): None,
        ("lexeme_many", ("spisr",)): [],
    }
    monkeypatch.setattr(token_classifier, "get_connection", lambda _db_path: _DummyConn(responses))
    classifier = LemmaAwareClassifier(
        Path("/tmp/does-not-matter.sqlite3"),
        nlp_adapter=_StubNLPAdapter({"spisr": "spisr"}),
        typo_engine=_StubTypoEngine(),
    )
    result = classifier.classify("spisr")
    assert result.classification == "typo_likely"
    assert result.match_source == "none"
    assert result.suggestions
    assert result.suggestions[0].value == "spiser"
