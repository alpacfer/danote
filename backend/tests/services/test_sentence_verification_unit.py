from __future__ import annotations

from app.services.sentence_verification import (
    SentenceVerificationErrorSpan,
    SentenceMWESpan,
)
from app.services.sentence_verification_parser import (
    _normalize_mwe_pos_tag,
    _strip_danish_parenthetical,
    parse_sentence_verification_result as _parse_result,
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


def test_parse_result_whole_input_mwe_success() -> None:
    raw = (
        '{"is_valid": true, "errors": [], "corrected_text": null, "language": "da", '
        '"is_multi_word_expression": true, "mwe_lemma": "se efter", "mwe_pos_tag": "phrasal_verb", '
        '"mwe_gloss": "undersøge", "mwe_english_translation": "look after", "mwe_spans": []}'
    )
    result = _parse_result(raw, "se efter")
    assert result.is_multi_word_expression is True
    assert result.mwe_lemma == "se efter"
    assert result.mwe_pos_tag == "VERB"
    assert result.mwe_gloss == "undersøge"
    assert result.mwe_english_translation == "look after"


def test_parse_result_whole_input_mwe_ignored_if_no_space() -> None:
    raw = (
        '{"is_valid": true, "errors": [], "corrected_text": null, "language": "da", '
        '"is_multi_word_expression": true, "mwe_lemma": "kigge", "mwe_pos_tag": "verb", '
        '"mwe_gloss": "se", "mwe_english_translation": "look", "mwe_spans": []}'
    )
    # Input has no space, so whole-input MWE is ignored
    result = _parse_result(raw, "kigge")
    assert result.is_multi_word_expression is False
    assert result.mwe_lemma is None
    assert result.mwe_pos_tag is None


def test_parse_result_mwe_spans_success() -> None:
    raw = (
        '{"is_valid": true, "errors": [], "corrected_text": null, "language": "da", '
        '"is_multi_word_expression": false, "mwe_lemma": null, "mwe_pos_tag": null, '
        '"mwe_gloss": null, "mwe_english_translation": null, '
        '"mwe_spans": [{'
        '  "start": 4, "end": 16, "surface": "kigger efter", "lemma": "se efter", '
        '  "pos_tag": "phrasal_verb", "gloss": "passe på", "english_translation": "look after"'
        '}]}'
    )
    result = _parse_result(raw, "Jeg kigger efter min kat")
    assert result.is_multi_word_expression is False
    assert len(result.mwe_spans) == 1
    span = result.mwe_spans[0]
    assert span.start == 4
    assert span.end == 16
    assert span.surface == "kigger efter"
    assert span.lemma == "se efter"
    assert span.pos_tag == "VERB"
    assert span.gloss == "passe på"
    assert span.english_translation == "look after"


def test_parse_result_mwe_spans_alignment_guards() -> None:
    raw = (
        '{"is_valid": true, "errors": [], "corrected_text": null, "language": "da", '
        '"is_multi_word_expression": false, "mwe_lemma": null, "mwe_pos_tag": null, '
        '"mwe_gloss": null, "mwe_english_translation": null, '
        '"mwe_spans": ['
        '  {"start": 5, "end": 16, "surface": "igger efter", "lemma": "se efter"},'  # bad start alignment
        '  {"start": 4, "end": 15, "surface": "kigger efte", "lemma": "se efter"},'  # bad end alignment
        '  {"start": 4, "end": 16, "surface": "kigger efter", "lemma": "se efter"}'   # good alignment
        ']}'
    )
    result = _parse_result(raw, "Jeg kigger efter min kat")
    assert len(result.mwe_spans) == 1
    span = result.mwe_spans[0]
    assert span.start == 4
    assert span.end == 16
    assert span.surface == "kigger efter"
    assert span.lemma == "se efter"



# --- _normalize_mwe_pos_tag --------------------------------------------------


def test_normalize_mwe_pos_tag_uppercases_and_strips() -> None:
    assert _normalize_mwe_pos_tag("verb") == "VERB"
    assert _normalize_mwe_pos_tag("  Verb ") == "VERB"
    assert _normalize_mwe_pos_tag("NOUN") == "NOUN"


def test_normalize_mwe_pos_tag_maps_legacy_aliases_to_ud_tags() -> None:
    """Even if Gemini disregards the prompt and emits the old vocabulary,
    `phrasal_verb`/`idiom`/`mwe` get coerced to the underlying UD tag."""
    assert _normalize_mwe_pos_tag("phrasal_verb") == "VERB"
    assert _normalize_mwe_pos_tag("phrasal verb") == "VERB"
    assert _normalize_mwe_pos_tag("Phrasal-Verb") == "VERB"
    assert _normalize_mwe_pos_tag("idiom") == "VERB"
    assert _normalize_mwe_pos_tag("MWE") == "VERB"


def test_normalize_mwe_pos_tag_passes_through_unknown_tags() -> None:
    """Unknown tags are kept as-is (uppercased) so we don't silently drop
    a tag we don't yet have an alias for."""
    assert _normalize_mwe_pos_tag("ADV") == "ADV"
    assert _normalize_mwe_pos_tag("WHATEVER") == "WHATEVER"


def test_normalize_mwe_pos_tag_returns_none_for_empty_or_non_string() -> None:
    assert _normalize_mwe_pos_tag(None) is None
    assert _normalize_mwe_pos_tag("") is None
    assert _normalize_mwe_pos_tag("   ") is None
    assert _normalize_mwe_pos_tag(123) is None


# --- merge_mwe_spans edge cases ----------------------------------------------


def test_merge_mwe_spans_drops_empty_lemma_spans() -> None:
    """Spans with empty/whitespace-only lemma are dropped before merge."""
    from app.nlp.adapter import NLPToken
    from app.services.use_cases.sentencebank_mwe import MWEToken, merge_mwe_spans

    tokens = [
        NLPToken(text="Han", lemma="han", pos="PRON", morphology=None, is_punctuation=False),
        NLPToken(text="løb", lemma="løbe", pos="VERB", morphology=None, is_punctuation=False),
    ]
    result = merge_mwe_spans(
        tokens,
        "Han løb",
        [SentenceMWESpan(start=0, end=7, surface="Han løb", lemma="   ")],
    )
    assert result == tokens, "empty-lemma spans must not produce MWE tokens"
    assert not any(isinstance(t, MWEToken) for t in result)


def test_merge_mwe_spans_drops_single_word_lemma_spans() -> None:
    """Gemini occasionally tags a single word as an MWE. Don't merge those — the
    result would be a 1-token "MWE" identical to the input but with confusing metadata.
    """
    from app.nlp.adapter import NLPToken
    from app.services.use_cases.sentencebank_mwe import MWEToken, merge_mwe_spans

    tokens = [
        NLPToken(text="Han", lemma="han", pos="PRON", morphology=None, is_punctuation=False),
        NLPToken(text="løb", lemma="løbe", pos="VERB", morphology=None, is_punctuation=False),
    ]
    result = merge_mwe_spans(
        tokens,
        "Han løb",
        [SentenceMWESpan(start=4, end=7, surface="løb", lemma="løbe", pos_tag="VERB")],
    )
    assert result == tokens
    assert not any(isinstance(t, MWEToken) for t in result)


def test_merge_mwe_spans_returns_input_unchanged_when_no_spans() -> None:
    from app.nlp.adapter import NLPToken
    from app.services.use_cases.sentencebank_mwe import merge_mwe_spans

    tokens = [
        NLPToken(text="Hej", lemma="hej", pos="INTJ", morphology=None, is_punctuation=False),
    ]
    assert merge_mwe_spans(tokens, "Hej", None) == tokens
    assert merge_mwe_spans(tokens, "Hej", []) == tokens


# --- mwe_meanings parsing ---------------------------------------------------


def test_parse_result_populates_mwe_meanings_for_polysemous_lemma() -> None:
    """Polysemous phrasal verbs like "tage på" return one entry per distinct sense."""
    raw = (
        '{"is_valid": true, "errors": [], "corrected_text": null, "language": "da", '
        '"is_multi_word_expression": true, "mwe_lemma": "tage på", "mwe_pos_tag": "VERB", '
        '"mwe_gloss": null, "mwe_english_translation": null, '
        '"mwe_meanings": ['
        '  {"gloss": "iføre sig tøj", "english_translation": "to put on (clothes)", "pos_tag": "VERB", "meaning_key": "iføre sig tøj"},'
        '  {"gloss": "forøge sin kropsvægt", "english_translation": "to gain weight", "pos_tag": "VERB", "meaning_key": "tage på i vægt"},'
        '  {"gloss": "tage afsted", "english_translation": "to go somewhere", "pos_tag": "VERB", "meaning_key": "tage afsted"}'
        ']}'
    )
    result = _parse_result(raw, "tage på")
    assert result.is_multi_word_expression is True
    assert result.mwe_lemma == "tage på"
    assert len(result.mwe_meanings) == 3
    assert result.mwe_meanings[0].gloss == "iføre sig tøj"
    assert result.mwe_meanings[0].english_translation == "to put on (clothes)"
    assert result.mwe_meanings[0].pos_tag == "VERB"
    assert result.mwe_meanings[1].english_translation == "to gain weight"
    assert result.mwe_meanings[2].meaning_key == "tage afsted"
    # Back-compat: when Gemini didn't populate the single mwe_* fields, the first
    # meaning supplies them.
    assert result.mwe_gloss == "iføre sig tøj"
    assert result.mwe_english_translation == "to put on (clothes)"


def test_parse_result_synthesizes_meanings_from_legacy_single_fields() -> None:
    """Forward-compat: older Gemini responses that only set mwe_gloss / english_translation
    get a one-element mwe_meanings synthesized so frontend code can iterate uniformly."""
    raw = (
        '{"is_valid": true, "errors": [], "corrected_text": null, "language": "da", '
        '"is_multi_word_expression": true, "mwe_lemma": "se efter", "mwe_pos_tag": "VERB", '
        '"mwe_gloss": "undersøge", "mwe_english_translation": "look after", "mwe_meanings": []}'
    )
    result = _parse_result(raw, "se efter")
    assert len(result.mwe_meanings) == 1
    assert result.mwe_meanings[0].gloss == "undersøge"
    assert result.mwe_meanings[0].english_translation == "look after"
    assert result.mwe_meanings[0].pos_tag == "VERB"


def test_parse_result_drops_mwe_meanings_when_not_an_mwe() -> None:
    """If the input isn't an MWE, the meanings list must be empty even if Gemini hallucinates entries."""
    raw = (
        '{"is_valid": true, "errors": [], "corrected_text": null, "language": "da", '
        '"is_multi_word_expression": false, "mwe_lemma": null, "mwe_pos_tag": null, '
        '"mwe_gloss": null, "mwe_english_translation": null, '
        '"mwe_meanings": [{"gloss": "X", "english_translation": "Y", "pos_tag": "VERB"}]}'
    )
    result = _parse_result(raw, "hello")
    assert result.is_multi_word_expression is False
    assert result.mwe_meanings == []


def test_parse_result_dedupes_mwe_meanings_by_key() -> None:
    raw = (
        '{"is_valid": true, "errors": [], "corrected_text": null, "language": "da", '
        '"is_multi_word_expression": true, "mwe_lemma": "tage på", "mwe_pos_tag": "VERB", '
        '"mwe_gloss": null, "mwe_english_translation": null, '
        '"mwe_meanings": ['
        '  {"gloss": "a", "english_translation": "X", "meaning_key": "K"},'
        '  {"gloss": "b", "english_translation": "X2", "meaning_key": "K"}'
        ']}'
    )
    result = _parse_result(raw, "tage på")
    assert len(result.mwe_meanings) == 1
    assert result.mwe_meanings[0].english_translation == "X"


def test_parse_result_drops_mwe_meanings_with_no_content() -> None:
    raw = (
        '{"is_valid": true, "errors": [], "corrected_text": null, "language": "da", '
        '"is_multi_word_expression": true, "mwe_lemma": "tage på", "mwe_pos_tag": "VERB", '
        '"mwe_gloss": null, "mwe_english_translation": null, '
        '"mwe_meanings": ['
        '  {"gloss": null, "english_translation": null, "meaning_key": "empty"},'
        '  {"gloss": "ok", "english_translation": null, "meaning_key": "kept"}'
        ']}'
    )
    result = _parse_result(raw, "tage på")
    assert len(result.mwe_meanings) == 1
    assert result.mwe_meanings[0].meaning_key == "kept"


# --- _strip_danish_parenthetical -------------------------------------------


def test_strip_danish_parenthetical_removes_danish_gloss() -> None:
    """The exact 'run away' bug: Gemini appends a Danish gloss in parens."""
    result = _strip_danish_parenthetical(
        "to run away (at flygte eller forlade et sted hurtigt)"
    )
    assert result == "to run away"


def test_strip_danish_parenthetical_preserves_english_disambiguator() -> None:
    """A parenthetical with only English characters (no æ/ø/å) must be left intact."""
    assert _strip_danish_parenthetical("to put on (clothes)") == "to put on (clothes)"
    assert _strip_danish_parenthetical("to run (figurative)") == "to run (figurative)"


def test_strip_danish_parenthetical_handles_none_and_empty() -> None:
    assert _strip_danish_parenthetical(None) is None
    assert _strip_danish_parenthetical("") is None


def test_strip_danish_parenthetical_removes_multiple_danish_parens() -> None:
    """Multiple parenthetical blocks are each evaluated independently."""
    result = _strip_danish_parenthetical(
        "to look after (at passe på) or search (figurative)"
    )
    assert result == "to look after or search (figurative)"


def test_parse_result_strips_danish_parenthetical_from_mwe_english_translation() -> None:
    """Regression test: Gemini Danish gloss in mwe_english_translation must be stripped."""
    raw = (
        '{"is_valid": true, "errors": [], "corrected_text": null, "language": "da", '
        '"is_multi_word_expression": true, "mwe_lemma": "løbe fra", "mwe_pos_tag": "VERB", '
        '"mwe_gloss": "forlade et sted hurtigt", '
        '"mwe_english_translation": "to run away (at flygte eller forlade et sted hurtigt)", '
        '"mwe_meanings": [{'
        '  "gloss": "forlade et sted hurtigt", '
        '  "english_translation": "to run away (at flygte eller forlade et sted hurtigt)", '
        '  "pos_tag": "VERB", "meaning_key": "løbe fra"}'
        ']}'
    )
    result = _parse_result(raw, "løbe fra")
    assert result.mwe_english_translation == "to run away"
    assert result.mwe_meanings[0].english_translation == "to run away"


def test_parse_result_rejects_mwe_longer_than_4_words() -> None:
    raw = (
        '{"is_valid": true, "errors": [], "corrected_text": null, "language": "da", '
        '"is_multi_word_expression": true, "mwe_lemma": "det er ikke min kop te", "mwe_pos_tag": "VERB", '
        '"mwe_gloss": "not my preference", "mwe_english_translation": "not my cup of tea", "mwe_meanings": []}'
    )
    result = _parse_result(raw, "det er ikke min kop te")
    assert result.is_multi_word_expression is False
    assert result.mwe_lemma is None


def test_parse_result_accepts_mwe_up_to_4_words() -> None:
    raw = (
        '{"is_valid": true, "errors": [], "corrected_text": null, "language": "da", '
        '"is_multi_word_expression": true, "mwe_lemma": "gå i gang", "mwe_pos_tag": "VERB", '
        '"mwe_gloss": "begynde", "mwe_english_translation": "get started", "mwe_meanings": []}'
    )
    result = _parse_result(raw, "gå i gang")
    assert result.is_multi_word_expression is True
    assert result.mwe_lemma == "gå i gang"

