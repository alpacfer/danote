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

def test_wordbank_use_case_runs_verification_task_and_returns_result(tmp_path: Path) -> None:
    verification_service = FakeVerificationService(
        verdict="verified",
        message="Lemma, surface form, and translations are coherent.",
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
    assert "coherent" in verified.verification.message.lower()
    assert verified.verification.requested_at is not None
    assert verified.verification.completed_at is not None
    assert len(verification_service.calls) == 1

    details_after_verify = use_case.get_lemma_details("bog")
    assert details_after_verify.meaning_sections[0].verification is not None
    assert details_after_verify.meaning_sections[0].verification.status == "verified"


def test_word_verification_payload_uses_saved_and_canonical_metadata_for_search_seed_entries(tmp_path: Path) -> None:
    verification_service = FakeVerificationService(
        verdict="verified",
        message="Entry is consistent.",
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
            "english_translation": None,
            "pos_tag": "VERB",
            "morphology": "Tense=Pres|VerbForm=Fin|Voice=Act",
        },
    )

    use_case.verify_added_word("lære", "lærer", meaning_id=None)

    payload = verification_service.calls[0]
    assert payload.selected_translation is None
    assert payload.selected_translation_scope is None
    assert payload.canonical_lemma_pos_tag == "VERB"
    assert payload.canonical_lemma_morphology == "VerbForm=Inf|Voice=Act"
    assert payload.selected_surface_pos_tag == "VERB"
    assert payload.selected_surface_morphology == "Tense=Pres|VerbForm=Fin|Voice=Act"

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
    assert details.meaning_sections[0].surface_forms[0].has_pronunciation is True


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
    assert [item.form for item in by_key["book"].surface_forms] == []
    assert [item.form for item in by_key["swamp"].surface_forms] == ["bogen", "moser"]


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
