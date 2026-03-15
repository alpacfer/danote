from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.api.schemas.v1.wordbank import LemmaDetailsResponse
from app.db.migrations import get_connection
from app.nlp.adapter import NLPToken
from app.services.tts import PronunciationAudio
from app.services.use_cases.wordbank import WordbankUseCase
from app.services.verification import WordVerificationAction
from tests.helpers.factories import _bog_homograph_cor_local, _cor_local_entry, _db_path
from tests.helpers.fakes import (
    FakeCORLocalLexiconService,
    FakeGeminiWordTranslationService,
    FakeTranslationService,
    FakeTTSService,
    FakeVerificationService,
)

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
    assert len(verification_service.category_calls) == 1
    assert verification_service.calls[0].available_surface_forms == verification_service.category_calls[0].available_surface_forms
    assert verification_service.category_calls[0].available_surface_forms[0].form == "bog"
    assert verification_service.category_calls[0].available_surface_forms[0].english_translation == "book"
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
                    message = "Entry is consistent."
                    categories = ("Food",)

                return Result()
            raise RuntimeError("provider unavailable")

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

    use_case.add_word(
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

    verified = use_case.verify_added_word("lære", "lærer", meaning_id=None)

    payload = verification_service.calls[0]
    assert verified.applied_categories == ["Actions", "School"]
    assert payload.selected_translation == "learn"
    assert payload.selected_translation_scope == "lemma"
    assert payload.available_categories
    assert [form.form for form in payload.available_surface_forms] == ["lærer"]
    assert payload.canonical_lemma_pos_tag == "VERB"
    assert payload.canonical_lemma_morphology == "VerbForm=Inf|Voice=Act"
    assert payload.selected_surface_pos_tag == "VERB"
    assert payload.selected_surface_morphology == "Tense=Pres|VerbForm=Fin|Voice=Act"
    details = use_case.get_lemma_details("lære")
    assert details.categories == ["Actions", "School"]


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
                message = "incorrect"
                problem = "Plural forms are missing."
                change_to_implement = "Add the missing plural forms."
                suggested_actions = (
                    WordVerificationAction(
                        action_type="fix_variations",
                        reason="Complete the paradigm.",
                        plural_indefinite_form="bøger",
                        plural_definite_form="bøgerne",
                    ),
                )
                categories = ()

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


def test_complete_variations_review_adds_fix_variations_action(tmp_path: Path) -> None:
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
    assert [action.action_type for action in verified.verification.suggested_actions] == ["fix_variations"]
    assert verified.verification.suggested_actions[0].plural_indefinite_form == "mødre"
    assert verified.verification.suggested_actions[0].plural_definite_form == "mødrene"


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
    assert [action.action_type for action in verified.verification.suggested_actions] == ["fix_variations"]


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
        action={"action_type": "fix_variations"},
        provider="gemini",
    )

    assert response.status == "applied"
    assert response.applied_action_type == "fix_variations"
    details = use_case.get_lemma_details("mor")
    assert sorted(form.form for form in details.meaning_sections[0].surface_forms) == ["moren", "mødre", "mødrene"]


def test_wordbank_use_case_hydrates_fix_variations_apply_from_saved_review_text(tmp_path: Path) -> None:
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
    assert [action.action_type for action in verified.verification.suggested_actions] == ["fix_variations"]
    response = use_case.apply_verification_changes(
        stored_lemma="mor",
        stored_surface_form=None,
        meaning_id=added.meaning.id,
        action={"action_type": "fix_variations"},
        provider="gemini",
    )

    assert response.status == "applied"
    assert response.applied_action_type == "fix_variations"
    details = use_case.get_lemma_details("mor")
    assert sorted(form.form for form in details.meaning_sections[0].surface_forms) == ["moren", "mødre", "mødrene"]


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
        stored_surface_form="bogen",
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


def test_wordbank_use_case_applies_gloss_verification_action(tmp_path: Path) -> None:
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

    assert response.status == "applied"
    assert response.applied_action_type == "fix_gloss"
    with get_connection(db_path) as conn:
        meaning_row = conn.execute(
            "SELECT gloss FROM lexeme_meanings WHERE id = ?",
            (added.meaning.id,),
        ).fetchone()
    assert meaning_row is not None
    assert meaning_row["gloss"] == "reading material"


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
        stored_surface_form="bogen",
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
    assert payload["stored_surface_form"] == "bogen"
    assert payload["action"]["english_translation"] == "Book"
    assert payload["action_type"] == "fix_translation"
    assert "timestamp_utc" in payload
