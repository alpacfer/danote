from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.api.schemas.v1.wordbank import LemmaDetailsResponse
from app.db.migrations import get_connection
from app.nlp.adapter import NLPToken
from app.services.tts import PronunciationAudio
from app.db.repositories.wordbank import WordbankRepository
from app.services.use_cases.wordbank import WordbankUseCase
from app.services.verification import GeminiWordVerificationService, WordVerificationAction
from tests.helpers.factories import _bog_homograph_cor_local, _cor_local_entry, _db_path
from tests.helpers.fakes import (
    FakeCORLocalLexiconService,
    FakeGeminiWordTranslationService,
    FakeNLPAdapter,
    FakeTranslationService,
    FakeTTSService,
    FakeVerificationService,
)


def test_search_seed_repeat_save_does_not_requeue_completed_pronunciation_when_audio_exists(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        tts_service=FakeTTSService({"bog": b"lemma-wav", "bogen": b"surface-wav"}),
    )

    payload = {
        "lemma": "bog",
        "surface": "bogen",
        "cor_id": "COR.BOG.BOOK.1",
        "cor_lemma_idx": 123,
        "meaning_key": "book",
        "gloss": "book",
        "english_translation": "book",
        "pos_tag": "NOUN",
        "morphology": "Gender=Com|Number=Sing|Definite=Def",
    }

    first = use_case.add_word("bogen", "bog", search_seed=payload)
    assert first.queued_pronunciation_forms == ["bog", "bogen"]

    use_case.process_queued_pronunciations("bog", requested_forms=["bog", "bogen"])
    with get_connection(db_path) as conn:
        job_id = int(
            conn.execute(
                """
                SELECT id
                FROM wordbank_background_jobs
                WHERE job_type = 'generate_pronunciation'
                LIMIT 1
                """
            ).fetchone()["id"]
        )
        conn.execute(
            """
            UPDATE wordbank_background_jobs
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (job_id,),
        )

    second = use_case.add_word("bogen", "bog", search_seed=payload)

    assert second.queued_pronunciation_forms == []
    with get_connection(db_path) as conn:
        job_row = conn.execute(
            """
            SELECT status, payload_json
            FROM wordbank_background_jobs
            WHERE job_type = 'generate_pronunciation'
            LIMIT 1
            """
        ).fetchone()
        audio_rows = conn.execute(
            """
            SELECT form, pronunciation_audio IS NOT NULL AS has_audio
            FROM surface_forms
            WHERE form IN ('bog', 'bogen')
            ORDER BY form ASC
            """
        ).fetchall()

    assert job_row is not None
    assert str(job_row["status"]) == "completed"
    assert json.loads(str(job_row["payload_json"])) == {
        "force": False,
        "requested_forms": ["bog", "bogen"],
        "stored_lemma": "bog",
    }
    assert [(str(row["form"]), int(row["has_audio"])) for row in audio_rows] == [
        ("bog", 1),
        ("bogen", 1),
    ]


def test_wordbank_use_case_runs_verification_task_and_returns_result(tmp_path: Path) -> None:
    verification_service = FakeVerificationService(
        verdict="verified",
        message="Lemma, surface form, and translations are coherent.",
        categories=("Food", "Household Objects"),
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"bog": "book", "bogen": "the book"}),
        verification_service=verification_service,
    )

    added = use_case.add_word("Bogen", "bog")

    assert added.verification is not None
    assert added.verification.status == "queued"
    assert added.verification.provider == "gemini"
    assert added.verification.reviewer_role == "Professional Danish Language Expert"
    assert "queued" in added.verification.message.lower()
    assert added.verification.requested_at is not None

    details_while_queued = use_case.get_lemma_details("bog")
    assert details_while_queued.meaning_sections[0].verification is not None
    assert details_while_queued.meaning_sections[0].verification.status == "queued"

    verified = use_case.verify_added_word("bog", "bogen", meaning_id=added.meaning.id if added.meaning else None)
    assert verified.verification.status == "verified"
    assert verified.applied_categories == ["Food", "Household Objects"]
    assert "coherent" in verified.verification.message.lower()
    assert verified.verification.requested_at is not None
    assert verified.verification.completed_at is not None
    assert len(verification_service.calls) == 1

    details_after_verify = use_case.get_lemma_details("bog")
    assert details_after_verify.meaning_sections[0].categories == ["Food", "Household Objects"]
    assert details_after_verify.meaning_sections[0].verification is not None
    assert details_after_verify.meaning_sections[0].verification.status == "queued"
    verified_surface = next(item for item in details_after_verify.meaning_sections[0].surface_forms if item.form == "bogen")
    assert verified_surface.verification is not None
    assert verified_surface.verification.status == "verified"


def test_wordbank_use_case_replaces_meaning_categories_on_reverify(tmp_path: Path) -> None:
    verification_service = FakeVerificationService(
        verdict="verified",
        message="Entry is consistent.",
        categories=("Food", "Plants"),
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"bog": "book", "bogen": "the book"}),
        verification_service=verification_service,
    )

    added = use_case.add_word("Bogen", "bog")
    first = use_case.verify_added_word("bog", "bogen", meaning_id=added.meaning.id if added.meaning else None)
    assert first.applied_categories == ["Food", "Plants"]

    verification_service._categories = ("Household Objects",)
    second = use_case.verify_added_word("bog", "bogen", meaning_id=added.meaning.id if added.meaning else None)

    assert second.applied_categories == ["Household Objects"]
    details = use_case.get_lemma_details("bog")
    assert details.meaning_sections[0].categories == ["Household Objects"]


def test_wordbank_use_case_rethinks_categories_without_changing_verification_state(tmp_path: Path) -> None:
    verification_service = FakeVerificationService(
        verdict="verified",
        message="Entry is consistent.",
        categories=("Food",),
        recategorized_categories=("Food", "Reading Material", "Education", "Culture"),
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"bog": "book", "bogen": "the book"}),
        verification_service=verification_service,
    )

    added = use_case.add_word("Bogen", "bog")
    use_case.verify_added_word("bog", "bogen", meaning_id=added.meaning.id if added.meaning else None)
    details_before = use_case.get_lemma_details("bog")

    rethought = use_case.rethink_categories("bog", None, meaning_id=added.meaning.id if added.meaning else None)

    assert rethought.status == "updated"
    assert rethought.applied_categories == ["Culture", "Education", "Food", "Reading Material"]
    assert len(verification_service.category_calls) == 2
    assert verification_service.calls[0].available_surface_forms == verification_service.category_calls[-1].available_surface_forms
    assert verification_service.category_calls[-1].available_surface_forms[0].form == "bog"
    assert verification_service.category_calls[-1].available_surface_forms[0].english_translation == "book"
    details_after = use_case.get_lemma_details("bog")
    assert details_after.meaning_sections[0].categories == ["Culture", "Education", "Food", "Reading Material"]
    assert details_before.meaning_sections[0].verification == details_after.meaning_sections[0].verification


def test_wordbank_use_case_keeps_existing_categories_when_verification_errors(tmp_path: Path) -> None:
    class FlakyVerificationService:
        provider = "gemini"
        reviewer_role = "Professional Danish Language Expert"

        def __init__(self) -> None:
            self.calls = 0

        def verify_word_entry(self, payload):
            self.calls += 1
            if self.calls == 1:
                class Result:
                    verdict = "verified"
                    message = "OK"

                return Result()
            raise RuntimeError("provider unavailable")

        def classify_word_categories(self, _payload):
            class Result:
                categories = ("Food",)

            return Result()

    verification_service = FlakyVerificationService()
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"bog": "book", "bogen": "the book"}),
        verification_service=verification_service,
    )

    added = use_case.add_word("Bogen", "bog")
    first = use_case.verify_added_word("bog", "bogen", meaning_id=added.meaning.id if added.meaning else None)
    assert first.applied_categories == ["Food"]

    second = use_case.verify_added_word("bog", "bogen", meaning_id=added.meaning.id if added.meaning else None)

    assert second.verification.status == "error"
    assert second.applied_categories == []
    details = use_case.get_lemma_details("bog")
    assert details.meaning_sections[0].categories == ["Food"]


def test_word_verification_payload_uses_saved_and_canonical_metadata_for_search_seed_entries(tmp_path: Path) -> None:
    verification_service = FakeVerificationService(
        verdict="verified",
        message="Entry is consistent.",
        categories=("Actions", "School"),
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        verification_service=verification_service,
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

    assert added.meaning is not None
    verified = use_case.verify_added_word("lære", "lærer", meaning_id=added.meaning.id)

    payload = verification_service.calls[0]
    assert verified.applied_categories == ["Actions", "School"]
    assert payload.selected_translation == "learn"
    assert payload.selected_translation_scope == "meaning_section"
    assert payload.available_categories
    assert [form.form for form in payload.available_surface_forms] == ["lærer"]
    assert payload.canonical_lemma_pos_tag == "VERB"
    assert payload.canonical_lemma_morphology == "VerbForm=Inf|Voice=Act"
    assert payload.selected_surface_pos_tag == "VERB"
    assert payload.selected_surface_morphology == "Tense=Pres|VerbForm=Fin|Voice=Act"
    details = use_case.get_lemma_details("lære")
    assert details.meaning_sections[0].categories == ["Actions", "School"]


def test_complete_variations_verification_payload_preserves_merged_gram_raw_for_shared_adjective_forms(
    tmp_path: Path,
) -> None:
    verification_service = FakeVerificationService(
        verdict="verified",
        message="Entry is consistent.",
    )
    smuk_n = _cor_local_entry(
        cor_id="COR.SMUK.N",
        lemma="smuk",
        gloss="beautiful",
        form="smuk",
        lemma_idx=221,
        pos_tag="ADJ",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="adj.sg.ubest.fk",
    )
    smuk_t = _cor_local_entry(
        cor_id="COR.SMUK.T",
        lemma="smuk",
        gloss="beautiful",
        form="smukt",
        lemma_idx=221,
        pos_tag="ADJ",
        morphology="Gender=Neut|Number=Sing|Definite=Ind",
        gram_raw="adj.sg.ubest.itk",
    )
    smuk_def = _cor_local_entry(
        cor_id="COR.SMUK.DEF",
        lemma="smuk",
        gloss="beautiful",
        form="smukke",
        lemma_idx=221,
        pos_tag="ADJ",
        morphology="Number=Sing|Definite=Def",
        gram_raw="adj.sg.best",
    )
    smuk_pl = _cor_local_entry(
        cor_id="COR.SMUK.PL",
        lemma="smuk",
        gloss="beautiful",
        form="smukke",
        lemma_idx=221,
        pos_tag="ADJ",
        morphology="Number=Plur",
        gram_raw="adj.pl",
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"smuk": [smuk_n], "smukt": [smuk_t], "smukke": [smuk_def, smuk_pl]},
            by_lemma_idx={221: [smuk_n, smuk_t, smuk_def, smuk_pl]},
        ),
        verification_service=verification_service,
    )

    added = use_case.add_word(
        "smukt",
        "smuk",
        search_seed={
            "lemma": "smuk",
            "surface": "smukt",
            "cor_id": "COR.SMUK.T",
            "cor_lemma_idx": 221,
            "meaning_key": "beautiful",
            "gloss": "beautiful",
            "english_translation": "beautiful",
            "pos_tag": "ADJ",
            "morphology": "Gender=Neut|Number=Sing|Definite=Ind",
        },
    )
    assert added.meaning is not None

    with get_connection(_db_path(tmp_path)) as conn:
        lexeme = conn.execute("SELECT id FROM lexemes WHERE lemma = ?", ("smuk",)).fetchone()
        assert lexeme is not None
        conn.execute(
            """
            INSERT INTO surface_forms (lexeme_id, meaning_id, form, source, pos_tag, morphology)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(lexeme["id"]),
                added.meaning.id,
                "smukke",
                "search",
                "ADJ",
                "Number=Sing|Definite=Def",
            ),
        )

    use_case.verify_added_word(
        "smuk",
        None,
        meaning_id=added.meaning.id,
        review_intent="complete_variations",
    )

    payload = verification_service.calls[0]
    smukke = next(form for form in payload.available_surface_forms if form.form == "smukke")

    assert smukke.gram_raw == "adj.sg.best | adj.pl"


def test_word_verification_payload_for_homograph_meaning_uses_translated_gloss_context(tmp_path: Path) -> None:
    verification_service = FakeVerificationService(
        verdict="verified",
        message="Entry is consistent.",
    )
    person = _cor_local_entry(
        cor_id="COR.MOR.PERSON.LEM",
        lemma="mor",
        gloss="person",
        form="mor",
        lemma_idx=51046,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    soil = _cor_local_entry(
        cor_id="COR.MOR.SOIL.LEM",
        lemma="mor",
        gloss="jordlag",
        form="mor",
        lemma_idx=51047,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"mor": [person, soil]},
            by_lemma_idx={51046: [person], 51047: [soil]},
        ),
        translation_service=FakeTranslationService({"person": "person", "jordlag": "soil layer"}),
        verification_service=verification_service,
    )

    use_case.add_word(
        "mor",
        "mor",
        search_seed={
            "lemma": "mor",
            "surface": "mor",
            "cor_id": "COR.MOR.PERSON.LEM",
            "cor_lemma_idx": 51046,
            "meaning_key": "person",
            "gloss": "person",
            "english_translation": "mother",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )
    added = use_case.add_word(
        "mor",
        "mor",
        search_seed={
            "lemma": "mor",
            "surface": "mor",
            "cor_id": "COR.MOR.SOIL.LEM",
            "cor_lemma_idx": 51047,
            "meaning_key": "soil-layer",
            "gloss": "jordlag",
            "english_translation": "mother",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )

    use_case.verify_added_word("mor", None, meaning_id=added.meaning.id if added.meaning else None)

    payload = verification_service.calls[-1]
    assert payload.meaning_gloss == "jordlag"
    assert payload.meaning_gloss_translation == "soil layer"
    assert [(section.id, section.meaning_key, section.gloss_translation) for section in payload.sibling_meaning_sections] == [
        (1, "person", "person")
    ]
    assert [
        (form.meaning_id, form.form, form.gloss_translation)
        for form in payload.available_surface_forms
    ] == [
        (1, "mor", "person"),
        (2, "mor", "soil layer"),
    ]


def test_word_verification_payload_preserves_imperative_metadata_for_bile_homograph_surface(tmp_path: Path) -> None:
    verification_service = FakeVerificationService(
        verdict="verified",
        message="Entry is consistent.",
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_lemma_idx={
                36439: [
                    _cor_local_entry(
                        cor_id="COR.36439.200.01",
                        lemma="bile",
                        gloss="køre i bil",
                        form="bile",
                        lemma_idx=36439,
                        pos_tag="VERB",
                        morphology="VerbForm=Inf|Voice=Act",
                        gram_raw="vb.inf.akt",
                    ),
                    _cor_local_entry(
                        cor_id="COR.36439.209.01",
                        lemma="bile",
                        gloss="køre i bil",
                        form="bil",
                        lemma_idx=36439,
                        pos_tag="VERB",
                        morphology="Mood=Imp|VerbForm=Fin",
                        gram_raw="vb.imp",
                    ),
                ],
            },
        ),
        translation_service=FakeTranslationService({"køre i bil": "go by car"}),
        verification_service=verification_service,
    )

    added = use_case.add_word(
        "bil",
        "bile",
        search_seed={
            "lemma": "bile",
            "surface": "bil",
            "cor_id": "COR.36439.209.01",
            "cor_lemma_idx": 36439,
            "meaning_key": "bile",
            "gloss": "køre i bil",
            "english_translation": "to bile",
            "pos_tag": "VERB",
            "morphology": "Mood=Imp|VerbForm=Fin",
        },
    )

    assert added.meaning is not None

    use_case.verify_added_word("bile", "bil", meaning_id=added.meaning.id)

    payload = verification_service.calls[-1]
    bil = next(form for form in payload.available_surface_forms if form.form == "bil")
    assert payload.selected_translation == "to bile"
    assert payload.meaning_gloss_translation == "go by car"
    assert payload.selected_surface_pos_tag == "VERB"
    assert payload.selected_surface_morphology == "Mood=Imp|VerbForm=Fin"
    assert bil.pos_tag == "VERB"
    assert bil.morphology == "Mood=Imp|VerbForm=Fin"
    assert bil.gram_raw == "vb.imp"


def test_verify_added_word_flags_missing_bile_translation_from_gloss_hint(tmp_path: Path, monkeypatch) -> None:
    verification_service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        verification_service,
        "_generate_text",
        lambda prompt: '{"verdict":"correct","word_count":1,"suggested_actions":[]}',
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_lemma_idx={
                36439: [
                    _cor_local_entry(
                        cor_id="COR.36439.200.01",
                        lemma="bile",
                        gloss="køre i bil",
                        form="bile",
                        lemma_idx=36439,
                        pos_tag="VERB",
                        morphology="VerbForm=Inf|Voice=Act",
                        gram_raw="vb.inf.akt",
                    ),
                    _cor_local_entry(
                        cor_id="COR.36439.209.01",
                        lemma="bile",
                        gloss="køre i bil",
                        form="bil",
                        lemma_idx=36439,
                        pos_tag="VERB",
                        morphology="Mood=Imp|VerbForm=Fin",
                        gram_raw="vb.imp",
                    ),
                ],
            },
        ),
        translation_service=FakeTranslationService({"køre i bil": "go by car"}),
        verification_service=verification_service,
    )

    added = use_case.add_word(
        "bil",
        "bile",
        search_seed={
            "lemma": "bile",
            "surface": "bil",
            "cor_id": "COR.36439.209.01",
            "cor_lemma_idx": 36439,
            "meaning_key": "bile",
            "gloss": "køre i bil",
            "english_translation": None,
            "pos_tag": "VERB",
            "morphology": "Mood=Imp|VerbForm=Fin",
        },
    )

    assert added.meaning is not None

    verified = use_case.verify_added_word("bile", None, meaning_id=added.meaning.id)

    assert verified.verification.status == "flagged"
    assert [action.action_type for action in verified.verification.suggested_actions] == ["fix_translation"]
    assert verified.verification.suggested_actions[0].english_translation == "go by car"


def test_verify_added_word_flags_missing_have_translation_without_gloss_hint(
    tmp_path: Path,
    monkeypatch,
) -> None:
    verification_service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        verification_service,
        "_generate_text",
        lambda prompt: '{"verdict":"correct","word_count":1,"suggested_actions":[]}',
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_lemma_idx={
                30035: [
                    _cor_local_entry(
                        cor_id="COR.30035.200.01",
                        lemma="have",
                        gloss=None,
                        form="have",
                        lemma_idx=30035,
                        pos_tag="VERB",
                        morphology="VerbForm=Inf|Voice=Act",
                        gram_raw="vb.inf.akt",
                    ),
                    _cor_local_entry(
                        cor_id="COR.30035.203.01",
                        lemma="have",
                        gloss=None,
                        form="har",
                        lemma_idx=30035,
                        pos_tag="VERB",
                        morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
                        gram_raw="vb.præs.akt",
                    ),
                ],
            },
        ),
        verification_service=verification_service,
    )

    added = use_case.add_word(
        "har",
        "have",
        search_seed={
            "lemma": "have",
            "surface": "har",
            "cor_id": "COR.30035.203.01",
            "cor_lemma_idx": 30035,
            "meaning_key": "have",
            "gloss": None,
            "english_translation": None,
            "pos_tag": "VERB",
            "morphology": "Tense=Pres|VerbForm=Fin|Voice=Act",
        },
    )

    assert added.meaning is not None

    verified = use_case.verify_added_word("have", None, meaning_id=added.meaning.id)

    assert verified.verification.status == "flagged"
    assert verified.verification.problem == "The English translation is missing."
    assert verified.verification.change_to_implement == "Add an English translation for this entry."
    assert verified.verification.suggested_actions == []


def test_verify_added_word_auto_applies_gemini_translation_for_missing_have_translation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    verification_service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        verification_service,
        "_generate_text",
        lambda prompt: '{"verdict":"correct","word_count":1,"suggested_actions":[]}',
    )
    gemini_translation = FakeGeminiWordTranslationService({("har", "have", None): "have"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_lemma_idx={
                30035: [
                    _cor_local_entry(
                        cor_id="COR.30035.200.01",
                        lemma="have",
                        gloss=None,
                        form="have",
                        lemma_idx=30035,
                        pos_tag="VERB",
                        morphology="VerbForm=Inf|Voice=Act",
                        gram_raw="vb.inf.akt",
                    ),
                    _cor_local_entry(
                        cor_id="COR.30035.203.01",
                        lemma="have",
                        gloss=None,
                        form="har",
                        lemma_idx=30035,
                        pos_tag="VERB",
                        morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
                        gram_raw="vb.præs.akt",
                    ),
                ],
            },
        ),
        gemini_word_translation_service=gemini_translation,
        verification_service=verification_service,
    )

    added = use_case.add_word(
        "har",
        "have",
        search_seed={
            "lemma": "have",
            "surface": "har",
            "cor_id": "COR.30035.203.01",
            "cor_lemma_idx": 30035,
            "meaning_key": "have",
            "gloss": None,
            "english_translation": None,
            "pos_tag": "VERB",
            "morphology": "Tense=Pres|VerbForm=Fin|Voice=Act",
        },
    )

    assert added.meaning is not None

    verified = use_case.verify_added_word("have", None, meaning_id=added.meaning.id)
    details = use_case.get_lemma_details("have")

    assert verified.verification.status == "verified"
    assert details.meaning_sections[0].english_translation == "to have"
    assert gemini_translation.calls == [("har", "have", None)]


def test_word_verification_payload_exposes_cor_canonical_lemma_when_saved_lemma_is_inflected(tmp_path: Path) -> None:
    verification_service = FakeVerificationService(
        verdict="verified",
        message="Entry is consistent.",
    )
    canonical_lemma = _cor_local_entry(
        cor_id="COR.MODER.LEM",
        lemma="moder",
        gloss="person",
        form="moder",
        lemma_idx=61046,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    inflected_surface = _cor_local_entry(
        cor_id="COR.MODER.SURF",
        lemma="moder",
        gloss="person",
        form="mor",
        lemma_idx=61046,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"mor": [inflected_surface]},
            by_lemma_idx={61046: [canonical_lemma, inflected_surface]},
        ),
        translation_service=FakeTranslationService({"person": "person"}),
        verification_service=verification_service,
    )

    added = use_case.add_word(
        "mor",
        "mor",
        search_seed={
            "lemma": "mor",
            "surface": "mor",
            "cor_id": "COR.MODER.SURF",
            "cor_lemma_idx": 61046,
            "meaning_key": "person",
            "gloss": "person",
            "english_translation": "mother",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )

    use_case.verify_added_word("mor", None, meaning_id=added.meaning.id if added.meaning else None)

    payload = verification_service.calls[-1]
    assert payload.stored_lemma == "mor"
    assert payload.canonical_lemma == "moder"


def test_general_save_verification_does_not_surface_fix_variations(tmp_path: Path) -> None:
    class VariationOnlyVerificationService:
        provider = "gemini"
        reviewer_role = "Professional Danish Language Expert"

        def verify_word_entry(self, _payload):
            class Result:
                verdict = "flagged"
                message = "Review needed"
                problem = "Plural forms are missing."
                change_to_implement = "Add the missing plural forms."
                suggested_actions = (
                    WordVerificationAction(
                        action_type="fix_variations",
                        reason="Complete the paradigm.",
                        plural_indefinite_forms=("bøger",),
                        plural_definite_forms=("bøgerne",),
                    ),
                )

            return Result()

    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"bog": "book", "bogen": "the book"}),
        verification_service=VariationOnlyVerificationService(),
    )

    added = use_case.add_word("Bogen", "bog")
    verified = use_case.verify_added_word("bog", "bogen", meaning_id=added.meaning.id if added.meaning else None)

    assert verified.verification.status == "verified"
    assert verified.verification.suggested_actions == []


def test_complete_variations_review_requires_structured_fix_variations_action(tmp_path: Path) -> None:
    class FlaggedCompletionVerificationService:
        provider = "gemini"
        reviewer_role = "Professional Danish Language Expert"

        def verify_word_entry(self, _payload):
            class Result:
                verdict = "flagged"
                message = "Review needed."
                problem = "Plural forms are wrong."
                change_to_implement = (
                    "The plural indefinite form should be 'mødre' instead of 'morer'. "
                    "The plural definite form should be 'mødrene' instead of 'morerne'."
                )
                suggested_actions = ()

            return Result()

    canonical_lemma = _cor_local_entry(
        cor_id="COR.MODER.LEM",
        lemma="moder",
        gloss="person",
        form="moder",
        lemma_idx=61046,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    inflected_surface = _cor_local_entry(
        cor_id="COR.MODER.SURF",
        lemma="moder",
        gloss="person",
        form="mor",
        lemma_idx=61046,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"mor": [inflected_surface]},
            by_lemma_idx={61046: [canonical_lemma, inflected_surface]},
        ),
        verification_service=FlaggedCompletionVerificationService(),
    )

    added = use_case.add_word(
        "mor",
        "mor",
        search_seed={
            "lemma": "mor",
            "surface": "mor",
            "cor_id": "COR.MODER.SURF",
            "cor_lemma_idx": 61046,
            "meaning_key": "person",
            "gloss": "person",
            "english_translation": "mother",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )

    verified = use_case.verify_added_word(
        "mor",
        None,
        meaning_id=added.meaning.id if added.meaning else None,
        review_intent="complete_variations",
    )

    assert verified.verification.status == "flagged"
    assert verified.verification.suggested_actions == []


def test_complete_variations_review_requires_structured_adjective_fix_variations_action(tmp_path: Path) -> None:
    class FlaggedCompletionVerificationService:
        provider = "gemini"
        reviewer_role = "Professional Danish Language Expert"

        def verify_word_entry(self, _payload):
            class Result:
                verdict = "flagged"
                message = "Review needed."
                problem = "The adjective agreement set is incomplete."
                change_to_implement = (
                    "The singular indefinite n-word form should be 'stor'. "
                    "The singular indefinite t-word form should be 'stort'. "
                    "The singular definite form should be 'store'."
                )
                suggested_actions = ()

            return Result()

    stor_n = _cor_local_entry(
        cor_id="COR.STOR.N",
        lemma="stor",
        gloss="large",
        form="stor",
        lemma_idx=220,
        pos_tag="ADJ",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="adj.sg.ubest.fk",
    )
    stor_t = _cor_local_entry(
        cor_id="COR.STOR.T",
        lemma="stor",
        gloss="large",
        form="stort",
        lemma_idx=220,
        pos_tag="ADJ",
        morphology="Gender=Neut|Number=Sing|Definite=Ind",
        gram_raw="adj.sg.ubest.itk",
    )
    stor_def = _cor_local_entry(
        cor_id="COR.STOR.DEF",
        lemma="stor",
        gloss="large",
        form="store",
        lemma_idx=220,
        pos_tag="ADJ",
        morphology="Number=Sing|Definite=Def",
        gram_raw="adj.sg.best",
    )
    stor_pl = _cor_local_entry(
        cor_id="COR.STOR.PL",
        lemma="stor",
        gloss="large",
        form="store",
        lemma_idx=220,
        pos_tag="ADJ",
        morphology="Number=Plur",
        gram_raw="adj.pl",
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"stor": [stor_n], "stort": [stor_t], "store": [stor_def, stor_pl]},
            by_lemma_idx={220: [stor_n, stor_t, stor_def, stor_pl]},
        ),
        verification_service=FlaggedCompletionVerificationService(),
    )

    added = use_case.add_word(
        "stort",
        "stor",
        search_seed={
            "lemma": "stor",
            "surface": "stort",
            "cor_id": "COR.STOR.T",
            "cor_lemma_idx": 220,
            "meaning_key": "large",
            "gloss": "large",
            "english_translation": "large",
            "pos_tag": "ADJ",
            "morphology": "Gender=Neut|Number=Sing|Definite=Ind",
        },
    )

    verified = use_case.verify_added_word(
        "stor",
        None,
        meaning_id=added.meaning.id if added.meaning else None,
        review_intent="complete_variations",
    )

    assert verified.verification.status == "flagged"
    assert verified.verification.suggested_actions == []


def test_complete_variations_review_requires_structured_verb_fix_variations_action(tmp_path: Path) -> None:
    class FlaggedCompletionVerificationService:
        provider = "gemini"
        reviewer_role = "Professional Danish Language Expert"

        def verify_word_entry(self, _payload):
            class Result:
                verdict = "flagged"
                message = "Review needed."
                problem = "The completed verb set is missing the imperative and past participle."
                change_to_implement = (
                    "The infinitive form should be 'lære'. "
                    "The present form should be 'lærer'. "
                    "The past form should be 'lærte'. "
                    "The imperative form should be 'lær'. "
                    "The past participle form should be 'lært'."
                )
                suggested_actions = ()

            return Result()

    laere_inf = _cor_local_entry(
        cor_id="COR.LAERE.INF",
        lemma="lære",
        gloss="learn",
        form="lære",
        lemma_idx=30686,
        pos_tag="VERB",
        morphology="VerbForm=Inf|Voice=Act",
        gram_raw="vb.inf.akt",
    )
    laere_pres = _cor_local_entry(
        cor_id="COR.LAERE.PRES",
        lemma="lære",
        gloss="learn",
        form="lærer",
        lemma_idx=30686,
        pos_tag="VERB",
        morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
        gram_raw="vb.præs.akt",
    )
    laere_past = _cor_local_entry(
        cor_id="COR.LAERE.PAST",
        lemma="lære",
        gloss="learn",
        form="lærte",
        lemma_idx=30686,
        pos_tag="VERB",
        morphology="Tense=Past|VerbForm=Fin|Voice=Act",
        gram_raw="vb.præt.akt",
    )
    laere_imp = _cor_local_entry(
        cor_id="COR.LAERE.IMP",
        lemma="lære",
        gloss="learn",
        form="lær",
        lemma_idx=30686,
        pos_tag="VERB",
        morphology="Mood=Imp|VerbForm=Fin",
        gram_raw="vb.imp",
    )
    laere_part = _cor_local_entry(
        cor_id="COR.LAERE.PART",
        lemma="lære",
        gloss="learn",
        form="lært",
        lemma_idx=30686,
        pos_tag="VERB",
        morphology="VerbForm=Part|Voice=Act",
        gram_raw="vb.perf.part",
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={
                "lære": [laere_inf],
                "lærer": [laere_pres],
                "lærte": [laere_past],
                "lær": [laere_imp],
                "lært": [laere_part],
            },
            by_lemma_idx={30686: [laere_inf, laere_pres, laere_past, laere_imp, laere_part]},
        ),
        verification_service=FlaggedCompletionVerificationService(),
    )

    added = use_case.add_word(
        "lærer",
        "lære",
        search_seed={
            "lemma": "lære",
            "surface": "lærer",
            "cor_id": "COR.LAERE.PRES",
            "cor_lemma_idx": 30686,
            "meaning_key": "learn",
            "gloss": "learn",
            "english_translation": "learn",
            "pos_tag": "VERB",
            "morphology": "Tense=Pres|VerbForm=Fin|Voice=Act",
        },
    )

    verified = use_case.verify_added_word(
        "lære",
        None,
        meaning_id=added.meaning.id if added.meaning else None,
        review_intent="complete_variations",
    )

    assert verified.verification.status == "flagged"
    assert verified.verification.suggested_actions == []


def test_complete_variations_review_discards_move_to_lemma_actions(tmp_path: Path) -> None:
    class FlaggedCompletionVerificationService:
        provider = "gemini"
        reviewer_role = "Professional Danish Language Expert"

        def verify_word_entry(self, _payload):
            class Result:
                verdict = "flagged"
                message = "Review needed."
                problem = "Plural forms are wrong."
                change_to_implement = "Replace the plural forms with the reviewed noun variations."
                suggested_actions = (
                    WordVerificationAction(
                        action_type="move_to_lemma",
                        target_lemma="moder",
                        target_meaning_key="person",
                        reason="Ignored for completion review.",
                    ),
                )

            return Result()

    use_case = WordbankUseCase(
        _db_path(tmp_path),
        verification_service=FlaggedCompletionVerificationService(),
    )

    added = use_case.add_word("mor", "mor")
    verified = use_case.verify_added_word(
        "mor",
        None,
        meaning_id=added.meaning.id if added.meaning else None,
        review_intent="complete_variations",
    )

    assert verified.verification.status == "flagged"
    assert verified.verification.suggested_actions == []


def test_wordbank_use_case_applies_fix_variations_action_for_completion_review(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    canonical_lemma = _cor_local_entry(
        cor_id="COR.MODER.LEM",
        lemma="moder",
        gloss="person",
        form="moder",
        lemma_idx=61046,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    inflected_surface = _cor_local_entry(
        cor_id="COR.MODER.SURF",
        lemma="moder",
        gloss="person",
        form="mor",
        lemma_idx=61046,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    singular_definite = _cor_local_entry(
        cor_id="COR.MODER.DEF",
        lemma="moder",
        gloss="person",
        form="moren",
        lemma_idx=61046,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Def",
        gram_raw="sb.fk.sg.best",
    )
    plural_indefinite = _cor_local_entry(
        cor_id="COR.MODER.PL",
        lemma="moder",
        gloss="person",
        form="mødre",
        lemma_idx=61046,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Plur|Definite=Ind",
        gram_raw="sb.fk.pl.ubest",
    )
    plural_definite = _cor_local_entry(
        cor_id="COR.MODER.PLDEF",
        lemma="moder",
        gloss="person",
        form="mødrene",
        lemma_idx=61046,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Plur|Definite=Def",
        gram_raw="sb.fk.pl.best",
    )
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"mor": [inflected_surface]},
            by_lemma_idx={61046: [canonical_lemma, inflected_surface, singular_definite, plural_indefinite, plural_definite]},
        ),
    )

    added = use_case.add_word(
        "mor",
        "mor",
        search_seed={
            "lemma": "mor",
            "surface": "mor",
            "cor_id": "COR.MODER.SURF",
            "cor_lemma_idx": 61046,
            "meaning_key": "person",
            "gloss": "person",
            "english_translation": "mother",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )
    assert added.meaning is not None

    with get_connection(db_path) as conn:
        lexeme = conn.execute("SELECT id FROM lexemes WHERE lemma = ?", ("mor",)).fetchone()
        assert lexeme is not None
        conn.execute(
            """
            INSERT INTO surface_forms (lexeme_id, meaning_id, form, source, pos_tag, morphology)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(lexeme["id"]),
                added.meaning.id,
                "morer",
                "search",
                "NOUN",
                "Gender=Com|Number=Plur|Definite=Ind",
            ),
        )
        conn.execute(
            """
            INSERT INTO surface_forms (lexeme_id, meaning_id, form, source, pos_tag, morphology)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(lexeme["id"]),
                added.meaning.id,
                "morerne",
                "search",
                "NOUN",
                "Gender=Com|Number=Plur|Definite=Def",
            ),
        )

    response = use_case.apply_verification_changes(
        stored_lemma="mor",
        stored_surface_form=None,
        meaning_id=added.meaning.id,
        action={
            "action_type": "fix_variations",
            "singular_indefinite_forms": ["mor", "moder"],
            "singular_definite_forms": ["moren"],
            "plural_indefinite_forms": ["mødre"],
            "plural_definite_forms": ["mødrene"],
        },
        provider="gemini",
    )

    assert response.status == "applied"
    assert response.applied_action_type == "fix_variations"
    details = use_case.get_lemma_details("mor")
    assert sorted(form.form for form in details.meaning_sections[0].surface_forms) == [
        "moder",
        "moren",
        "mødre",
        "mødrene",
    ]


def test_wordbank_use_case_applies_fix_variations_action_for_adjective_completion_review(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    stor_n = _cor_local_entry(
        cor_id="COR.STOR.N",
        lemma="stor",
        gloss="large",
        form="stor",
        lemma_idx=220,
        pos_tag="ADJ",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="adj.sg.ubest.fk",
    )
    stor_t = _cor_local_entry(
        cor_id="COR.STOR.T",
        lemma="stor",
        gloss="large",
        form="stort",
        lemma_idx=220,
        pos_tag="ADJ",
        morphology="Gender=Neut|Number=Sing|Definite=Ind",
        gram_raw="adj.sg.ubest.itk",
    )
    stor_def = _cor_local_entry(
        cor_id="COR.STOR.DEF",
        lemma="stor",
        gloss="large",
        form="store",
        lemma_idx=220,
        pos_tag="ADJ",
        morphology="Number=Sing|Definite=Def",
        gram_raw="adj.sg.best",
    )
    stor_pl = _cor_local_entry(
        cor_id="COR.STOR.PL",
        lemma="stor",
        gloss="large",
        form="store",
        lemma_idx=220,
        pos_tag="ADJ",
        morphology="Number=Plur",
        gram_raw="adj.pl",
    )
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"stor": [stor_n], "stort": [stor_t], "store": [stor_def, stor_pl]},
            by_lemma_idx={220: [stor_n, stor_t, stor_def, stor_pl]},
        ),
    )

    added = use_case.add_word(
        "stort",
        "stor",
        search_seed={
            "lemma": "stor",
            "surface": "stort",
            "cor_id": "COR.STOR.T",
            "cor_lemma_idx": 220,
            "meaning_key": "large",
            "gloss": "large",
            "english_translation": "large",
            "pos_tag": "ADJ",
            "morphology": "Gender=Neut|Number=Sing|Definite=Ind",
        },
    )
    assert added.meaning is not None

    with get_connection(db_path) as conn:
        lexeme = conn.execute("SELECT id FROM lexemes WHERE lemma = ?", ("stor",)).fetchone()
        assert lexeme is not None
        conn.execute(
            """
            INSERT INTO surface_forms (lexeme_id, meaning_id, form, source, pos_tag, morphology)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(lexeme["id"]),
                added.meaning.id,
                "storre",
                "search",
                "ADJ",
                "Number=Sing|Definite=Def",
            ),
        )
    response = use_case.apply_verification_changes(
        stored_lemma="stor",
        stored_surface_form=None,
        meaning_id=added.meaning.id,
        action={
            "action_type": "fix_variations",
            "singular_indefinite_n_word_forms": ["stor"],
            "singular_indefinite_t_word_forms": ["stort"],
            "singular_definite_forms": ["store"],
            "plural_indefinite_forms": ["store"],
            "plural_definite_forms": ["store"],
        },
        provider="gemini",
    )

    assert response.status == "applied"
    details = use_case.get_lemma_details("stor")
    assert sorted(form.form for form in details.meaning_sections[0].surface_forms) == ["store", "stort"]


def test_wordbank_use_case_applies_fix_variations_action_for_verb_completion_review(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    komme_inf = _cor_local_entry(
        cor_id="COR.KOMME.INF",
        lemma="komme",
        gloss="come",
        form="komme",
        lemma_idx=30031,
        pos_tag="VERB",
        morphology="VerbForm=Inf|Voice=Act",
        gram_raw="vb.inf.akt",
    )
    komme_pres = _cor_local_entry(
        cor_id="COR.KOMME.PRES",
        lemma="komme",
        gloss="come",
        form="kommer",
        lemma_idx=30031,
        pos_tag="VERB",
        morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
        gram_raw="vb.præs.akt",
    )
    komme_past = _cor_local_entry(
        cor_id="COR.KOMME.PAST",
        lemma="komme",
        gloss="come",
        form="kom",
        lemma_idx=30031,
        pos_tag="VERB",
        morphology="Tense=Past|VerbForm=Fin|Voice=Act",
        gram_raw="vb.præt.akt",
    )
    komme_imp = _cor_local_entry(
        cor_id="COR.KOMME.IMP",
        lemma="komme",
        gloss="come",
        form="kom",
        lemma_idx=30031,
        pos_tag="VERB",
        morphology="Mood=Imp|VerbForm=Fin",
        gram_raw="vb.imp",
    )
    komme_part = _cor_local_entry(
        cor_id="COR.KOMME.PART",
        lemma="komme",
        gloss="come",
        form="kommet",
        lemma_idx=30031,
        pos_tag="VERB",
        morphology="VerbForm=Part|Voice=Act",
        gram_raw="vb.perf.part",
    )
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={
                "komme": [komme_inf],
                "kommer": [komme_pres],
                "kom": [komme_past, komme_imp],
                "kommet": [komme_part],
            },
            by_lemma_idx={30031: [komme_inf, komme_pres, komme_past, komme_imp, komme_part]},
        ),
    )

    added = use_case.add_word(
        "kommer",
        "komme",
        search_seed={
            "lemma": "komme",
            "surface": "kommer",
            "cor_id": "COR.KOMME.PRES",
            "cor_lemma_idx": 30031,
            "meaning_key": "come",
            "gloss": "come",
            "english_translation": "come",
            "pos_tag": "VERB",
            "morphology": "Tense=Pres|VerbForm=Fin|Voice=Act",
        },
    )
    assert added.meaning is not None

    with get_connection(db_path) as conn:
        lexeme = conn.execute("SELECT id FROM lexemes WHERE lemma = ?", ("komme",)).fetchone()
        assert lexeme is not None
        conn.execute(
            """
            INSERT INTO surface_forms (lexeme_id, meaning_id, form, source, pos_tag, morphology)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(lexeme["id"]),
                added.meaning.id,
                "kommede",
                "search",
                "VERB",
                "Tense=Past|VerbForm=Fin|Voice=Act",
            ),
        )

    response = use_case.apply_verification_changes(
        stored_lemma="komme",
        stored_surface_form=None,
        meaning_id=added.meaning.id,
        action={
            "action_type": "fix_variations",
            "infinitive_forms": ["komme"],
            "present_forms": ["kommer"],
            "past_forms": ["kom"],
            "imperative_forms": ["kom"],
            "past_participle_forms": ["kommet"],
        },
        provider="gemini",
    )

    assert response.status == "applied"
    details = use_case.get_lemma_details("komme")
    assert sorted(form.form for form in details.meaning_sections[0].surface_forms) == ["kom", "kommer", "kommet"]


def test_wordbank_use_case_applies_fix_variations_with_singular_indefinite_aliases(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    fader_lemma = _cor_local_entry(
        cor_id="COR.FADER.LEM",
        lemma="fader",
        gloss="father",
        form="fader",
        lemma_idx=410,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    far_alias = _cor_local_entry(
        cor_id="COR.FADER.IRREG",
        lemma="fader",
        gloss="father",
        form="far",
        lemma_idx=410,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    faderen = _cor_local_entry(
        cor_id="COR.FADER.DEF",
        lemma="fader",
        gloss="father",
        form="faderen",
        lemma_idx=410,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Def",
        gram_raw="sb.fk.sg.best",
    )
    faedre = _cor_local_entry(
        cor_id="COR.FADER.PL",
        lemma="fader",
        gloss="father",
        form="fædre",
        lemma_idx=410,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Plur|Definite=Ind",
        gram_raw="sb.fk.pl.ubest",
    )
    faedrene = _cor_local_entry(
        cor_id="COR.FADER.PLDEF",
        lemma="fader",
        gloss="father",
        form="fædrene",
        lemma_idx=410,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Plur|Definite=Def",
        gram_raw="sb.fk.pl.best",
    )
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"fader": [fader_lemma], "far": [far_alias]},
            by_lemma_idx={410: [fader_lemma, far_alias, faderen, faedre, faedrene]},
        ),
    )

    added = use_case.add_word(
        "fader",
        "fader",
        search_seed={
            "lemma": "fader",
            "surface": "fader",
            "cor_id": "COR.FADER.LEM",
            "cor_lemma_idx": 410,
            "meaning_key": "father",
            "gloss": "father",
            "english_translation": "father",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )
    assert added.meaning is not None

    with get_connection(db_path) as conn:
        lexeme = conn.execute("SELECT id FROM lexemes WHERE lemma = ?", ("fader",)).fetchone()
        assert lexeme is not None
        for form, morphology in [
            ("fadermand", "Gender=Com|Number=Sing|Definite=Ind"),
            ("faderen", "Gender=Com|Number=Sing|Definite=Def"),
            ("fædre", "Gender=Com|Number=Plur|Definite=Ind"),
            ("fædrene", "Gender=Com|Number=Plur|Definite=Def"),
        ]:
            conn.execute(
                """
                INSERT INTO surface_forms (lexeme_id, meaning_id, form, source, pos_tag, morphology)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    int(lexeme["id"]),
                    added.meaning.id,
                    form,
                    "search",
                    "NOUN",
                    morphology,
                ),
            )

    response = use_case.apply_verification_changes(
        stored_lemma="fader",
        stored_surface_form=None,
        meaning_id=added.meaning.id,
        action={
            "action_type": "fix_variations",
            "singular_indefinite_forms": ["far"],
            "singular_definite_forms": ["faderen"],
            "plural_indefinite_forms": ["fædre"],
            "plural_definite_forms": ["fædrene"],
        },
        provider="gemini",
    )

    assert response.status == "applied"
    details = use_case.get_lemma_details("fader")
    assert [form.form for form in details.meaning_sections[0].surface_forms] == ["far", "faderen", "fædre", "fædrene"]


def test_wordbank_use_case_rejects_fix_variations_apply_without_structured_slots(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)

    class FlaggedCompletionVerificationService:
        provider = "gemini"
        reviewer_role = "Professional Danish Language Expert"

        def verify_word_entry(self, _payload):
            class Result:
                verdict = "flagged"
                message = "Review needed."
                problem = "The plural surface forms provided for the noun 'mor' are incorrect."
                change_to_implement = (
                    "The plural indefinite form should be 'mødre' instead of 'morer'. "
                    "The plural definite form should be 'mødrene' instead of 'morerne'."
                )
                suggested_actions = ()

            return Result()

    saved_lemma = _cor_local_entry(
        cor_id="COR.MOR.PERSON.LEM",
        lemma="mor",
        gloss="person",
        form="mor",
        lemma_idx=47530,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    saved_singular_definite = _cor_local_entry(
        cor_id="COR.MOR.PERSON.DEF",
        lemma="mor",
        gloss="person",
        form="moren",
        lemma_idx=47530,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Def",
        gram_raw="sb.fk.sg.best",
    )
    saved_plural_indefinite = _cor_local_entry(
        cor_id="COR.MOR.PERSON.PL",
        lemma="mor",
        gloss="person",
        form="morer",
        lemma_idx=47530,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Plur|Definite=Ind",
        gram_raw="sb.fk.pl.ubest",
    )
    saved_plural_definite = _cor_local_entry(
        cor_id="COR.MOR.PERSON.PLDEF",
        lemma="mor",
        gloss="person",
        form="morerne",
        lemma_idx=47530,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Plur|Definite=Def",
        gram_raw="sb.fk.pl.best",
    )
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"mor": [saved_lemma]},
            by_lemma_idx={
                47530: [saved_lemma, saved_singular_definite, saved_plural_indefinite, saved_plural_definite],
            },
        ),
        verification_service=FlaggedCompletionVerificationService(),
    )

    added = use_case.add_word(
        "mor",
        "mor",
        search_seed={
            "lemma": "mor",
            "surface": "mor",
            "cor_id": "COR.MOR.PERSON.LEM",
            "cor_lemma_idx": 47530,
            "meaning_key": "person",
            "gloss": "person",
            "english_translation": "mother",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )
    assert added.meaning is not None

    with get_connection(db_path) as conn:
        lexeme = conn.execute("SELECT id FROM lexemes WHERE lemma = ?", ("mor",)).fetchone()
        assert lexeme is not None
        conn.execute(
            """
            INSERT INTO surface_forms (lexeme_id, meaning_id, form, source, pos_tag, morphology)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(lexeme["id"]),
                added.meaning.id,
                "moren",
                "search",
                "NOUN",
                "Gender=Com|Number=Sing|Definite=Def",
            ),
        )
        conn.execute(
            """
            INSERT INTO surface_forms (lexeme_id, meaning_id, form, source, pos_tag, morphology)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(lexeme["id"]),
                added.meaning.id,
                "morer",
                "search",
                "NOUN",
                "Gender=Com|Number=Plur|Definite=Ind",
            ),
        )
        conn.execute(
            """
            INSERT INTO surface_forms (lexeme_id, meaning_id, form, source, pos_tag, morphology)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(lexeme["id"]),
                added.meaning.id,
                "morerne",
                "search",
                "NOUN",
                "Gender=Com|Number=Plur|Definite=Def",
            ),
        )

    verified = use_case.verify_added_word(
        "mor",
        None,
        meaning_id=added.meaning.id,
        review_intent="complete_variations",
    )

    assert verified.verification.status == "flagged"
    assert verified.verification.suggested_actions == []
    with pytest.raises(ValueError, match="structured slot forms"):
        use_case.apply_verification_changes(
            stored_lemma="mor",
            stored_surface_form=None,
            meaning_id=added.meaning.id,
            action={"action_type": "fix_variations"},
            provider="gemini",
        )


def test_complete_variations_apply_rejects_non_fix_variations_actions(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(db_path)
    added = use_case.add_word("mor", "mor")
    assert added.meaning is not None

    verified = use_case.verify_added_word(
        "mor",
        None,
        meaning_id=added.meaning.id,
        review_intent="complete_variations",
    )
    assert verified.verification.review_intent == "complete_variations"

    with pytest.raises(ValueError, match="Only fix_variations can be applied"):
        use_case.apply_verification_changes(
            stored_lemma="mor",
            stored_surface_form=None,
            meaning_id=added.meaning.id,
            action={
                "action_type": "move_to_lemma",
                "target_lemma": "moder",
                "target_meaning_key": "person",
            },
            provider="gemini",
        )


def test_wordbank_use_case_stores_and_returns_surface_pronunciation(tmp_path: Path) -> None:
    tts_service = FakeTTSService({"bogen": b"fake-wav-bytes"})
    use_case = WordbankUseCase(_db_path(tmp_path), tts_service=tts_service)

    use_case.add_word("Bogen", "bog")
    pronunciation = use_case.get_pronunciation_audio("bogen")

    assert pronunciation.mime_type == "audio/wav"
    assert pronunciation.audio_bytes == b"fake-wav-bytes"
    assert tts_service.calls == ["bogen"]

def test_wordbank_use_case_generates_pronunciation_on_demand_for_existing_form(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    with get_connection(db_path) as conn:
        conn.execute("INSERT INTO lexemes (lemma, source) VALUES (?, ?)", ("bog", "manual"))
        lexeme_row = conn.execute("SELECT id FROM lexemes WHERE lemma = ?", ("bog",)).fetchone()
        assert lexeme_row is not None
        conn.execute(
            "INSERT INTO surface_forms (lexeme_id, form, source) VALUES (?, ?, ?)",
            (int(lexeme_row["id"]), "bogen", "manual"),
        )

    tts_service = FakeTTSService({"bogen": b"lazy-wav-bytes"})
    use_case = WordbankUseCase(db_path, tts_service=tts_service)

    pronunciation = use_case.get_pronunciation_audio("bogen")

    assert pronunciation.mime_type == "audio/wav"
    assert pronunciation.audio_bytes == b"lazy-wav-bytes"
    assert tts_service.calls == ["bogen"]

def test_wordbank_use_case_generates_distinct_lemma_and_surface_pronunciation(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(db_path)
    use_case.add_word("Bogen", "bog")

    tts_service = FakeTTSService({"bog": b"lemma-wav", "bogen": b"surface-wav"})
    use_case = WordbankUseCase(db_path, tts_service=tts_service)

    generated = use_case.generate_pronunciation_for_added_word("bog", "bogen")
    lemma_audio = use_case.get_pronunciation_audio("bog")
    surface_audio = use_case.get_pronunciation_audio("bogen")

    assert generated.status == "generated"
    assert generated.pronunciation_form == "bogen"
    assert lemma_audio.audio_bytes == b"lemma-wav"
    assert surface_audio.audio_bytes == b"surface-wav"
    assert tts_service.calls == ["bog", "bogen"]


def test_wordbank_use_case_exposes_generated_lemma_audio_in_sectioned_details(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(db_path)
    use_case.add_word("Bogen", "bog")

    tts_service = FakeTTSService({"bog": b"lemma-wav", "bogen": b"surface-wav"})
    use_case = WordbankUseCase(db_path, tts_service=tts_service)

    use_case.generate_pronunciation_for_added_word("bog", "bogen")
    details = use_case.get_lemma_details("bog")

    assert [item.form for item in details.surface_forms] == ["bog"]
    assert details.surface_forms[0].has_pronunciation is True
    assert [item.form for item in details.meaning_sections[0].surface_forms] == ["bogen"]
    assert all(item.has_pronunciation for item in details.meaning_sections[0].surface_forms)


def test_wordbank_use_case_force_regenerates_pronunciation(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(db_path)
    use_case.add_word("Bogen", "bog")

    class RotatingTTSService:
        provider = "gemini_tts"
        model = "gemini-2.5-flash-preview-tts"

        def __init__(self) -> None:
            self.calls: list[str] = []
            self._counter = 0

        def synthesize(self, text: str) -> PronunciationAudio | None:
            self.calls.append(text)
            self._counter += 1
            return PronunciationAudio(
                audio_bytes=f"wav-{self._counter}".encode(),
                mime_type="audio/wav",
            )

    tts_service = RotatingTTSService()
    use_case = WordbankUseCase(db_path, tts_service=tts_service)

    first = use_case.generate_pronunciation_for_added_word("bog", "bogen")
    second = use_case.generate_pronunciation_for_added_word("bog", "bogen", force=True)
    audio = use_case.get_pronunciation_audio("bogen")

    assert first.status == "generated"
    assert second.status == "generated"
    assert audio.audio_bytes == b"wav-4"
    assert tts_service.calls == ["bog", "bogen", "bog", "bogen"]

def test_wordbank_use_case_normalizes_l16_pronunciation_to_wav(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(db_path)
    use_case.add_word("Bogen", "bog")

    class L16TTSService:
        provider = "gemini_tts"
        model = "gemini-2.5-flash-preview-tts"

        def synthesize(self, text: str) -> PronunciationAudio | None:
            if text != "bogen":
                return None
            return PronunciationAudio(
                audio_bytes=(b"\x00\x00" * 2400),
                mime_type="audio/l16;codec=pcm;rate=24000",
            )

    use_case = WordbankUseCase(db_path, tts_service=L16TTSService())
    generated = use_case.generate_pronunciation_for_added_word("bog", "bogen", force=True)
    audio = use_case.get_pronunciation_audio("bogen")

    assert generated.status == "generated"
    assert audio.mime_type == "audio/wav"
    assert audio.audio_bytes[:4] == b"RIFF"

def test_wordbank_use_case_applies_translation_verification_action(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(db_path)
    added = use_case.add_word("Bogen", "bog")

    response = use_case.apply_verification_changes(
        stored_lemma="bog",
        stored_surface_form=None,
        meaning_id=added.meaning.id if added.meaning else None,
        action={
            "action_type": "fix_translation",
            "english_translation": "book",
        },
        provider="gemini",
    )

    assert response.status == "applied"
    assert response.applied_action_type == "fix_translation"
    assert response.target_lemma == "bog"
    assert response.target_meaning_id == added.meaning.id

    with get_connection(db_path) as conn:
        meaning_row = conn.execute(
            """
            SELECT english_translation
            FROM lexeme_meanings
            WHERE id = ?
            """,
            (added.meaning.id,),
        ).fetchone()

    assert meaning_row is not None
    assert meaning_row["english_translation"] == "book"


def test_wordbank_use_case_rejects_surface_scoped_translation_verification_action(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(db_path)
    added = use_case.add_word("Bogen", "bog")

    with pytest.raises(ValueError, match="surface-form verification targets"):
        use_case.apply_verification_changes(
            stored_lemma="bog",
            stored_surface_form="bogen",
            meaning_id=added.meaning.id if added.meaning else None,
            action={
                "action_type": "fix_translation",
                "english_translation": "book",
            },
            provider="gemini",
        )


def test_wordbank_use_case_skips_deprecated_gloss_verification_action(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(db_path)
    added = use_case.add_word("Bogen", "bog")

    response = use_case.apply_verification_changes(
        stored_lemma="bog",
        stored_surface_form="bogen",
        meaning_id=added.meaning.id if added.meaning else None,
        action={
            "action_type": "fix_gloss",
            "gloss": "reading material",
        },
        provider="gemini",
    )

    assert response.status == "skipped"
    assert response.applied_action_type is None
    with get_connection(db_path) as conn:
        meaning_row = conn.execute(
            "SELECT gloss FROM lexeme_meanings WHERE id = ?",
            (added.meaning.id,),
        ).fetchone()
    assert meaning_row is not None
    assert meaning_row["gloss"] is None


def test_wordbank_use_case_moves_surface_to_another_meaning_section(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=_bog_homograph_cor_local(),
        translation_service=FakeTranslationService({"bog": "book", "bogen": "book", "moser": "swamp"}),
    )
    first = use_case.add_word("Bogen", "bog", cor_id="COR.BOG.BOOK.DEF")
    second = use_case.add_word("Moser", "bog", cor_id="COR.BOG.SWAMP.PL")

    response = use_case.apply_verification_changes(
        stored_lemma="bog",
        stored_surface_form="bogen",
        meaning_id=first.meaning.id if first.meaning else None,
        action={
            "action_type": "move_to_meaning_section",
            "target_meaning_id": second.meaning.id if second.meaning else None,
        },
        provider="gemini",
    )

    assert response.status == "applied"
    assert response.applied_action_type == "move_to_meaning_section"
    assert response.target_meaning_id == second.meaning.id
    details = use_case.get_lemma_details("bog")
    by_key = {section.meaning_key: section for section in details.meaning_sections}
    assert by_key["book"].surface_forms == []
    assert [item.form for item in by_key["swamp"].surface_forms] == ["bogen", "moser"]


def test_wordbank_use_case_marks_moved_surface_as_verified_after_apply(tmp_path: Path) -> None:
    class FlaggedMoveVerificationService:
        provider = "gemini"
        reviewer_role = "Professional Danish Language Expert"

        def verify_word_entry(self, _payload):
            class Result:
                verdict = "flagged"
                message = "Review needed."
                problem = "This form belongs in another meaning section."
                change_to_implement = "Move the form to the swamp meaning."
                suggested_actions = (
                    WordVerificationAction(
                        action_type="move_to_meaning_section",
                        target_meaning_id=2,
                        reason="The saved form matches the swamp meaning.",
                    ),
                )

            return Result()

    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=_bog_homograph_cor_local(),
        translation_service=FakeTranslationService({"bog": "book", "bogen": "book", "moser": "swamp"}),
        verification_service=FlaggedMoveVerificationService(),
    )
    first = use_case.add_word("Bogen", "bog", cor_id="COR.BOG.BOOK.DEF")
    second = use_case.add_word("Moser", "bog", cor_id="COR.BOG.SWAMP.PL")

    verified = use_case.verify_added_word("bog", "bogen", meaning_id=first.meaning.id if first.meaning else None)
    assert verified.verification.status == "flagged"

    response = use_case.apply_verification_changes(
        stored_lemma="bog",
        stored_surface_form="bogen",
        meaning_id=first.meaning.id if first.meaning else None,
        action={
            "action_type": "move_to_meaning_section",
            "target_meaning_id": second.meaning.id if second.meaning else None,
        },
        provider="gemini",
    )

    assert response.status == "applied"
    details = use_case.get_lemma_details("bog")
    swamp_section = next(section for section in details.meaning_sections if section.id == second.meaning.id)
    moved_surface = next(item for item in swamp_section.surface_forms if item.form == "bogen")
    assert moved_surface.verification is not None
    assert moved_surface.verification.status == "verified"
    assert moved_surface.verification.suggested_actions == []


def test_wordbank_use_case_moves_meaning_section_to_new_lemma(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=_bog_homograph_cor_local(),
        translation_service=FakeTranslationService({"bog": "book", "bogen": "book"}),
    )
    added = use_case.add_word("Bogen", "bog", cor_id="COR.BOG.BOOK.DEF")

    response = use_case.apply_verification_changes(
        stored_lemma="bog",
        stored_surface_form="bogen",
        meaning_id=added.meaning.id if added.meaning else None,
        action={
            "action_type": "move_to_lemma",
            "target_lemma": "bind",
            "target_meaning_key": "book",
            "target_gloss": "book",
            "target_english_translation": "book",
            "target_pos_tag": "NOUN",
            "target_morphology": "Gender=Com|Number=Sing",
        },
        provider="gemini",
    )

    assert response.status == "applied"
    assert response.applied_action_type == "move_to_lemma"
    assert response.target_lemma == "bind"
    moved_details = use_case.get_lemma_details("bind")
    assert [section.meaning_key for section in moved_details.meaning_sections] == ["book"]
    assert [item.form for item in moved_details.meaning_sections[0].surface_forms] == ["bogen"]
    with get_connection(db_path) as conn:
        source_lexeme = conn.execute("SELECT id FROM lexemes WHERE lemma = ?", ("bog",)).fetchone()
    assert source_lexeme is None


def test_wordbank_use_case_logs_gemini_applied_changes(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(db_path)
    added = use_case.add_word("Bogen", "bog")
    log_path = tmp_path / "gemini-applied-changes.jsonl"

    use_case = WordbankUseCase(db_path, gemini_changes_log_path=log_path)
    response = use_case.apply_verification_changes(
        stored_lemma="bog",
        stored_surface_form=None,
        meaning_id=added.meaning.id if added.meaning else None,
        action={
            "action_type": "fix_translation",
            "english_translation": "Book",
        },
        provider="gemini",
    )

    assert response.status == "applied"
    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["provider"] == "gemini"
    assert payload["stored_lemma"] == "bog"
    assert payload["stored_surface_form"] is None
    assert payload["action"]["english_translation"] == "Book"
    assert payload["action_type"] == "fix_translation"
    assert "timestamp_utc" in payload


def test_permanently_failed_verify_word_job_sets_verification_status_to_error(tmp_path: Path) -> None:
    """When a verify_word background job exhausts all retries, the verification record must be 'error'."""
    import time
    from app.db.migrations import get_connection
    from app.services.use_cases.wordbank.background_jobs import WordbankBackgroundJobRunner

    db_path = _db_path(tmp_path)

    class AlwaysFailingVerification:
        provider = "gemini"
        reviewer_role = "Professional Danish Language Expert"

        def verify_word_entry(self, payload):
            raise RuntimeError("Simulated permanent Gemini failure")

        def classify_word_categories(self, payload):
            raise RuntimeError("Simulated permanent Gemini failure")

    # Use the same NLP adapter for both add_word and the job runner so snapshot hashes stay consistent
    shared_nlp = FakeNLPAdapter()

    # Add word with always-failing verification — this queues the verify_word job
    use_case = WordbankUseCase(
        db_path,
        nlp_adapter=shared_nlp,
        verification_service=AlwaysFailingVerification(),
    )
    added = use_case.add_word("hund", "hund")
    assert added.verification.status == "queued"

    # Set max_attempts=1 so the first failure is the final one (avoids multi-second retry delays)
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE wordbank_background_jobs SET max_attempts = 1 WHERE job_type = 'verify_word'"
        )

    # Create a services namespace that provides the failing verification service and safe fakes for others.
    # nlp_adapter must match the one used for add_word so snapshot hashes are consistent.
    class _Services:
        typo_engine = None
        translation_service = FakeTranslationService({})
        gemini_word_translation_service = FakeGeminiWordTranslationService({})
        gemini_related_words_service = None
        nlp_adapter = shared_nlp
        cor_lexicon_service = None
        cor_local_lexicon_service = FakeCORLocalLexiconService()
        en_local_lexicon_service = None
        en_gemini_translation_service = None
        word_verification_service = AlwaysFailingVerification()
        tts_service = FakeTTSService({})

    runner = WordbankBackgroundJobRunner(
        db_path=db_path,
        services=_Services(),
        gemini_changes_log_path=None,
        max_workers=1,
        poll_interval_seconds=0.05,
    )
    runner.start()
    time.sleep(0.5)  # enough for one attempt + completion
    runner.stop()

    # The verification record must now be 'error', not 'queued'
    details = use_case.get_lemma_details("hund")
    if details.meaning_sections:
        status = details.meaning_sections[0].verification.status
    else:
        status = details.verification.status
    assert status == "error", f"Expected 'error' after permanent job failure, got '{status}'"


def test_verify_word_background_job_auto_applies_fix_translation_for_homograph_meaning(tmp_path: Path) -> None:
    import time

    from app.services.use_cases.wordbank.background_jobs import WordbankBackgroundJobRunner

    person = _cor_local_entry(
        cor_id="COR.MOR.PERSON.LEM",
        lemma="mor",
        gloss="person",
        form="mor",
        lemma_idx=51046,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    soil = _cor_local_entry(
        cor_id="COR.MOR.SOIL.LEM",
        lemma="mor",
        gloss="jordlag",
        form="mor",
        lemma_idx=51047,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )

    class ConditionalVerificationService:
        provider = "gemini"
        reviewer_role = "Professional Danish Language Expert"

        def __init__(self) -> None:
            self.calls: list[tuple[int | None, str | None, str | None]] = []

        def verify_word_entry(self, payload):
            self.calls.append((payload.meaning_id, payload.meaning_gloss, payload.selected_translation))

            class Result:
                categories = ()
                composed_word_count = None
                problem = None
                change_to_implement = None

            if payload.meaning_gloss == "jordlag":
                Result.verdict = "flagged"
                Result.message = "Wrong translation"
                Result.suggested_actions = (
                    WordVerificationAction(
                        action_type="fix_translation",
                        english_translation="soil layer",
                        reason="Use the gloss translation for this meaning.",
                    ),
                )
            else:
                Result.verdict = "verified"
                Result.message = "OK"
                Result.suggested_actions = ()
            return Result()

        def classify_word_categories(self, _payload):
            class Result:
                categories = ()

            return Result()

    db_path = _db_path(tmp_path)
    shared_nlp = FakeNLPAdapter()
    verification_service = ConditionalVerificationService()
    cor_local = FakeCORLocalLexiconService(
        by_form={"mor": [person, soil]},
        by_lemma_idx={51046: [person], 51047: [soil]},
    )
    translation_service = FakeTranslationService({"person": "person", "jordlag": "soil layer"})
    use_case = WordbankUseCase(
        db_path,
        nlp_adapter=shared_nlp,
        cor_local_lexicon_service=cor_local,
        translation_service=translation_service,
        verification_service=verification_service,
    )

    use_case.add_word(
        "mor",
        "mor",
        search_seed={
            "lemma": "mor",
            "surface": "mor",
            "cor_id": "COR.MOR.PERSON.LEM",
            "cor_lemma_idx": 51046,
            "meaning_key": "person",
            "gloss": "person",
            "english_translation": "mother",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )
    added = use_case.add_word(
        "mor",
        "mor",
        search_seed={
            "lemma": "mor",
            "surface": "mor",
            "cor_id": "COR.MOR.SOIL.LEM",
            "cor_lemma_idx": 51047,
            "meaning_key": "soil-layer",
            "gloss": "jordlag",
            "english_translation": "mother",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )
    assert [(target.meaning_id, target.stored_surface_form) for target in added.queued_verification_targets] == [
        (1, None),
        (2, None),
    ]

    _shared_nlp = shared_nlp
    _cor_local = cor_local
    _verification_service = verification_service

    class _Services:
        typo_engine = None
        translation_service = FakeTranslationService({"person": "person", "jordlag": "soil layer"})
        gemini_word_translation_service = FakeGeminiWordTranslationService({})
        gemini_related_words_service = None
        nlp_adapter = _shared_nlp
        cor_lexicon_service = None
        cor_local_lexicon_service = _cor_local
        en_local_lexicon_service = None
        en_gemini_translation_service = None
        word_verification_service = _verification_service
        tts_service = FakeTTSService({})

    runner = WordbankBackgroundJobRunner(
        db_path=db_path,
        services=_Services(),
        gemini_changes_log_path=None,
        max_workers=1,
        poll_interval_seconds=0.05,
    )
    runner.start()
    time.sleep(0.6)
    runner.stop()

    details = use_case.get_lemma_details("mor")
    assert [section.english_translation for section in details.meaning_sections] == ["mother", "soil layer"]
    assert all((section.verification.status if section.verification is not None else None) == "verified" for section in details.meaning_sections)

    repository = WordbankRepository(db_path)
    entries = repository.get_change_log_entries_for_lemma("mor")
    assert len(entries) == 1
    assert entries[0].meaning_id == 2
    assert entries[0].action_type == "fix_translation"
    assert verification_service.calls == [
        (1, "person", "mother"),
        (2, "jordlag", "mother"),
    ]


def test_verify_word_background_job_requeues_stale_sibling_targets_after_auto_apply(tmp_path: Path) -> None:
    import time

    from app.services.use_cases.wordbank.background_jobs import WordbankBackgroundJobRunner

    person = _cor_local_entry(
        cor_id="COR.MOR.PERSON.LEM",
        lemma="mor",
        gloss="person",
        form="mor",
        lemma_idx=51046,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    soil = _cor_local_entry(
        cor_id="COR.MOR.SOIL.LEM",
        lemma="mor",
        gloss="jordlag",
        form="mor",
        lemma_idx=51047,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )

    class MultiAutoApplyVerificationService:
        provider = "gemini"
        reviewer_role = "Professional Danish Language Expert"

        def __init__(self) -> None:
            self.calls: list[tuple[int | None, str | None, str | None]] = []

        def verify_word_entry(self, payload):
            self.calls.append((payload.meaning_id, payload.meaning_gloss, payload.selected_translation))

            class Result:
                verdict = "flagged"
                message = "Wrong translation"
                categories = ()
                composed_word_count = None
                problem = None
                change_to_implement = None

            Result.suggested_actions = (
                WordVerificationAction(
                    action_type="fix_translation",
                    english_translation="soil layer" if payload.meaning_gloss == "jordlag" else "person",
                    reason="Use the translated gloss for this meaning.",
                ),
            )
            return Result()

        def classify_word_categories(self, _payload):
            class Result:
                categories = ()

            return Result()

    db_path = _db_path(tmp_path)
    shared_nlp = FakeNLPAdapter()
    verification_service = MultiAutoApplyVerificationService()
    cor_local = FakeCORLocalLexiconService(
        by_form={"mor": [person, soil]},
        by_lemma_idx={51046: [person], 51047: [soil]},
    )
    translation_service = FakeTranslationService({"person": "person", "jordlag": "soil layer"})
    use_case = WordbankUseCase(
        db_path,
        nlp_adapter=shared_nlp,
        cor_local_lexicon_service=cor_local,
        translation_service=translation_service,
        verification_service=verification_service,
    )

    use_case.add_word(
        "mor",
        "mor",
        search_seed={
            "lemma": "mor",
            "surface": "mor",
            "cor_id": "COR.MOR.PERSON.LEM",
            "cor_lemma_idx": 51046,
            "meaning_key": "person",
            "gloss": "person",
            "english_translation": "mother",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )
    use_case.add_word(
        "mor",
        "mor",
        search_seed={
            "lemma": "mor",
            "surface": "mor",
            "cor_id": "COR.MOR.SOIL.LEM",
            "cor_lemma_idx": 51047,
            "meaning_key": "soil-layer",
            "gloss": "jordlag",
            "english_translation": "mother",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )

    _shared_nlp = shared_nlp
    _cor_local = cor_local
    _verification_service = verification_service

    class _Services:
        typo_engine = None
        translation_service = FakeTranslationService({"person": "person", "jordlag": "soil layer"})
        gemini_word_translation_service = FakeGeminiWordTranslationService({})
        gemini_related_words_service = None
        nlp_adapter = _shared_nlp
        cor_lexicon_service = None
        cor_local_lexicon_service = _cor_local
        en_local_lexicon_service = None
        en_gemini_translation_service = None
        word_verification_service = _verification_service
        tts_service = FakeTTSService({})

    runner = WordbankBackgroundJobRunner(
        db_path=db_path,
        services=_Services(),
        gemini_changes_log_path=None,
        max_workers=1,
        poll_interval_seconds=0.05,
    )
    runner.start()
    time.sleep(2.0)
    runner.stop()

    details = use_case.get_lemma_details("mor")
    assert [section.english_translation for section in details.meaning_sections] == ["person", "soil layer"]
    assert all((section.verification.status if section.verification is not None else None) == "verified" for section in details.meaning_sections)

    with get_connection(db_path) as conn:
        job_rows = conn.execute(
            """
            SELECT id, status, rerun_requested
            FROM wordbank_background_jobs
            WHERE job_type = 'verify_word'
            ORDER BY id ASC
            """
        ).fetchall()
    assert [str(row["status"]) for row in job_rows] == ["completed", "completed"]
    assert [bool(row["rerun_requested"]) for row in job_rows] == [False, False]

    repository = WordbankRepository(db_path)
    entries = repository.get_change_log_entries_for_lemma("mor")
    assert len(entries) == 2
    assert {entry.meaning_id for entry in entries} == {1, 2}
    assert len(verification_service.calls) >= 3
