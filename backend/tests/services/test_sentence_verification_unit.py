from __future__ import annotations

from app.services.sentence_verification import (
    SentenceVerificationErrorSpan,
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


def test_parse_result_ignores_english_sentence_initial_capitalization_only_error() -> None:
    raw = '{"is_valid": false, "errors": [{"start": 0, "end": 1, "message": "capitalization"}], "corrected_text": "I am happy", "language": "en"}'
    result = _parse_result(raw, "i am happy")
    assert result.is_valid is True
    assert result.errors == []
    assert result.corrected_text is None


def test_parse_result_preserves_source_initial_case_for_english_corrections() -> None:
    raw = '{"is_valid": false, "errors": [{"start": 5, "end": 9, "message": "typo"}], "corrected_text": "I am happy", "language": "en"}'
    result = _parse_result(raw, "i am hapy")
    assert result.is_valid is False
    assert result.errors == [SentenceVerificationErrorSpan(start=5, end=9, message="typo")]
    assert result.corrected_text == "i am happy"


def test_parse_result_ignores_mid_sentence_capitalization_only_error() -> None:
    raw = '{"is_valid": false, "errors": [{"start": 7, "end": 10, "message": "capitalization"}], "corrected_text": "jeg er Glad", "language": "da"}'
    result = _parse_result(raw, "jeg er glad")
    assert result.is_valid is True
    assert result.errors == []
    assert result.corrected_text is None


def test_parse_result_removes_unrequested_terminal_period() -> None:
    raw = '{"is_valid": false, "errors": [{"start": 7, "end": 11, "message": "typo"}], "corrected_text": "jeg er glad.", "language": "da"}'
    result = _parse_result(raw, "jeg er glat")
    assert result.corrected_text == "jeg er glad"


def test_parse_result_realigns_span_to_changed_word_when_model_points_at_previous_word() -> None:
    raw = (
        '{"is_valid": false, "errors": [{"start": 11, "end": 14, "message": "typo"}], '
        '"corrected_text": "vi sejler til havs igen", "language": "da"}'
    )
    result = _parse_result(raw, "vi sejler til hav igen")

    assert result.errors == [SentenceVerificationErrorSpan(start=14, end=17, message="typo")]
    assert result.corrected_text == "vi sejler til havs igen"


def test_parse_result_expands_partial_word_span_to_full_changed_word() -> None:
    raw = '{"is_valid": false, "errors": [{"start": 8, "end": 10, "message": "typo"}], "corrected_text": "jeg er glad", "language": "da"}'
    result = _parse_result(raw, "jeg er glat")

    assert result.errors == [SentenceVerificationErrorSpan(start=7, end=11, message="typo")]


def test_parse_result_rejects_autocomplete_for_partial_input() -> None:
    raw = (
        '{"is_valid": false, "errors": [{"start": 11, "end": 15, "message": "incomplete phrase"}], '
        '"corrected_text": "jeg har en stor hund", "language": "da"}'
    )
    result = _parse_result(raw, "jeg har en stor")

    assert result.is_valid is True
    assert result.errors == []
    assert result.corrected_text is None


def test_parse_result_keeps_existing_typos_when_model_both_corrects_and_autocompletes() -> None:
    raw = (
        '{"is_valid": false, "errors": [{"start": 11, "end": 16, "message": "typo"}], '
        '"corrected_text": "jeg har en stor hund", "language": "da"}'
    )
    result = _parse_result(raw, "jeg har en storr")

    assert result.is_valid is False
    assert result.errors == [SentenceVerificationErrorSpan(start=11, end=16, message="typo")]
    assert result.corrected_text is None


def test_parse_result_ignores_fragment_only_feedback_without_correction() -> None:
    raw = (
        '{"is_valid": false, "errors": [{"start": 0, "end": 15, "message": "Incomplete sentence fragment."}], '
        '"corrected_text": null, "language": "da"}'
    )
    result = _parse_result(raw, "jeg har en stor")

    assert result.is_valid is True
    assert result.errors == []
    assert result.corrected_text is None


def test_parse_result_ignores_fragment_only_feedback_when_model_repeats_source_text() -> None:
    raw = (
        '{"is_valid": false, "errors": [{"start": 0, "end": 15, "message": "Ufuldstændig sætning."}], '
        '"corrected_text": "jeg har en stor", "language": "da"}'
    )
    result = _parse_result(raw, "jeg har en stor")

    assert result.is_valid is True
    assert result.errors == []
    assert result.corrected_text is None


def test_parse_result_allows_word_split_correction_without_treating_it_as_autocomplete() -> None:
    raw = (
        '{"is_valid": false, "errors": [{"start": 0, "end": 5, "message": "spelling"}], '
        '"corrected_text": "i dag", "language": "da"}'
    )
    result = _parse_result(raw, "idag")

    assert result.is_valid is False
    assert result.errors == [SentenceVerificationErrorSpan(start=0, end=4, message="spelling")]
    assert result.corrected_text == "i dag"
