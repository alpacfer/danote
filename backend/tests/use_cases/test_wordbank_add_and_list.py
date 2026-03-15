from __future__ import annotations

import json
from pathlib import Path

from app.api.schemas.v1.wordbank import LemmaDetailsResponse
from app.db.migrations import get_connection
from app.nlp.adapter import NLPToken
from app.services.tts import PronunciationAudio
from app.services.use_cases.wordbank import WordbankUseCase
from tests.helpers.factories import _bog_homograph_cor_local, _cor_local_entry, _db_path
from tests.helpers.fakes import (
    FakeCORLocalLexiconService,
    FakeGeminiWordTranslationService,
    FakeTranslationService,
    FakeTTSService,
    FakeVerificationService,
)
import pytest


def _verify_meaning_targets(use_case: WordbankUseCase, *, lemma: str, meaning_id: int, surfaces: list[str]) -> None:
    use_case.verify_added_word(lemma, None, meaning_id=meaning_id)
    for surface in surfaces:
        use_case.verify_added_word(lemma, surface, meaning_id=meaning_id)


def _bog_complete_paradigm_cor_local() -> FakeCORLocalLexiconService:
    book_entries = [
        _cor_local_entry(
            cor_id="COR.BOG.BOOK.LEM",
            lemma="bog",
            gloss="book",
            form="bog",
            lemma_idx=123,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing|Definite=Ind",
            gram_raw="sb.fk.sg.ubest",
        ),
        _cor_local_entry(
            cor_id="COR.BOG.BOOK.DEF",
            lemma="bog",
            gloss="book",
            form="bogen",
            lemma_idx=123,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing|Definite=Def",
            gram_raw="sb.fk.sg.best",
        ),
        _cor_local_entry(
            cor_id="COR.BOG.BOOK.PL",
            lemma="bog",
            gloss="book",
            form="bøger",
            lemma_idx=123,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Plur|Definite=Ind",
            gram_raw="sb.fk.pl.ubest",
        ),
        _cor_local_entry(
            cor_id="COR.BOG.BOOK.PLDEF",
            lemma="bog",
            gloss="book",
            form="bøgerne",
            lemma_idx=123,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Plur|Definite=Def",
            gram_raw="sb.fk.pl.best",
        ),
    ]
    swamp_entries = [
        _cor_local_entry(
            cor_id="COR.BOG.SWAMP.LEM",
            lemma="bog",
            gloss="swamp",
            form="bog",
            lemma_idx=124,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing|Definite=Ind",
            gram_raw="sb.fk.sg.ubest",
        ),
        _cor_local_entry(
            cor_id="COR.BOG.SWAMP.DEF",
            lemma="bog",
            gloss="swamp",
            form="bogen",
            lemma_idx=124,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing|Definite=Def",
            gram_raw="sb.fk.sg.best",
        ),
        _cor_local_entry(
            cor_id="COR.BOG.SWAMP.PL",
            lemma="bog",
            gloss="swamp",
            form="moser",
            lemma_idx=124,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Plur|Definite=Ind",
            gram_raw="sb.fk.pl.ubest",
        ),
        _cor_local_entry(
            cor_id="COR.BOG.SWAMP.PLDEF",
            lemma="bog",
            gloss="swamp",
            form="moserne",
            lemma_idx=124,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Plur|Definite=Def",
            gram_raw="sb.fk.pl.best",
        ),
    ]
    return FakeCORLocalLexiconService(
        by_form={
            "bog": [book_entries[0], swamp_entries[0]],
            "bogen": [book_entries[1], swamp_entries[1]],
            "bøger": [book_entries[2]],
            "bøgerne": [book_entries[3]],
            "moser": [swamp_entries[2]],
            "moserne": [swamp_entries[3]],
        },
        by_lemma_idx={
            123: book_entries,
            124: swamp_entries,
        },
    )


def _fader_complete_paradigm_cor_local() -> FakeCORLocalLexiconService:
    entries = [
        _cor_local_entry(
            cor_id="COR.FADER.LEM",
            lemma="fader",
            gloss="father",
            form="fader",
            lemma_idx=410,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing|Definite=Ind",
            gram_raw="sb.fk.sg.ubest",
        ),
        _cor_local_entry(
            cor_id="COR.FADER.IRREG",
            lemma="fader",
            gloss="father",
            form="far",
            lemma_idx=410,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing|Definite=Ind",
            gram_raw="sb.fk.sg.ubest",
        ),
        _cor_local_entry(
            cor_id="COR.FADER.DEF",
            lemma="fader",
            gloss="father",
            form="faderen",
            lemma_idx=410,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing|Definite=Def",
            gram_raw="sb.fk.sg.best",
        ),
        _cor_local_entry(
            cor_id="COR.FADER.PL",
            lemma="fader",
            gloss="father",
            form="fædre",
            lemma_idx=410,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Plur|Definite=Ind",
            gram_raw="sb.fk.pl.ubest",
        ),
        _cor_local_entry(
            cor_id="COR.FADER.PLDEF",
            lemma="fader",
            gloss="father",
            form="fædrene",
            lemma_idx=410,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Plur|Definite=Def",
            gram_raw="sb.fk.pl.best",
        ),
    ]
    return FakeCORLocalLexiconService(
        by_form={entry.form: [entry] for entry in entries},
        by_lemma_idx={410: entries},
    )


def test_wordbank_use_case_round_trip(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    added = use_case.add_word("Bogen", "bog")
    assert added.status == "inserted"
    assert added.stored_lemma == "bog"
    assert added.stored_surface_form == "bogen"

    details = use_case.get_lemma_details("bog")
    assert details.lemma == "bog"
    assert details.is_sectioned is True
    assert [item.form for item in details.surface_forms] == ["bog"]
    assert len(details.meaning_sections) == 1
    assert details.meaning_sections[0].meaning_key == "bog"
    assert [item.form for item in details.meaning_sections[0].surface_forms] == ["bogen"]

    listing = use_case.list_lemmas()
    assert listing.items[0].lemma == "bog"
    assert listing.items[0].display_lemma == "bog"
    assert listing.items[0].variation_count == 1
    assert listing.items[0].english_translation is None


def test_wordbank_starter_categories_are_seeded_once(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    _ = WordbankUseCase(db_path)

    with get_connection(db_path) as conn:
        count_before = conn.execute("SELECT COUNT(*) AS count FROM wordbank_categories").fetchone()
    assert count_before is not None
    assert count_before["count"] == 20

    _ = WordbankUseCase(db_path)

    with get_connection(db_path) as conn:
        count_after = conn.execute("SELECT COUNT(*) AS count FROM wordbank_categories").fetchone()
    assert count_after is not None
    assert count_after["count"] == 20

def test_wordbank_use_case_facade_delegates_across_extracted_workflows(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"bog": "book", "bogen": "the book"}),
    )

    added = use_case.add_word("Bogen", "bog")
    listing = use_case.list_lemmas()
    search = use_case.search_lemmas("bog")
    details = use_case.get_lemma_details("bog")

    assert added.status == "inserted"
    assert listing.items[0].lemma == "bog"
    assert search.items[0].lemma == "bog"
    assert details.lemma == "bog"
    assert details.english_translation == "book"
    assert details.is_sectioned is True
    assert len(details.meaning_sections) == 1
    assert details.meaning_sections[0].surface_forms[0].lemma_translation == "book"

def test_wordbank_use_case_includes_pos_and_morphology_when_nlp_available(tmp_path: Path) -> None:
    class WordbankNLPAdapter:
        def tokenize(self, text: str) -> list[NLPToken]:
            return [
                NLPToken(
                    text=text,
                    lemma=text.lower(),
                    pos="NOUN",
                    morphology="Gender=Com|Number=Sing",
                    is_punctuation=False,
                )
            ]

        def lemma_candidates_for_token(self, token: str) -> list[str]:
            return [token.lower()]

        def lemma_for_token(self, token: str) -> str | None:
            return token.lower()

        def metadata(self) -> dict[str, str]:
            return {"adapter": "wordbank-fake"}

    use_case = WordbankUseCase(
        _db_path(tmp_path),
        nlp_adapter=WordbankNLPAdapter(),
    )

    use_case.add_word("Bogen", "bog")

    details = use_case.get_lemma_details("bog")
    assert details.pos_tag == "NOUN"
    assert details.morphology == "Gender=Com|Number=Sing"
    assert details.is_sectioned is True
    assert len(details.surface_forms) == 1
    assert details.surface_forms[0].form == "bog"
    assert details.surface_forms[0].pos_tag == "NOUN"
    assert details.surface_forms[0].morphology == "Gender=Com|Number=Sing"
    assert len(details.meaning_sections) == 1
    assert details.meaning_sections[0].pos_tag == "NOUN"
    assert details.meaning_sections[0].morphology == "Gender=Com|Number=Sing"
    assert details.meaning_sections[0].surface_forms == [
        LemmaDetailsResponse.SurfaceFormDetails(
            form="bogen",
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing",
            lemma="bog",
            lemma_translation=None,
        ),
    ]

def test_wordbank_list_lemmas_displays_verbs_with_at_prefix(tmp_path: Path) -> None:
    class VerbListNLPAdapter:
        def tokenize(self, text: str) -> list[NLPToken]:
            return [
                NLPToken(
                    text=text,
                    lemma=text.lower(),
                    pos="VERB",
                    morphology="VerbForm=Inf",
                    is_punctuation=False,
                )
            ]

        def lemma_candidates_for_token(self, token: str) -> list[str]:
            return [token.lower()]

        def lemma_for_token(self, token: str) -> str | None:
            return token.lower()

        def metadata(self) -> dict[str, str]:
            return {"adapter": "verb-list-fake"}

    use_case = WordbankUseCase(
        _db_path(tmp_path),
        nlp_adapter=VerbListNLPAdapter(),
    )
    use_case.add_word("laver", "lave")

    listing = use_case.list_lemmas()
    assert listing.items[0].lemma == "lave"
    assert listing.items[0].display_lemma == "at lave"

def test_wordbank_add_word_keeps_same_surface_under_distinct_meaning_sections(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=_bog_homograph_cor_local(),
        translation_service=FakeTranslationService(
            {
                "book": "book",
                "swamp": "swamp",
                "bog": "book-fallback",
                "bogen": "generic-bogen",
            }
        ),
        gemini_word_translation_service=FakeGeminiWordTranslationService(
            {
                ("bog", "bog", "book"): "book",
                ("bogen", "bog", "book"): "the book",
                ("bog", "bog", "swamp"): "swamp",
                ("bogen", "bog", "swamp"): "the swamp",
            }
        ),
    )

    first = use_case.add_word("Bogen", "bog", cor_id="COR.BOG.BOOK.DEF")
    second = use_case.add_word("Bogen", "bog", cor_id="COR.BOG.SWAMP.DEF")
    details = use_case.get_lemma_details("bog")

    assert first.status == "inserted"
    assert second.status == "inserted"
    assert first.meaning is not None
    assert second.meaning is not None
    assert first.meaning.id != second.meaning.id
    assert [section.meaning_key for section in details.meaning_sections] == ["book", "swamp"]
    assert details.meaning_sections[0].surface_forms[0].lemma_translation == "book"
    assert details.meaning_sections[1].surface_forms[0].lemma_translation == "swamp"

def test_wordbank_add_word_treats_duplicate_cor_id_for_same_meaning_form_as_exists(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=_bog_homograph_cor_local(),
    )

    first = use_case.add_word("Bogen", "bog", cor_id="COR.BOG.BOOK.DEF")
    second = use_case.add_word("Bogen", "bog", cor_id="COR.BOG.BOOK.DEF")

    assert first.status == "inserted"
    assert second.status == "exists"

def test_wordbank_add_word_routes_variations_to_their_matching_meaning(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=_bog_homograph_cor_local(),
        translation_service=FakeTranslationService({"book": "book", "swamp": "swamp"}),
        gemini_word_translation_service=FakeGeminiWordTranslationService(
            {
                ("bog", "bog", "book"): "book",
                ("bogen", "bog", "book"): "the book",
                ("bøger", "bog", "book"): "books",
                ("bog", "bog", "swamp"): "swamp",
                ("moser", "bog", "swamp"): "swamps",
            }
        ),
    )

    use_case.add_word("Bogen", "bog", cor_id="COR.BOG.BOOK.DEF")
    use_case.add_word("Moser", "bog", cor_id="COR.BOG.SWAMP.PL")
    details = use_case.get_lemma_details("bog")

    by_key = {section.meaning_key: section for section in details.meaning_sections}
    assert [item.form for item in by_key["book"].surface_forms] == ["bogen"]
    assert [item.form for item in by_key["swamp"].surface_forms] == ["moser"]
    assert by_key["swamp"].surface_forms[0].lemma_translation == "swamp"


def test_complete_meaning_variations_backfills_missing_noun_slots_for_search_seed_entries(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=_bog_complete_paradigm_cor_local(),
        verification_service=FakeVerificationService(),
        tts_service=FakeTTSService({}),
    )

    added = use_case.add_word(
        "bøger",
        "bog",
        search_seed={
            "lemma": "bog",
            "surface": "bøger",
            "cor_id": "COR.BOG.BOOK.PL",
            "cor_lemma_idx": 123,
            "meaning_key": "book",
            "gloss": "book",
            "english_translation": "book",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Plur|Definite=Ind",
        },
    )
    assert added.meaning is not None
    _verify_meaning_targets(use_case, lemma="bog", meaning_id=added.meaning.id, surfaces=["bøger"])

    response = use_case.complete_meaning_variations("bog", meaning_id=added.meaning.id)

    assert response.status == "updated"
    assert [
        (target.meaning_id, target.stored_surface_form)
        for target in response.queued_verification_targets
    ] == [(added.meaning.id, None)]
    assert response.added_surface_forms == ["bogen", "bøgerne"]
    assert response.queued_pronunciation_forms == ["bogen", "bøgerne"]

    details = use_case.get_lemma_details("bog")
    assert [form.form for form in details.meaning_sections[0].surface_forms] == ["bogen", "bøger", "bøgerne"]
    assert details.surface_forms == []

    with get_connection(db_path) as conn:
        jobs = conn.execute(
            """
            SELECT dedupe_key
            FROM wordbank_background_jobs
            WHERE job_type = 'generate_pronunciation'
            ORDER BY dedupe_key ASC
            """
        ).fetchall()
    assert [str(row["dedupe_key"]) for row in jobs] == [
        "generate_pronunciation::bog::bogen",
        "generate_pronunciation::bog::bøger",
        "generate_pronunciation::bog::bøgerne",
    ]


def test_complete_meaning_variations_uses_selected_homograph_meaning_only(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=_bog_complete_paradigm_cor_local(),
        verification_service=FakeVerificationService(),
    )

    first = use_case.add_word(
        "bogen",
        "bog",
        search_seed={
            "lemma": "bog",
            "surface": "bogen",
            "cor_id": "COR.BOG.BOOK.DEF",
            "cor_lemma_idx": 123,
            "meaning_key": "book",
            "gloss": "book",
            "english_translation": "book",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Def",
        },
    )
    second = use_case.add_word(
        "bogen",
        "bog",
        search_seed={
            "lemma": "bog",
            "surface": "bogen",
            "cor_id": "COR.BOG.SWAMP.DEF",
            "cor_lemma_idx": 124,
            "meaning_key": "swamp",
            "gloss": "swamp",
            "english_translation": "swamp",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Def",
        },
    )
    assert first.meaning is not None
    assert second.meaning is not None
    _verify_meaning_targets(use_case, lemma="bog", meaning_id=first.meaning.id, surfaces=["bogen"])

    response = use_case.complete_meaning_variations("bog", meaning_id=first.meaning.id)

    assert response.status == "updated"
    details = use_case.get_lemma_details("bog")
    assert [section.gloss for section in details.meaning_sections] == ["book", "swamp"]
    assert [form.form for form in details.meaning_sections[0].surface_forms] == ["bogen", "bøger", "bøgerne"]
    assert [form.form for form in details.meaning_sections[1].surface_forms] == ["bogen"]


def test_get_lemma_details_orders_standard_noun_variations_in_slot_order(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=_bog_complete_paradigm_cor_local(),
        verification_service=FakeVerificationService(),
    )

    for surface, cor_id, morphology in [
        ("bøger", "COR.BOG.BOOK.PL", "Gender=Com|Number=Plur|Definite=Ind"),
        ("bøgerne", "COR.BOG.BOOK.PLDEF", "Gender=Com|Number=Plur|Definite=Def"),
        ("bogen", "COR.BOG.BOOK.DEF", "Gender=Com|Number=Sing|Definite=Def"),
    ]:
        use_case.add_word(
            surface,
            "bog",
            search_seed={
                "lemma": "bog",
                "surface": surface,
                "cor_id": cor_id,
                "cor_lemma_idx": 123,
                "meaning_key": "book",
                "gloss": "book",
                "english_translation": "book",
                "pos_tag": "NOUN",
                "morphology": morphology,
            },
        )

    details = use_case.get_lemma_details("bog")

    assert [form.form for form in details.meaning_sections[0].surface_forms] == ["bogen", "bøger", "bøgerne"]


def test_get_lemma_details_keeps_irregular_other_variations_before_standard_noun_slots(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=_fader_complete_paradigm_cor_local(),
    )

    for surface, cor_id, morphology in [
        ("fædrene", "COR.FADER.PLDEF", "Gender=Com|Number=Plur|Definite=Def"),
        ("far", "COR.FADER.IRREG", "Gender=Com|Number=Sing|Definite=Ind"),
        ("faderen", "COR.FADER.DEF", "Gender=Com|Number=Sing|Definite=Def"),
        ("fædre", "COR.FADER.PL", "Gender=Com|Number=Plur|Definite=Ind"),
    ]:
        use_case.add_word(
            surface,
            "fader",
            search_seed={
                "lemma": "fader",
                "surface": surface,
                "cor_id": cor_id,
                "cor_lemma_idx": 410,
                "meaning_key": "father",
                "gloss": "father",
                "english_translation": "father",
                "pos_tag": "NOUN",
                "morphology": morphology,
            },
        )

    details = use_case.get_lemma_details("fader")

    assert [form.form for form in details.meaning_sections[0].surface_forms] == ["far", "faderen", "fædre", "fædrene"]


def test_complete_meaning_variations_skips_when_already_complete_or_cor_identity_missing(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=_bog_complete_paradigm_cor_local(),
        verification_service=FakeVerificationService(),
    )

    added = use_case.add_word(
        "bøgerne",
        "bog",
        search_seed={
            "lemma": "bog",
            "surface": "bøgerne",
            "cor_id": "COR.BOG.BOOK.PLDEF",
            "cor_lemma_idx": 123,
            "meaning_key": "book",
            "gloss": "book",
            "english_translation": "book",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Plur|Definite=Def",
        },
    )
    assert added.meaning is not None
    _verify_meaning_targets(use_case, lemma="bog", meaning_id=added.meaning.id, surfaces=["bøgerne"])
    updated = use_case.complete_meaning_variations("bog", meaning_id=added.meaning.id)
    _verify_meaning_targets(use_case, lemma="bog", meaning_id=added.meaning.id, surfaces=["bogen", "bøger", "bøgerne"])
    skipped = use_case.complete_meaning_variations("bog", meaning_id=added.meaning.id)

    assert updated.status == "updated"
    assert skipped.status == "skipped"
    assert skipped.added_surface_forms == []

    manual_dir = tmp_path / "manual"
    manual_dir.mkdir()
    manual_use_case = WordbankUseCase(_db_path(manual_dir), verification_service=FakeVerificationService())
    manual = manual_use_case.add_word(
        "Bogen",
        "bog",
        search_seed={
            "lemma": "bog",
            "surface": "bogen",
            "cor_id": "COR.BOG.BOOK.DEF",
            "cor_lemma_idx": None,
            "meaning_key": "book",
            "gloss": "book",
            "english_translation": "book",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Def",
        },
    )
    assert manual.meaning is not None
    _verify_meaning_targets(manual_use_case, lemma="bog", meaning_id=manual.meaning.id, surfaces=["bogen"])

    missing_identity = manual_use_case.complete_meaning_variations("bog", meaning_id=manual.meaning.id)

    assert missing_identity.status == "skipped"
    assert "COR identity" in missing_identity.message


def test_complete_meaning_variations_requeues_single_meaning_verification_review(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=_bog_complete_paradigm_cor_local(),
        verification_service=FakeVerificationService(),
    )

    added = use_case.add_word(
        "bøger",
        "bog",
        search_seed={
            "lemma": "bog",
            "surface": "bøger",
            "cor_id": "COR.BOG.BOOK.PL",
            "cor_lemma_idx": 123,
            "meaning_key": "book",
            "gloss": "book",
            "english_translation": "book",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Plur|Definite=Ind",
        },
    )
    assert added.meaning is not None
    _verify_meaning_targets(use_case, lemma="bog", meaning_id=added.meaning.id, surfaces=["bøger"])

    with get_connection(db_path) as conn:
        before_rows = conn.execute(
            """
            SELECT dedupe_key, payload_json
            FROM wordbank_background_jobs
            WHERE job_type = 'verify_word'
            ORDER BY id ASC
            """
        ).fetchall()

    response = use_case.complete_meaning_variations("bog", meaning_id=added.meaning.id)

    assert response.status == "updated"

    with get_connection(db_path) as conn:
        after_rows = conn.execute(
            """
            SELECT dedupe_key, payload_json
            FROM wordbank_background_jobs
            WHERE job_type = 'verify_word'
            ORDER BY id ASC
            """
        ).fetchall()
        verification_rows = conn.execute(
            """
            SELECT meaning_id, stored_surface_form, status
            FROM wordbank_verification_records
            ORDER BY id ASC
            """
        ).fetchall()

    assert len(after_rows) == len(before_rows) + 1
    new_job = after_rows[-1]
    new_payload = json.loads(str(new_job["payload_json"]))
    assert "complete_variations" in str(new_job["dedupe_key"])
    assert new_payload == {
        "meaning_id": added.meaning.id,
        "request_generation": new_payload["request_generation"],
        "review_intent": "complete_variations",
        "snapshot_hash": new_payload["snapshot_hash"],
        "stored_lemma": "bog",
        "stored_surface_form": None,
    }
    assert [(row["meaning_id"], row["stored_surface_form"], row["status"]) for row in verification_rows] == [
        (added.meaning.id, None, "queued")
    ]

    details = use_case.get_lemma_details("bog")
    assert details.meaning_sections[0].verification is not None
    assert details.meaning_sections[0].verification.status == "queued"
    assert all(form.verification is None for form in details.meaning_sections[0].surface_forms)


@pytest.mark.parametrize("provider", ["azure_translator", "deepl_translator"])
def test_wordbank_add_word_normalizes_framed_single_word_translation_for_all_providers(
    tmp_path: Path,
    provider: str,
) -> None:
    vin_entry = _cor_local_entry(
        cor_id="COR.VIN.110.01",
        lemma="vin",
        gloss=None,
        form="vin",
        lemma_idx=64001,
        pos_tag="NOUN",
        morphology="Gender=Neut|Number=Sing|Definite=Ind",
        gram_raw="sb.itk.sg.ubest",
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"vin": [vin_entry]},
            by_lemma_idx={64001: [vin_entry]},
        ),
        translation_service=FakeTranslationService({"et vin": "in wine"}, provider=provider),
    )

    use_case.add_word("Vin", "vin", cor_id="COR.VIN.110.01")

    listing = use_case.list_lemmas()
    details = use_case.get_lemma_details("vin")

    assert listing.items[0].english_translation == "wine"
    assert details.english_translation == "wine"

def test_wordbank_add_word_applies_selected_pos_and_morphology(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    use_case.add_word(
        "Gift",
        "gifte",
        pos_tag="verb",
        morphology="Mood=Imp|VerbForm=Fin",
    )

    details = use_case.get_lemma_details("gifte")
    assert details.pos_tag == "VERB"
    assert details.morphology == "Mood=Imp|VerbForm=Fin"
    assert details.surface_forms[0].pos_tag == "VERB"
    assert details.surface_forms[0].morphology == "Mood=Imp|VerbForm=Fin"

def test_wordbank_add_word_stores_lemma_form_when_surface_differs(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    use_case.add_word(
        "lærer",
        "lære",
        pos_tag="VERB",
        morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
    )

    details = use_case.get_lemma_details("lære")
    forms = {item.form: item for item in details.surface_forms}
    assert "lærer" in forms
    assert "lære" in forms
    assert forms["lærer"].morphology == "Tense=Pres|VerbForm=Fin|Voice=Act"

def test_wordbank_list_lemmas_uses_stored_pos_metadata_without_runtime_tokenization(tmp_path: Path) -> None:
    class CountingNLPAdapter:
        def __init__(self) -> None:
            self.calls = 0

        def tokenize(self, text: str) -> list[NLPToken]:
            self.calls += 1
            return [
                NLPToken(
                    text=text,
                    lemma=text.lower(),
                    pos="VERB",
                    morphology="VerbForm=Inf",
                    is_punctuation=False,
                )
            ]

        def lemma_candidates_for_token(self, token: str) -> list[str]:
            return [token.lower()]

        def lemma_for_token(self, token: str) -> str | None:
            return token.lower()

        def metadata(self) -> dict[str, str]:
            return {"adapter": "counting"}

    adapter = CountingNLPAdapter()
    use_case = WordbankUseCase(_db_path(tmp_path), nlp_adapter=adapter)

    use_case.add_word("Laver", "lave")
    calls_after_add = adapter.calls

    listing = use_case.list_lemmas()

    assert listing.items[0].display_lemma == "at lave"
    assert adapter.calls == calls_after_add

def test_wordbank_get_lemma_details_persists_extracted_pos_and_morphology_for_forms(tmp_path: Path) -> None:
    class CountingNLPAdapter:
        def __init__(self) -> None:
            self.calls = 0

        def tokenize(self, text: str) -> list[NLPToken]:
            self.calls += 1
            return [
                NLPToken(
                    text=text,
                    lemma=text.lower(),
                    pos="NOUN",
                    morphology="Number=Sing",
                    is_punctuation=False,
                )
            ]

        def lemma_candidates_for_token(self, token: str) -> list[str]:
            return [token.lower()]

        def lemma_for_token(self, token: str) -> str | None:
            return token.lower()

        def metadata(self) -> dict[str, str]:
            return {"adapter": "counting"}

    adapter = CountingNLPAdapter()
    use_case = WordbankUseCase(_db_path(tmp_path), nlp_adapter=adapter)

    use_case.add_word("Bogen", "bog")
    calls_after_add = adapter.calls

    details_first = use_case.get_lemma_details("bog")
    assert details_first.pos_tag == "NOUN"
    assert details_first.is_sectioned is True
    assert details_first.meaning_sections[0].surface_forms[0].pos_tag == "NOUN"

    details_second = use_case.get_lemma_details("bog")
    assert details_second.pos_tag == "NOUN"
    assert details_second.meaning_sections[0].surface_forms[0].morphology == "Number=Sing"


def test_wordbank_search_seed_add_stores_only_selected_search_payload(tmp_path: Path) -> None:
    class CountingNLPAdapter:
        def __init__(self) -> None:
            self.calls = 0

        def tokenize(self, text: str) -> list[NLPToken]:
            self.calls += 1
            return [
                NLPToken(
                    text=text,
                    lemma=text.lower(),
                    pos="NOUN",
                    morphology="Number=Sing",
                    is_punctuation=False,
                )
            ]

        def lemma_candidates_for_token(self, token: str) -> list[str]:
            return [token.lower()]

        def lemma_for_token(self, token: str) -> str | None:
            return token.lower()

        def metadata(self) -> dict[str, str]:
            return {"adapter": "counting"}

    nlp_adapter = CountingNLPAdapter()
    translation_service = FakeTranslationService({"lærere": "teachers"})
    gemini_service = FakeGeminiWordTranslationService({("lærere", "lærer", "teacher"): "teachers"})
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        translation_service=translation_service,
        gemini_word_translation_service=gemini_service,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_lemma_idx={
                49032: [
                    _cor_local_entry(
                        cor_id="COR.49032.110.01",
                        lemma="lærer",
                        gloss="teacher",
                        form="lærer",
                        lemma_idx=49032,
                        pos_tag="NOUN",
                        morphology="Gender=Com|Number=Sing|Definite=Ind",
                        gram_raw="sb.fk.sg.ubest",
                    ),
                    _cor_local_entry(
                        cor_id="COR.49032.112.01",
                        lemma="lærer",
                        gloss="teacher",
                        form="lærere",
                        lemma_idx=49032,
                        pos_tag="NOUN",
                        morphology="Gender=Com|Number=Plur|Definite=Ind",
                        gram_raw="sb.fk.pl.ubest",
                    ),
                ],
            },
        ),
    )

    added = use_case.add_word(
        "lærere",
        "lærer",
        search_seed={
            "lemma": "lærer",
            "surface": "lærere",
            "cor_id": "COR.49032.112.01",
            "cor_lemma_idx": 49032,
            "meaning_key": "teacher",
            "gloss": "teacher",
            "english_translation": "teacher",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Plur|Definite=Ind",
        },
    )

    details = use_case.get_lemma_details("lærer")

    assert added.saved_snapshot is not None
    assert translation_service.calls == []
    assert gemini_service.calls == []
    assert gemini_service.batch_calls == []
    assert nlp_adapter.calls == 0
    assert details.is_sectioned is True
    assert details.pos_tag == "NOUN"
    assert details.morphology == "Gender=Com|Number=Sing|Definite=Ind"
    assert details.meaning_sections[0].english_translation == "teacher"
    assert details.meaning_sections[0].morphology == "Gender=Com|Number=Sing|Definite=Ind"
    assert [item.form for item in details.meaning_sections[0].surface_forms] == ["lærere"]
    assert details.meaning_sections[0].surface_forms[0].morphology == "Gender=Com|Number=Plur|Definite=Ind"

    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT form
            FROM surface_forms sf
            JOIN lexemes l ON l.id = sf.lexeme_id
            WHERE l.lemma = ?
            ORDER BY form ASC
            """,
            ("lærer",),
        ).fetchall()
    assert [str(row["form"]) for row in rows] == ["lærere"]


def test_wordbank_search_seed_add_uses_canonical_lemma_metadata_for_verbs(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_lemma_idx={
                30686: [
                    _cor_local_entry(
                        cor_id="COR.30686.200.01",
                        lemma="lære",
                        gloss="learn",
                        form="lære",
                        lemma_idx=30686,
                        pos_tag="VERB",
                        morphology="VerbForm=Inf|Voice=Act",
                        gram_raw="vb.inf.akt",
                    ),
                    _cor_local_entry(
                        cor_id="COR.30686.203.01",
                        lemma="lære",
                        gloss="learn",
                        form="lærer",
                        lemma_idx=30686,
                        pos_tag="VERB",
                        morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
                        gram_raw="vb.præs.akt",
                    ),
                ],
            },
        ),
    )

    added = use_case.add_word(
        "lærer",
        "lære",
        search_seed={
            "lemma": "lære",
            "surface": "lærer",
            "cor_id": "COR.30686.203.01",
            "cor_lemma_idx": 30686,
            "meaning_key": "learn",
            "gloss": "learn",
            "english_translation": "learn",
            "pos_tag": "VERB",
            "morphology": "Tense=Pres|VerbForm=Fin|Voice=Act",
        },
    )

    details = use_case.get_lemma_details("lære")

    assert added.saved_snapshot is not None
    assert added.saved_snapshot.pos_tag == "VERB"
    assert added.saved_snapshot.morphology == "VerbForm=Inf|Voice=Act"
    assert details.pos_tag == "VERB"
    assert details.morphology == "VerbForm=Inf|Voice=Act"
    assert details.surface_forms == [
        LemmaDetailsResponse.SurfaceFormDetails(
            form="lærer",
            pos_tag="VERB",
            morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
            lemma="lære",
            lemma_translation="learn",
        )
    ]


def test_wordbank_search_seed_details_preserve_merged_gram_raw_for_adjective_lemma_forms(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_lemma_idx={
                20408: [
                    _cor_local_entry(
                        cor_id="COR.20408.300.01",
                        lemma="orange",
                        gloss="orange",
                        form="orange",
                        lemma_idx=20408,
                        pos_tag="ADJ",
                        morphology="Gender=Com|Number=Sing|Definite=Ind",
                        gram_raw="adj.sg.ubest.fk",
                    ),
                    _cor_local_entry(
                        cor_id="COR.20408.301.01",
                        lemma="orange",
                        gloss="orange",
                        form="orange",
                        lemma_idx=20408,
                        pos_tag="ADJ",
                        morphology="Gender=Neut|Number=Sing|Definite=Ind",
                        gram_raw="adj.sg.ubest.itk",
                    ),
                    _cor_local_entry(
                        cor_id="COR.20408.302.01",
                        lemma="orange",
                        gloss="orange",
                        form="orange",
                        lemma_idx=20408,
                        pos_tag="ADJ",
                        morphology="Number=Sing|Definite=Def",
                        gram_raw="adj.sg.best",
                    ),
                    _cor_local_entry(
                        cor_id="COR.20408.303.01",
                        lemma="orange",
                        gloss="orange",
                        form="orange",
                        lemma_idx=20408,
                        pos_tag="ADJ",
                        morphology="Number=Plur",
                        gram_raw="adj.pl",
                    ),
                ],
            },
            by_form={
                "orange": [
                    _cor_local_entry(
                        cor_id="COR.20408.300.01",
                        lemma="orange",
                        gloss="orange",
                        form="orange",
                        lemma_idx=20408,
                        pos_tag="ADJ",
                        morphology="Gender=Com|Number=Sing|Definite=Ind",
                        gram_raw="adj.sg.ubest.fk",
                    ),
                    _cor_local_entry(
                        cor_id="COR.20408.301.01",
                        lemma="orange",
                        gloss="orange",
                        form="orange",
                        lemma_idx=20408,
                        pos_tag="ADJ",
                        morphology="Gender=Neut|Number=Sing|Definite=Ind",
                        gram_raw="adj.sg.ubest.itk",
                    ),
                    _cor_local_entry(
                        cor_id="COR.20408.302.01",
                        lemma="orange",
                        gloss="orange",
                        form="orange",
                        lemma_idx=20408,
                        pos_tag="ADJ",
                        morphology="Number=Sing|Definite=Def",
                        gram_raw="adj.sg.best",
                    ),
                    _cor_local_entry(
                        cor_id="COR.20408.303.01",
                        lemma="orange",
                        gloss="orange",
                        form="orange",
                        lemma_idx=20408,
                        pos_tag="ADJ",
                        morphology="Number=Plur",
                        gram_raw="adj.pl",
                    ),
                ],
            },
        ),
    )

    use_case.add_word(
        "orange",
        "orange",
        search_seed={
            "lemma": "orange",
            "surface": "orange",
            "cor_id": "COR.20408.300.01",
            "cor_lemma_idx": 20408,
            "meaning_key": "orange",
            "gloss": "orange",
            "english_translation": "orange",
            "pos_tag": "ADJ",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )

    details = use_case.get_lemma_details("orange")

    assert details.is_sectioned is True
    assert details.meaning_sections[0].gram_raw == (
        "adj.sg.ubest.fk | adj.sg.ubest.itk | adj.sg.best | adj.pl"
    )
    assert details.surface_forms[0].gram_raw == (
        "adj.sg.ubest.fk | adj.sg.ubest.itk | adj.sg.best | adj.pl"
    )


def test_wordbank_search_seed_repeat_save_repairs_surface_derived_meaning_metadata(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    initial_use_case = WordbankUseCase(db_path)
    initial_use_case.add_word(
        "lærere",
        "lærer",
        search_seed={
            "lemma": "lærer",
            "surface": "lærere",
            "cor_id": "COR.49032.112.01",
            "cor_lemma_idx": 49032,
            "meaning_key": "teacher",
            "gloss": "teacher",
            "english_translation": "teacher",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Plur|Definite=Ind",
        },
    )

    repaired_use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_lemma_idx={
                49032: [
                    _cor_local_entry(
                        cor_id="COR.49032.110.01",
                        lemma="lærer",
                        gloss="teacher",
                        form="lærer",
                        lemma_idx=49032,
                        pos_tag="NOUN",
                        morphology="Gender=Com|Number=Sing|Definite=Ind",
                        gram_raw="sb.fk.sg.ubest",
                    ),
                    _cor_local_entry(
                        cor_id="COR.49032.112.01",
                        lemma="lærer",
                        gloss="teacher",
                        form="lærere",
                        lemma_idx=49032,
                        pos_tag="NOUN",
                        morphology="Gender=Com|Number=Plur|Definite=Ind",
                        gram_raw="sb.fk.pl.ubest",
                    ),
                ],
            },
        ),
    )

    repaired_use_case.add_word(
        "lærere",
        "lærer",
        search_seed={
            "lemma": "lærer",
            "surface": "lærere",
            "cor_id": "COR.49032.112.01",
            "cor_lemma_idx": 49032,
            "meaning_key": "teacher",
            "gloss": "teacher",
            "english_translation": "teacher",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Plur|Definite=Ind",
        },
    )

    details = repaired_use_case.get_lemma_details("lærer")

    assert details.morphology == "Gender=Com|Number=Sing|Definite=Ind"
    assert details.meaning_sections[0].morphology == "Gender=Com|Number=Sing|Definite=Ind"
    assert details.meaning_sections[0].surface_forms[0].morphology == "Gender=Com|Number=Plur|Definite=Ind"


def test_round_trip_word_page_search_seed_meanings_include_gloss_translation(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_lemma_idx={
                123: [
                    _cor_local_entry(
                        cor_id="COR.BOG.READING.LEM",
                        lemma="bog",
                        gloss="til læsning",
                        form="bog",
                        lemma_idx=123,
                        pos_tag="NOUN",
                        morphology="Gender=Com|Number=Sing|Definite=Ind",
                        gram_raw="sb.fk.sg.ubest",
                    ),
                ],
                124: [
                    _cor_local_entry(
                        cor_id="COR.BOG.BEECHMAST.LEM",
                        lemma="bog",
                        gloss="frugt fra et bøgetræ",
                        form="bog",
                        lemma_idx=124,
                        pos_tag="NOUN",
                        morphology="Gender=Neut|Number=Sing|Definite=Ind",
                        gram_raw="sb.itk.sg.ubest",
                    ),
                ],
            },
        ),
        translation_service=FakeTranslationService({
            "til læsning": "for reading",
            "frugt fra et bøgetræ": "fruit from a beech tree",
        }),
    )

    use_case.add_word(
        "bog",
        "bog",
        search_seed={
            "lemma": "bog",
            "surface": "bog",
            "cor_id": "COR.BOG.READING.LEM",
            "cor_lemma_idx": 123,
            "meaning_key": "for-reading",
            "gloss": "til læsning",
            "english_translation": "book",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )
    use_case.add_word(
        "bog",
        "bog",
        search_seed={
            "lemma": "bog",
            "surface": "bog",
            "cor_id": "COR.BOG.BEECHMAST.LEM",
            "cor_lemma_idx": 124,
            "meaning_key": "beechmast",
            "gloss": "frugt fra et bøgetræ",
            "english_translation": "beechmast",
            "pos_tag": "NOUN",
            "morphology": "Gender=Neut|Number=Sing|Definite=Ind",
        },
    )

    details = use_case.get_lemma_details("bog")

    assert details.is_sectioned is True
    assert [section.english_translation for section in details.meaning_sections] == ["book", "beechmast"]
    assert [section.gloss_translation for section in details.meaning_sections] == [
        "for reading",
        "fruit from a beech tree",
    ]
