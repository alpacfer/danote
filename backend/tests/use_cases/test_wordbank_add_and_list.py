from __future__ import annotations

import json
from pathlib import Path

from app.api.schemas.v1.wordbank import LemmaDetailsResponse
from app.db.migrations import get_connection
from app.nlp.adapter import NLPToken
from app.services.tts import PronunciationAudio
from app.services.use_cases.wordbank import WordbankUseCase
from tests.helpers.factories import _bog_homograph_cor_local, _db_path
from tests.helpers.fakes import (
    FakeGeminiWordTranslationService,
    FakeTranslationService,
    FakeTTSService,
    FakeVerificationService,
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
    assert details.surface_forms == []
    assert len(details.meaning_sections) == 1
    assert details.meaning_sections[0].meaning_key == "bog"
    assert [item.form for item in details.meaning_sections[0].surface_forms] == ["bogen"]

    listing = use_case.list_lemmas()
    assert listing.items[0].lemma == "bog"
    assert listing.items[0].display_lemma == "bog"
    assert listing.items[0].variation_count == 1
    assert listing.items[0].english_translation is None

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

    verified = use_case.verify_added_word("bog", "bogen", meaning_id=added.meaning.id if added.meaning else None)
    assert verified.verification.status == "verified"
    assert "coherent" in verified.verification.message.lower()
    assert len(verification_service.calls) == 1

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
    assert details.surface_forms == []
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
        )
    ]

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

def test_wordbank_use_case_applies_verification_changes(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(db_path)
    added = use_case.add_word("Bogen", "bog")

    response = use_case.apply_verification_changes(
        stored_lemma="bog",
        stored_surface_form="bogen",
        meaning_id=added.meaning.id if added.meaning else None,
        suggested_changes={
            "lemma_pos_tag": "NOUN",
            "lemma_morphology": "Gender=Com|Number=Sing",
            "surface_pos_tag": "NOUN",
            "surface_morphology": "Definite=Def|Number=Sing",
            "lexeme_translation": "book",
        },
        provider="gemini",
    )

    assert response.status == "applied"
    assert set(response.applied_fields) == {
        "lemma_pos_tag",
        "lemma_morphology",
        "surface_pos_tag",
        "surface_morphology",
        "lexeme_translation",
    }

    with get_connection(db_path) as conn:
        meaning_row = conn.execute(
            """
            SELECT pos_tag, morphology, english_translation
            FROM lexeme_meanings
            WHERE id = ?
            """,
            (added.meaning.id,),
        ).fetchone()
        surface_row = conn.execute(
            """
            SELECT pos_tag, morphology
            FROM surface_forms
            WHERE meaning_id = ? AND form = ?
            """,
            (added.meaning.id, "bogen"),
        ).fetchone()

    assert meaning_row is not None
    assert meaning_row["pos_tag"] == "NOUN"
    assert meaning_row["morphology"] == "Gender=Com|Number=Sing"
    assert meaning_row["english_translation"] == "book"
    assert surface_row is not None
    assert surface_row["pos_tag"] == "NOUN"
    assert surface_row["morphology"] == "Definite=Def|Number=Sing"

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
        suggested_changes={
            "lemma_pos_tag": "NOUN",
            "lexeme_translation": "Book",
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
    assert payload["suggested_changes"]["lexeme_translation"] == "book"
    assert "timestamp_utc" in payload

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
    assert adapter.calls == calls_after_add

