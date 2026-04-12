from __future__ import annotations

from app.services.sentence_verification import (
    SentenceVerificationErrorSpan,
    SentenceVerificationResult,
    _parse_result,
)


def test_parse_result_valid_sentence() -> None:
    raw = '{"is_valid": true, "errors": [], "corrected_text": null, "language": "da"}'
    result = _parse_result(raw, "Jeg er glad")
    assert result.is_valid is True
    assert result.errors == []
    assert result.corrected_text is None
    assert result.language == "da"


def test_parse_result_with_errors() -> None:
    raw = '{"is_valid": false, "errors": [{"start": 7, "end": 11, "message": "typo"}], "corrected_text": "Jeg er glad", "language": "da"}'
    result = _parse_result(raw, "jeg er glat")
    assert result.is_valid is False
    assert len(result.errors) == 1
    assert result.errors[0] == SentenceVerificationErrorSpan(start=7, end=11, message="typo")
    assert result.corrected_text == "jeg er glad"
    assert result.language == "da"


def test_parse_result_none_returns_valid_fallback() -> None:
    result = _parse_result(None, "any text")
    assert result.is_valid is True
    assert result.errors == []
    assert result.corrected_text is None
    assert result.language == "unknown"


def test_parse_result_invalid_json_returns_valid_fallback() -> None:
    result = _parse_result("not json", "any text")
    assert result.is_valid is True
    assert result.errors == []


def test_parse_result_unknown_language_normalized() -> None:
    raw = '{"is_valid": true, "errors": [], "corrected_text": null, "language": "fr"}'
    result = _parse_result(raw, "bonjour")
    assert result.language == "unknown"


def test_parse_result_english_detected() -> None:
    raw = '{"is_valid": true, "errors": [], "corrected_text": null, "language": "en"}'
    result = _parse_result(raw, "hello world")
    assert result.language == "en"


def test_parse_result_skips_malformed_error_spans() -> None:
    raw = '{"is_valid": false, "errors": [{"start": "bad", "end": 5, "message": "x"}, {"start": 0, "end": 3, "message": "ok"}], "corrected_text": "fix", "language": "da"}'
    result = _parse_result(raw, "fix me")
    assert len(result.errors) == 1
    assert result.errors[0].start == 0


def test_parse_result_preserves_initial_capitalization_style() -> None:
    raw = '{"is_valid": false, "errors": [{"start": 4, "end": 9, "message": "typo"}], "corrected_text": "jeg er glad", "language": "da"}'
    result = _parse_result(raw, "Jeg er glat")
    assert result.corrected_text == "Jeg er glad"


def test_parse_result_ignores_sentence_initial_capitalization_only_error() -> None:
    raw = '{"is_valid": false, "errors": [{"start": 0, "end": 1, "message": "capitalization"}], "corrected_text": "Jeg er glad", "language": "da"}'
    result = _parse_result(raw, "jeg er glad")
    assert result.is_valid is True
    assert result.errors == []
    assert result.corrected_text is None
