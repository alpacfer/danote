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


def test_map_lemma_details_keeps_lemma_form_when_only_audio_carrier(tmp_path: Path) -> None:
    """When a non-sectioned lemma has the lemma form as its only audio-bearing
    surface form (and there is <=1 non-lemma form), the mapper used to drop the
    lemma row entirely. That broke the Infinitive-row play button on the word page.

    The mapper now keeps the lemma row when it carries pronunciation, so the
    frontend's pronunciation-availability map sees it.
    """
    from app.api.schemas.v1.wordbank import LemmaDetailsResponse
    from app.services.use_cases.wordbank.mappers import map_lemma_details_response

    response = LemmaDetailsResponse(
        lemma="passe på",
        english_translation="watch out for / take care of",
        pos_tag="VERB",
        is_sectioned=False,
        surface_forms=[
            LemmaDetailsResponse.SurfaceFormDetails(
                form="pas på", pos_tag="VERB", morphology="Mood=Imp|VerbForm=Fin",
                has_pronunciation=True,
            ),
            LemmaDetailsResponse.SurfaceFormDetails(
                form="passe på", pos_tag="VERB", morphology=None,
                has_pronunciation=True,
            ),
        ],
    )

    mapped = map_lemma_details_response(response)
    forms_by_text = {form.form for form in mapped.surface_forms}
    assert "passe på" in forms_by_text, (
        "lemma form must be retained when it has audio so the Infinitive row gets a play button"
    )
    assert "pas på" in forms_by_text


def test_map_lemma_details_still_drops_silent_lemma_form_when_alone(tmp_path: Path) -> None:
    """The dedup behavior is preserved when the lemma form has no pronunciation:
    keeping it would just clutter the variation list with the header text again.
    """
    from app.api.schemas.v1.wordbank import LemmaDetailsResponse
    from app.services.use_cases.wordbank.mappers import map_lemma_details_response

    response = LemmaDetailsResponse(
        lemma="bog",
        english_translation="book",
        pos_tag="NOUN",
        is_sectioned=False,
        surface_forms=[
            LemmaDetailsResponse.SurfaceFormDetails(
                form="bogen", pos_tag="NOUN", has_pronunciation=True,
            ),
            LemmaDetailsResponse.SurfaceFormDetails(
                form="bog", pos_tag="NOUN", has_pronunciation=False,
            ),
        ],
    )

    mapped = map_lemma_details_response(response)
    forms_by_text = {form.form for form in mapped.surface_forms}
    assert forms_by_text == {"bogen"}, "silent lemma form should still be dropped"


def test_ensure_wordbank_meaning_compatibility_scoped_per_lemma(tmp_path: Path) -> None:
    """A legacy/orphan surface form on one lemma must not block reads of an
    unrelated lemma. ``ensure_wordbank_meaning_compatibility(lemma=...)`` scopes
    the check so a bad row elsewhere doesn't cascade into "No details found."
    """
    import sqlite3
    from app.services.use_cases.wordbank.meaning_sections import (
        LEGACY_WORDBANK_RESET_REQUIRED_MESSAGE,
        ensure_wordbank_meaning_compatibility,
    )

    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(db_path)
    use_case.add_word("Bog", "bog")

    # Inject an orphan: a non-verb surface form (lemma "rotten") whose form differs
    # from the lemma and has meaning_id NULL — the exact shape the legacy check fires on.
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO lexemes (owner_user_id, lemma, source, dictionary_status, pos_tag) "
            "VALUES (?, ?, ?, ?, ?)",
            (1, "rotten", "search", "unknown", "NOUN"),
        )
        lexeme_id = cur.lastrowid
        conn.execute(
            "INSERT INTO surface_forms (lexeme_id, form, source, pos_tag, seen_count) "
            "VALUES (?, ?, ?, ?, ?)",
            (lexeme_id, "rotter", "search", "NOUN", 1),
        )
        conn.commit()

    # Global check fires (legacy orphan present somewhere in the DB).
    try:
        ensure_wordbank_meaning_compatibility(use_case.runtime)
    except RuntimeError as exc:
        assert LEGACY_WORDBANK_RESET_REQUIRED_MESSAGE in str(exc)
    else:
        raise AssertionError("expected global compat check to fire on the injected orphan")

    # But the lemma-scoped check for an unrelated lemma still passes — the orphan
    # belongs to a different lexeme.
    ensure_wordbank_meaning_compatibility(use_case.runtime, lemma="bog")

    # And `get_lemma_details("bog")` succeeds despite the orphan.
    details = use_case.get_lemma_details("bog")
    assert details.lemma == "bog"
