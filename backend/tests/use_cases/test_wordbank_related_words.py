from __future__ import annotations

import json
from pathlib import Path

from app.db.repositories.wordbank_background_jobs import WordbankBackgroundJobRepository
from app.db.migrations import get_connection
from app.services.use_cases.wordbank import WordbankUseCase
from tests.helpers.factories import _cor_local_entry, _db_path
from tests.helpers.fakes import FakeCORLocalLexiconService, FakeGeminiRelatedWordsService


def _related_words_cor_local() -> FakeCORLocalLexiconService:
    legeplads = _cor_local_entry(
        cor_id="COR.LEGEPLADS.LEM",
        lemma="legeplads",
        gloss="playground",
        form="legeplads",
        lemma_idx=10,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    lege = _cor_local_entry(
        cor_id="COR.LEGE.LEM",
        lemma="lege",
        gloss="play",
        form="lege",
        lemma_idx=11,
        pos_tag="VERB",
        morphology="VerbForm=Inf|Voice=Act",
        gram_raw="vb.inf.akt",
    )
    plads_space = _cor_local_entry(
        cor_id="COR.PLADS.SPACE.LEM",
        lemma="plads",
        gloss="space",
        form="plads",
        lemma_idx=12,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    plads_square = _cor_local_entry(
        cor_id="COR.PLADS.SQUARE.LEM",
        lemma="plads",
        gloss="square",
        form="plads",
        lemma_idx=13,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    far_lemma = _cor_local_entry(
        cor_id="COR.FAR.LEM",
        lemma="far",
        gloss="father",
        form="far",
        lemma_idx=14,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    fader_lemma = _cor_local_entry(
        cor_id="COR.FADER.LEM",
        lemma="fader",
        gloss="father",
        form="fader",
        lemma_idx=15,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    fader_variation = _cor_local_entry(
        cor_id="COR.FADER.VAR",
        lemma="fader",
        gloss="father",
        form="far",
        lemma_idx=15,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    return FakeCORLocalLexiconService(
        by_form={
            "legeplads": [legeplads],
            "lege": [lege],
            "plads": [plads_space, plads_square],
            "far": [far_lemma, fader_variation],
            "fader": [fader_lemma],
        },
        by_lemma_idx={
            15: [fader_lemma, fader_variation],
        },
    )


def test_add_word_queues_related_words_and_saved_snapshot_starts_queued(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        gemini_related_words_service=FakeGeminiRelatedWordsService({"legeplads": [("lege", "play", "VERB")]}),
    )

    response = use_case.add_word("legeplads", "legeplads")

    assert response.saved_snapshot is not None
    assert response.saved_snapshot.related_words.status == "queued"
    assert response.saved_snapshot.related_words.items == []

    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT job_type, dedupe_key, payload_json, status
            FROM wordbank_background_jobs
            WHERE job_type = 'resolve_related_words'
            """
        ).fetchall()

    assert len(rows) == 1
    assert str(rows[0]["job_type"]) == "resolve_related_words"
    assert str(rows[0]["dedupe_key"]) == "resolve_related_words::legeplads"
    assert json.loads(str(rows[0]["payload_json"])) == {"stored_lemma": "legeplads"}
    assert str(rows[0]["status"]) == "pending"


def test_process_related_words_persists_candidates_and_replaces_stale_rows(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    related_words_service = FakeGeminiRelatedWordsService({
        "legeplads": [
            ("lege", "play", "VERB"),
            ("plads", "space", "NOUN"),
            ("ukendt", "unknown", "NOUN"),
        ]
    })
    use_case = WordbankUseCase(
        db_path,
        gemini_related_words_service=related_words_service,
        cor_local_lexicon_service=_related_words_cor_local(),
    )

    use_case.add_word("legeplads", "legeplads")
    use_case.process_queued_related_words("legeplads")
    _mark_related_words_job_completed(db_path, "legeplads")

    details = use_case.get_lemma_details("legeplads")

    assert details.related_words.status == "ready"
    assert [item.lemma for item in details.related_words.items] == ["lege", "plads"]
    assert details.related_words.items[0].english_translation == "to play"
    assert details.related_words.items[0].display_variant is not None
    assert details.related_words.items[0].display_variant.cor_id == "COR.LEGE.LEM"
    assert details.related_words.items[0].candidate_variants == []
    assert details.related_words.items[1].display_variant is None
    assert {variant.cor_id for variant in details.related_words.items[1].candidate_variants} == {
        "COR.PLADS.SPACE.LEM",
        "COR.PLADS.SQUARE.LEM",
    }

    related_words_service._mapping["legeplads"] = [("plads", "space", "NOUN")]
    use_case.process_queued_related_words("legeplads")

    refreshed = use_case.get_lemma_details("legeplads")

    assert refreshed.related_words.status == "ready"
    assert [item.lemma for item in refreshed.related_words.items] == ["plads"]

    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT related_lemma
            FROM wordbank_related_words
            ORDER BY sort_order ASC, id ASC
            """
        ).fetchall()

    assert [str(row["related_lemma"]) for row in rows] == ["plads"]


def test_related_words_report_saved_lemma_and_saved_variation_targets(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        gemini_related_words_service=FakeGeminiRelatedWordsService({
            "legefar": [
                ("lege", "play", "VERB"),
                ("far", "father", "NOUN"),
            ]
        }),
        cor_local_lexicon_service=_related_words_cor_local(),
    )

    use_case.add_word("lege", "lege", pos_tag="VERB", morphology="VerbForm=Inf|Voice=Act")
    saved_variation = use_case.add_word(
        "far",
        "fader",
        search_seed={
            "lemma": "fader",
            "surface": "far",
            "cor_id": "COR.FADER.VAR",
            "cor_lemma_idx": 15,
            "meaning_key": "father",
            "gloss": "father",
            "english_translation": "father",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )
    assert saved_variation.meaning is not None

    use_case.add_word("legefar", "legefar")
    use_case.process_queued_related_words("legefar")

    details = use_case.get_lemma_details("legefar")
    items_by_lemma = {item.lemma: item for item in details.related_words.items}

    assert items_by_lemma["lege"].saved_match.status == "saved_lemma"
    assert items_by_lemma["lege"].saved_match.target_lemma == "lege"
    assert items_by_lemma["lege"].saved_match.target_meaning_id is None

    assert items_by_lemma["far"].saved_match.status == "saved_variation"
    assert items_by_lemma["far"].saved_match.target_lemma == "fader"
    assert items_by_lemma["far"].saved_match.target_meaning_id == saved_variation.meaning.id


def test_related_words_add_additional_translation_to_saved_lemma_page(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        gemini_related_words_service=FakeGeminiRelatedWordsService({
            "legeplads": [("lege", "frolic", "VERB")]
        }),
        cor_local_lexicon_service=_related_words_cor_local(),
    )

    use_case.add_word("lege", "lege", pos_tag="VERB", morphology="VerbForm=Inf|Voice=Act")
    use_case.add_word("legeplads", "legeplads")
    use_case.process_queued_related_words("legeplads")
    _mark_related_words_job_completed(db_path, "legeplads")

    details = use_case.get_lemma_details("lege")

    assert details.english_translation is None
    assert details.additional_translations == ["to frolic"]


def test_related_words_add_reverse_compound_links_and_saved_translation_to_saved_target(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        gemini_related_words_service=FakeGeminiRelatedWordsService({
            "legeplads": [
                ("lege", "play", "VERB"),
                ("plads", "place", "NOUN"),
            ]
        }),
        cor_local_lexicon_service=_related_words_cor_local(),
    )

    use_case.add_word(
        "plads",
        "plads",
        search_seed={
            "lemma": "plads",
            "surface": "plads",
            "cor_id": "COR.PLADS.SPACE.LEM",
            "cor_lemma_idx": 12,
            "meaning_key": "space",
            "gloss": "space",
            "english_translation": "seat",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )
    use_case.add_word("lege", "lege", pos_tag="VERB", morphology="VerbForm=Inf|Voice=Act")
    use_case.add_word("legeplads", "legeplads")
    use_case.process_queued_related_words("legeplads")
    _mark_related_words_job_completed(db_path, "legeplads")

    plads_details = use_case.get_lemma_details("plads")
    lege_details = use_case.get_lemma_details("lege")

    assert [item.lemma for item in plads_details.related_words.items] == ["legeplads"]
    assert plads_details.related_words.items[0].relation_type == "compound_host"
    assert plads_details.related_words.items[0].saved_match.status == "saved_lemma"
    assert plads_details.meaning_sections[0].english_translation == "seat"
    assert plads_details.meaning_sections[0].additional_translations == ["place"]

    assert [item.lemma for item in lege_details.related_words.items] == ["legeplads"]
    assert lege_details.related_words.items[0].relation_type == "compound_host"
    assert lege_details.related_words.items[0].saved_match.status == "saved_lemma"


def test_related_words_add_additional_translation_to_saved_variation_meaning(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        gemini_related_words_service=FakeGeminiRelatedWordsService({
            "legefar": [("far", "dad", "NOUN")]
        }),
        cor_local_lexicon_service=_related_words_cor_local(),
    )

    saved_variation = use_case.add_word(
        "far",
        "fader",
        search_seed={
            "lemma": "fader",
            "surface": "far",
            "cor_id": "COR.FADER.VAR",
            "cor_lemma_idx": 15,
            "meaning_key": "father",
            "gloss": "father",
            "english_translation": "father",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )
    assert saved_variation.meaning is not None

    use_case.add_word("legefar", "legefar")
    use_case.process_queued_related_words("legefar")
    _mark_related_words_job_completed(db_path, "legefar")

    details = use_case.get_lemma_details("fader")

    assert details.meaning_sections[0].id == saved_variation.meaning.id
    assert details.meaning_sections[0].english_translation == "father"
    assert details.meaning_sections[0].additional_translations == ["dad"]


def test_non_compound_related_words_finish_as_empty(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        gemini_related_words_service=FakeGeminiRelatedWordsService({"enkeltord": []}),
    )

    use_case.add_word("enkeltord", "enkeltord")
    use_case.process_queued_related_words("enkeltord")
    _mark_related_words_job_completed(db_path, "enkeltord")

    details = use_case.get_lemma_details("enkeltord")

    assert details.related_words.status == "empty"
    assert details.related_words.items == []


def test_gemini_picks_gloss_variant_sets_display_variant_not_candidates(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        gemini_related_words_service=FakeGeminiRelatedWordsService(
            mapping={"legeplads": [("plads", "space", "NOUN")]},
            gloss_picks={"plads": "COR.PLADS.SPACE.LEM"},
        ),
        cor_local_lexicon_service=_related_words_cor_local(),
    )

    use_case.add_word("legeplads", "legeplads")
    use_case.process_queued_related_words("legeplads")
    _mark_related_words_job_completed(db_path, "legeplads")

    details = use_case.get_lemma_details("legeplads")

    assert details.related_words.status == "ready"
    plads_item = details.related_words.items[0]
    assert plads_item.lemma == "plads"
    assert plads_item.display_variant is not None
    assert plads_item.display_variant.cor_id == "COR.PLADS.SPACE.LEM"
    assert plads_item.candidate_variants == []


def test_gemini_uncertain_gloss_variant_falls_back_to_candidate_variants(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        gemini_related_words_service=FakeGeminiRelatedWordsService(
            mapping={"legeplads": [("plads", "space", "NOUN")]},
            gloss_picks={},
        ),
        cor_local_lexicon_service=_related_words_cor_local(),
    )

    use_case.add_word("legeplads", "legeplads")
    use_case.process_queued_related_words("legeplads")
    _mark_related_words_job_completed(db_path, "legeplads")

    details = use_case.get_lemma_details("legeplads")

    plads_item = details.related_words.items[0]
    assert plads_item.display_variant is None
    assert {v.cor_id for v in plads_item.candidate_variants} == {
        "COR.PLADS.SPACE.LEM",
        "COR.PLADS.SQUARE.LEM",
    }


def _mark_related_words_job_completed(db_path: Path, lemma: str) -> None:
    jobs = WordbankBackgroundJobRepository(db_path)
    job = jobs.get_by_dedupe_key(f"resolve_related_words::{lemma}")
    assert job is not None
    jobs.mark_completed(job.id)
