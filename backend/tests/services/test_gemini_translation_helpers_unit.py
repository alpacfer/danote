from app.services.gemini_translation import MeaningSectionCandidateInput, MeaningSectionSelectionInput
from app.services.gemini_translation_helpers import (
    build_meaning_section_selection_prompt,
    normalize_translation_value,
    parse_meaning_section_payload,
    parse_translation,
)


def test_parse_translation_from_json_payload() -> None:
    assert parse_translation('{"translation":"  Book  "}') == "book"


def test_normalize_translation_value_none_for_blank() -> None:
    assert normalize_translation_value("   ") is None


def test_parse_meaning_section_payload_filters_invalid_ids() -> None:
    assert parse_meaning_section_payload({"meaning_section_id": 2}, valid_ids={1}) is None
    assert parse_meaning_section_payload({"meaning_section_id": 1}, valid_ids={1}) == 1


def test_meaning_selection_prompt_serializes_slot_dataclasses() -> None:
    prompt = build_meaning_section_selection_prompt(
        MeaningSectionSelectionInput(
            surface_form="bogen",
            lemma="bog",
            meaning_candidates=[MeaningSectionCandidateInput(id=10, meaning_key="book")],
        )
    )
    assert '"id": 10' in prompt
    assert '"meaning_key": "book"' in prompt
