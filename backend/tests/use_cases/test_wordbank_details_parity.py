from __future__ import annotations

from pathlib import Path

from app.services.use_cases.wordbank import WordbankUseCase
from tests.helpers.factories import _db_path


def test_saved_and_builtin_lemma_details_share_response_shape(tmp_path: Path) -> None:
    """Saved words and built-in words must return a LemmaDetailsResponse with the same
    structural fields so the shared word-page layout can render either one without
    branching."""
    use_case = WordbankUseCase(_db_path(tmp_path))
    use_case.add_word("Bog", "bog")

    saved = use_case.get_lemma_details("bog")
    builtin = use_case.get_lemma_details("du")

    expected_fields = {
        "lemma",
        "english_translation",
        "is_sectioned",
        "pos_tag",
        "morphology",
        "categories",
        "surface_forms",
        "meaning_sections",
        "reference_links",
    }
    saved_fields = set(saved.model_dump().keys())
    builtin_fields = set(builtin.model_dump().keys())
    assert expected_fields.issubset(saved_fields)
    assert expected_fields.issubset(builtin_fields)
    assert saved_fields == builtin_fields

    assert saved.surface_forms, "Saved word should expose at least one surface form"
    assert builtin.surface_forms, "Built-in word should expose at least one surface form"
    assert all(hasattr(form, "has_pronunciation") for form in saved.surface_forms)
    assert all(hasattr(form, "has_pronunciation") for form in builtin.surface_forms)


def test_builtin_lemma_details_exposes_pinned_reference_links(tmp_path: Path) -> None:
    """Built-in lemmas should advertise their pinned home(s) through reference_links so
    the shared word-page layout can render the chip without special-casing."""
    use_case = WordbankUseCase(_db_path(tmp_path))

    details = use_case.get_lemma_details("du")

    reference_chip_sources = list(details.reference_links or [])
    for section in details.meaning_sections or []:
        reference_chip_sources.extend(section.reference_links or [])
    assert reference_chip_sources, "Built-in lemma should expose at least one pinned reference link"
    assert any(link.page_id == "pronouns" for link in reference_chip_sources)


def test_hvem_returns_single_interrogative_sense(tmp_path: Path) -> None:
    """Regression: 'hvem' is defined in both static_pronouns and static_hv_words.
    The use-case must collapse them into a single meaning so the word page does not
    render two duplicate cards for the same interrogative-pronoun meaning."""
    use_case = WordbankUseCase(_db_path(tmp_path))

    details = use_case.get_lemma_details("hvem")

    if details.is_sectioned:
        assert details.meaning_sections is not None
        assert len(details.meaning_sections) == 1
        only_section = details.meaning_sections[0]
        assert only_section.english_translation.casefold() == "who"
    else:
        assert details.english_translation is not None
        assert details.english_translation.casefold() == "who"


def test_hvem_dedup_collapses_pronoun_and_hv_word(tmp_path: Path) -> None:
    """Regression at the use-case layer: the canonical translation 'who' from both
    static_pronouns.py and static_hv_words.py must not survive as two senses."""
    from app.services.use_cases.static_builtin_words import static_builtin_senses_for_token

    senses = static_builtin_senses_for_token("hvem")

    assert len(senses) == 1
    sense = senses[0]
    assert sense.lemma == "hvem"
    assert sense.english_translation.casefold() == "who"
    assert (sense.pos_tag or "").upper() == "PRON"
