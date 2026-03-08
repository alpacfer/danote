from __future__ import annotations

import json
from pathlib import Path

from app.api.schemas.v1.wordbank import LemmaDetailsResponse
from app.db.migrations import apply_migrations, get_connection
from app.services.use_cases.analyze import AnalyzeNoteUseCase, strip_inline_comments
from app.services.use_cases.sentencebank import SentencebankUseCase
from app.services.use_cases.wordbank import WordbankUseCase
from app.services.cor import COREntry
from app.services.cor_local import CORLocalEntry
from app.nlp.adapter import NLPToken
from app.services.tts import PronunciationAudio




class FakeTranslationService:
    provider = "azure_translator"

    def __init__(self, mapping: dict[str, str], detected_languages: dict[str, str] | None = None):
        self._mapping = mapping
        self._detected_languages = detected_languages or {}
        self.calls: list[str] = []

    def translate_da_to_en(self, text: str) -> str | None:
        self.calls.append(text)
        return self._mapping.get(text)

    def translate_en_to_da(self, text: str) -> str | None:
        self.calls.append(text)
        return self._mapping.get(text)

    def detect_source_language(self, text: str) -> str | None:
        self.calls.append(text)
        return self._detected_languages.get(text)

class FakeNLPAdapter:
    def tokenize(self, text: str) -> list[NLPToken]:
        return [
            NLPToken(text="Hej", lemma="hej", pos="INTJ", morphology="PronType=Prs", is_punctuation=False),
            NLPToken(text=",", lemma=None, pos=None, morphology=None, is_punctuation=True),
            NLPToken(text=" ", lemma=None, pos=None, morphology=None, is_punctuation=False),
            NLPToken(text="bog", lemma="bog", pos="NOUN", morphology="Definite=Ind|Gender=Com", is_punctuation=False),
        ]

    def lemma_candidates_for_token(self, token: str) -> list[str]:
        return [token.lower()]

    def lemma_for_token(self, token: str) -> str | None:
        return token.lower()

    def metadata(self) -> dict[str, str]:
        return {"adapter": "fake"}


class FakeCORLexiconService:
    def __init__(self, mapping: dict[str, list[COREntry]]):
        self._mapping = {key.lower(): value for key, value in mapping.items()}

    def lookup_full_form(self, value: str) -> list[COREntry]:
        return list(self._mapping.get(value.lower(), []))


class FakeCORLocalLexiconService:
    def __init__(
        self,
        by_form: dict[str, list[CORLocalEntry]] | None = None,
        by_lemma_idx: dict[int, list[CORLocalEntry]] | None = None,
    ):
        self._by_form = {key.lower(): value for key, value in (by_form or {}).items()}
        self._by_lemma_idx = by_lemma_idx or {}

    def lookup_form(self, value: str, limit: int = 100) -> list[CORLocalEntry]:
        return list(self._by_form.get(value.lower(), []))[:limit]

    def lookup_lemma(self, lemma_idx: int, limit: int = 1000) -> list[CORLocalEntry]:
        return list(self._by_lemma_idx.get(lemma_idx, []))[:limit]


class FakeVerificationService:
    provider = "gemini"
    reviewer_role = "Professional Danish Language Expert"

    def __init__(self, verdict: str = "verified", message: str = "Entry is consistent."):
        self._verdict = verdict
        self._message = message
        self.calls = []

    def verify_word_entry(self, payload):
        self.calls.append(payload)

        class Result:
            def __init__(self, verdict: str, message: str):
                self.verdict = verdict
                self.message = message

        return Result(self._verdict, self._message)


class FakeGeminiWordTranslationService:
    provider = "gemini_word_translation"

    def __init__(self, mapping: dict[tuple[str, str, str | None], str]):
        self._mapping = mapping
        self.calls: list[tuple[str, str, str | None]] = []

    def translate_word(self, payload) -> str | None:
        key = (payload.surface_form, payload.lemma, payload.gloss)
        self.calls.append(key)
        return self._mapping.get(key)


class FakeTTSService:
    provider = "gemini_tts"
    model = "gemini-2.5-flash-preview-tts"

    def __init__(self, mapping: dict[str, bytes]):
        self._mapping = mapping
        self.calls: list[str] = []

    def synthesize(self, text: str) -> PronunciationAudio | None:
        self.calls.append(text)
        data = self._mapping.get(text)
        if not data:
            return None
        return PronunciationAudio(audio_bytes=data, mime_type="audio/wav")


def _db_path(tmp_path: Path) -> Path:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    return db_path


def test_wordbank_use_case_round_trip(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    added = use_case.add_word("Bogen", "bog")
    assert added.status == "inserted"
    assert added.stored_lemma == "bog"
    assert added.stored_surface_form == "bogen"

    details = use_case.get_lemma_details("bog")
    assert details.lemma == "bog"
    assert details.surface_forms == [
        LemmaDetailsResponse.SurfaceFormDetails(
            form="bog",
            english_translation=None,
            lemma="bog",
            lemma_translation=None,
        ),
        LemmaDetailsResponse.SurfaceFormDetails(
            form="bogen",
            english_translation=None,
            lemma="bog",
            lemma_translation=None,
        )
    ]

    listing = use_case.list_lemmas()
    assert listing.items[0].lemma == "bog"
    assert listing.items[0].display_lemma == "bog"
    assert listing.items[0].variation_count == 2
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
    assert details.surface_forms[1].english_translation == "the book"


def test_wordbank_use_case_stores_deepl_translations_for_lemma_and_surface(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"bog": "book", "bogen": "the book"}),
    )

    use_case.add_word("Bogen", "bog")

    details = use_case.get_lemma_details("bog")
    assert details.english_translation == "book"
    assert details.surface_forms == [
        LemmaDetailsResponse.SurfaceFormDetails(
            form="bog",
            english_translation="book",
            lemma="bog",
            lemma_translation="book",
        ),
        LemmaDetailsResponse.SurfaceFormDetails(
            form="bogen",
            english_translation="the book",
            lemma="bog",
            lemma_translation="book",
        )
    ]


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

    verified = use_case.verify_added_word("bog", "bogen")
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
    assert details.surface_forms == [
        LemmaDetailsResponse.SurfaceFormDetails(
            form="bog",
            english_translation=None,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing",
            lemma="bog",
            lemma_translation=None,
        ),
        LemmaDetailsResponse.SurfaceFormDetails(
            form="bogen",
            english_translation=None,
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
                audio_bytes=f"wav-{self._counter}".encode("utf-8"),
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
    use_case.add_word("Bogen", "bog")

    response = use_case.apply_verification_changes(
        stored_lemma="bog",
        stored_surface_form="bogen",
        suggested_changes={
            "lemma_pos_tag": "NOUN",
            "lemma_morphology": "Gender=Com|Number=Sing",
            "surface_pos_tag": "NOUN",
            "surface_morphology": "Definite=Def|Number=Sing",
            "lexeme_translation": "book",
            "surface_translation": "the book",
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
        "surface_translation",
    }

    with get_connection(db_path) as conn:
        lexeme_row = conn.execute(
            "SELECT pos_tag, morphology, english_translation, translation_provider FROM lexemes WHERE lemma = ?",
            ("bog",),
        ).fetchone()
        surface_row = conn.execute(
            """
            SELECT pos_tag, morphology, english_translation, translation_provider
            FROM surface_forms
            WHERE form = ?
            """,
            ("bogen",),
        ).fetchone()

    assert lexeme_row is not None
    assert lexeme_row["pos_tag"] == "NOUN"
    assert lexeme_row["morphology"] == "Gender=Com|Number=Sing"
    assert lexeme_row["english_translation"] == "book"
    assert lexeme_row["translation_provider"] == "gemini"
    assert surface_row is not None
    assert surface_row["pos_tag"] == "NOUN"
    assert surface_row["morphology"] == "Definite=Def|Number=Sing"
    assert surface_row["english_translation"] == "the book"
    assert surface_row["translation_provider"] == "gemini"


def test_wordbank_use_case_logs_gemini_applied_changes(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(db_path)
    use_case.add_word("Bogen", "bog")
    log_path = tmp_path / "gemini-applied-changes.jsonl"

    use_case = WordbankUseCase(db_path, gemini_changes_log_path=log_path)
    response = use_case.apply_verification_changes(
        stored_lemma="bog",
        stored_surface_form="bogen",
        suggested_changes={
            "lemma_pos_tag": "NOUN",
            "lexeme_translation": "Book",
            "surface_translation": "The Book",
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
    assert payload["suggested_changes"]["surface_translation"] == "the book"
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


def test_wordbank_search_lemmas_matches_variations(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))
    use_case.add_word("Bogens", "bog")
    use_case.add_word("Huse", "hus")

    result = use_case.search_lemmas("gens")

    assert len(result.items) == 1
    assert result.items[0].lemma == "bog"
    assert result.items[0].match_surface == "bogens"


def test_wordbank_search_lemmas_uses_matched_surface_metadata(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))
    use_case.add_word(
        "Ulykker",
        "ulykke",
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Plur|Definite=Ind",
    )

    result = use_case.search_lemmas("ulykker")

    assert len(result.items) == 1
    assert result.items[0].lemma == "ulykke"
    assert result.items[0].match_surface == "ulykker"
    assert result.items[0].pos_tag == "NOUN"
    assert result.items[0].morphology == "Gender=Com|Number=Plur|Definite=Ind"


def test_wordbank_search_lemmas_prefers_exact_surface_match_and_stable_variation_count(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))
    use_case.add_word("abc", "lemma")
    use_case.add_word("aabc", "lemma")
    use_case.add_word("abcx", "lemma")

    result = use_case.search_lemmas("abc")

    assert len(result.items) == 1
    assert result.items[0].lemma == "lemma"
    assert result.items[0].match_surface == "abc"
    assert result.items[0].variation_count == 4


def test_wordbank_search_lemmas_prioritizes_exact_surface_match_over_prefix_lemmas(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))
    use_case.add_word("abc", "target")
    for index in range(10):
        token = f"abcx{index}"
        use_case.add_word(token, token)

    result = use_case.search_lemmas("abc", limit=8)

    assert len(result.items) == 8
    assert result.items[0].lemma == "target"
    assert result.items[0].match_surface == "abc"


def test_wordbank_generate_translation_uses_surface_form_not_lemma(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"bogen": "book", "bogens": "book's"}),
    )

    generated_a = use_case.generate_translation("Bogen", "bog")
    generated_b = use_case.generate_translation("Bogens", "bog")

    assert generated_a.status == "generated"
    assert generated_a.source_word == "bogen"
    assert generated_a.lemma == "bog"
    assert generated_a.english_translation == "book"
    assert generated_b.status == "generated"
    assert generated_b.source_word == "bogens"
    assert generated_b.lemma == "bog"
    assert generated_b.english_translation == "book's"


def test_wordbank_translation_is_normalized_to_lowercase(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"bogen": "The Book"}),
    )

    generated = use_case.generate_translation("Bogen", "bog")

    assert generated.status == "generated"
    assert generated.english_translation == "the book"


def test_wordbank_generate_translation_falls_back_to_gemini_when_azure_echoes_input(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"mere": "mere"}),
        gemini_word_translation_service=FakeGeminiWordTranslationService({("mere", "mere", None): "more"}),
    )

    generated = use_case.generate_translation("Mere", "mere")

    assert generated.status == "generated"
    assert generated.english_translation == "more"


def test_wordbank_generate_translation_returns_unavailable_when_azure_echoes_input_and_gemini_is_missing(
    tmp_path: Path,
) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"mere": "mere"}),
    )

    generated = use_case.generate_translation("Mere", "mere")

    assert generated.status == "unavailable"
    assert generated.english_translation is None


def test_wordbank_phrase_translation_does_not_use_gemini_when_azure_echoes_input(tmp_path: Path) -> None:
    gemini_translation = FakeGeminiWordTranslationService({("mere", "mere", None): "more"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"mere": "mere"}),
        gemini_word_translation_service=gemini_translation,
    )

    generated = use_case.generate_phrase_translation("Mere")

    assert generated.status == "generated"
    assert generated.english_translation == "mere"
    assert gemini_translation.calls == []


def test_wordbank_phrase_translation_caches_by_normalized_phrase(tmp_path: Path) -> None:
    translation_service = FakeTranslationService({"jeg kan godt lide det": "i like it"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=translation_service,
    )

    generated = use_case.generate_phrase_translation("Jeg kan godt lide det")
    cached = use_case.generate_phrase_translation("  jeg   kan godt   lide det ")

    assert generated.status == "generated"
    assert generated.source_text == "jeg kan godt lide det"
    assert generated.english_translation == "i like it"
    assert cached.status == "cached"
    assert cached.source_text == "jeg kan godt lide det"
    assert cached.english_translation == "i like it"
    assert translation_service.calls == ["jeg kan godt lide det"]


def test_wordbank_generate_reverse_translation_uses_en_to_da_provider(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"house": "hus"}),
    )

    generated = use_case.generate_reverse_translation("House")
    assert generated.status == "generated"
    assert generated.source_word == "house"
    assert generated.danish_translation == "hus"


def test_wordbank_generate_reverse_translation_normalizes_provider_case(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"mug": "Krus"}),
    )

    generated = use_case.generate_reverse_translation("Mug")
    assert generated.status == "generated"
    assert generated.source_word == "mug"
    assert generated.danish_translation == "krus"


def test_wordbank_detect_word_language_uses_provider_signal(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({}, detected_languages={"house": "EN"}),
    )

    detected = use_case.detect_word_language("House")
    assert detected.source_word == "house"
    assert detected.language == "en"
    assert detected.confidence == 0.82


def test_wordbank_detect_word_language_handles_danish_characters_without_provider(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path), translation_service=FakeTranslationService({}))

    detected = use_case.detect_word_language("børn")
    assert detected.source_word == "børn"
    assert detected.language == "da"
    assert detected.confidence == 0.99


def test_wordbank_detect_word_language_marks_short_homographs_as_ambiguous(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({}, detected_languages={"is": "EN"}),
    )

    detected = use_case.detect_word_language("is")
    assert detected.source_word == "is"
    assert detected.language == "ambiguous"
    assert detected.confidence == 0.4

def test_wordbank_resolve_query_returns_variation_match_summary(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"bog": "book", "bogen": "the book"}),
    )
    use_case.add_word("Bogen", "bog")

    resolved = use_case.resolve_query("Bogen")

    assert resolved.query_surface == "bogen"
    assert resolved.query_lemma == "bog"
    assert resolved.classification == "known"
    assert resolved.matched_lemma == "bog"
    assert resolved.matched_lemma_summary is not None
    assert resolved.matched_lemma_summary.lemma == "bog"
    assert resolved.matched_lemma_summary.english_translation == "book"


def test_wordbank_resolve_query_generates_translation_and_language_signals(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService(
            {"house": "hus"},
            detected_languages={"house": "EN"},
        ),
    )

    resolved = use_case.resolve_query("House")

    assert resolved.query_surface == "house"
    assert resolved.classification == "new"
    assert resolved.en_to_da_translation == "hus"
    assert resolved.resolved_surface == "hus"
    assert resolved.resolved_lemma == "hus"
    assert resolved.query_language == "en"
    assert resolved.query_language_confidence == 0.82


def test_wordbank_resolve_query_expands_new_word_actions_with_cor_pos_options(tmp_path: Path) -> None:
    cor_service = FakeCORLexiconService(
        {
            "gift": [
                COREntry(
                    cor_id="COR.1",
                    lemma="gift",
                    full_form="gift",
                    ordklasse="sb",
                    grammatical_function="sb.fk.sg.ubest",
                    glosse=None,
                    norm_status="N",
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Ind",
                ),
                COREntry(
                    cor_id="COR.2",
                    lemma="gifte",
                    full_form="gift",
                    ordklasse="vb",
                    grammatical_function="vb.imp",
                    glosse=None,
                    norm_status="N",
                    pos_tag="VERB",
                    morphology="Mood=Imp|VerbForm=Fin",
                ),
            ]
        }
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_lexicon_service=cor_service,
        translation_service=FakeTranslationService(
            {
                "gift": "poison",
                "at gifte": "marry",
            }
        ),
    )

    resolved = use_case.resolve_query("gift", include_language_detection=True)

    assert resolved.classification == "new"
    assert resolved.query_lemma == "gift"
    assert resolved.query_language == "da"
    assert (resolved.query_language_confidence or 0) >= 0.9
    assert len(resolved.word_actions) == 2
    assert [action.action_type for action in resolved.word_actions] == ["add_as_new", "add_as_new"]
    assert [action.pos_tag for action in resolved.word_actions] == ["NOUN", "VERB"]
    assert [action.lemma for action in resolved.word_actions] == ["gift", "gifte"]
    assert [action.translation_label for action in resolved.word_actions] == ["poison", "marry"]


def test_wordbank_resolve_query_returns_single_best_option_per_pos(tmp_path: Path) -> None:
    cor_service = FakeCORLexiconService(
        {
            "lærer": [
                COREntry(
                    cor_id="COR.verb",
                    lemma="lære",
                    full_form="lærer",
                    ordklasse="vb",
                    grammatical_function="vb.prs.akt",
                    glosse=None,
                    norm_status="N",
                    pos_tag="VERB",
                    morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
                ),
                COREntry(
                    cor_id="COR.noun.pl",
                    lemma="lære",
                    full_form="lærer",
                    ordklasse="sb",
                    grammatical_function="sb.fk.pl.ubest",
                    glosse=None,
                    norm_status="N",
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Plur|Definite=Ind",
                ),
                COREntry(
                    cor_id="COR.noun.sg",
                    lemma="lærer",
                    full_form="lærer",
                    ordklasse="sb",
                    grammatical_function="sb.fk.sg.ubest",
                    glosse=None,
                    norm_status="N",
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Ind",
                ),
            ]
        }
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_lexicon_service=cor_service,
        translation_service=FakeTranslationService(
            {
                "at lære": "to learn",
                "lærer": "teacher",
                "lære": "learn",
            }
        ),
    )

    resolved = use_case.resolve_query("lærer", include_language_detection=True)

    assert len(resolved.word_actions) == 2
    assert [action.pos_tag for action in resolved.word_actions] == ["NOUN", "VERB"]
    assert [action.lemma for action in resolved.word_actions] == ["lærer", "lære"]
    assert [action.translation_label for action in resolved.word_actions] == ["teacher", "to learn"]


def test_wordbank_search_cor_form_groups_variants_by_lemma_gloss_pos(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "lærer": [
                CORLocalEntry(
                    cor_id="COR.49032.110.01",
                    lemma="lærer",
                    gloss="teacher",
                    gram_raw="sb.fk.sg.ubest",
                    form="lærer",
                    norm="N",
                    lemma_idx=49032,
                    gram_code=110,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Ind",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.49032.112.01",
                    lemma="lærer",
                    gloss="teacher",
                    gram_raw="sb.fk.pl.ubest",
                    form="lærere",
                    norm="N",
                    lemma_idx=49032,
                    gram_code=112,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Plur|Definite=Ind",
                    features={"Gender": "Com", "Number": "Plur", "Definite": "Ind"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.30686.203.01",
                    lemma="lære",
                    gloss="learn",
                    gram_raw="vb.præs.akt",
                    form="lærer",
                    norm="N",
                    lemma_idx=30686,
                    gram_code=203,
                    variation=1,
                    pos_tag="VERB",
                    morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
                    features={"Tense": "Pres", "VerbForm": "Fin", "Voice": "Act"},
                    extra_tags=[],
                ),
            ]
        }
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService(
            {
                "en lærer": "a teacher",
                "at lære": "to learn",
            }
        ),
    )

    response = use_case.search_cor_form("LÆRER", limit=100)

    assert response.form == "lærer"
    assert len(response.groups) == 2
    assert response.groups[0].lemma == "lærer"
    assert response.groups[0].gloss == "teacher"
    assert response.groups[0].pos_tag == "NOUN"
    assert [variant.cor_id for variant in response.groups[0].variants] == [
        "COR.49032.110.01",
        "COR.49032.112.01",
    ]
    assert response.groups[0].variants[0].lemma_translation == "teacher"
    assert response.groups[0].variants[1].lemma_translation == "teacher"
    assert response.groups[1].lemma == "lære"
    assert response.groups[1].pos_tag == "VERB"
    assert response.groups[1].variants[0].lemma_translation == "to learn"


def test_wordbank_search_cor_form_uses_gemini_for_gloss_aware_translations(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "bogen": [
                CORLocalEntry(
                    cor_id="COR.123.111.01",
                    lemma="bog",
                    gloss="book",
                    gram_raw="sb.fk.sg.best",
                    form="bogen",
                    norm="N",
                    lemma_idx=123,
                    gram_code=111,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Def",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Def"},
                    extra_tags=[],
                ),
            ]
        }
    )
    gemini_translation = FakeGeminiWordTranslationService({("bogen", "bog", "book"): "the book"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService({"en bog": "a book"}),
        gemini_word_translation_service=gemini_translation,
    )

    response = use_case.search_cor_form("bogen", limit=100)

    assert response.groups[0].variants[0].lemma_translation == "the book"
    assert response.groups[0].variants[0].gloss_translation == "the book"
    assert gemini_translation.calls == [("bogen", "bog", "book"), ("bogen", "bog", "book")]


def test_wordbank_search_cor_form_translates_comma_separated_gloss_parts(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "glas": [
                CORLocalEntry(
                    cor_id="COR.50306.120.01",
                    lemma="glas",
                    gloss="drikkeglas, brilleglas",
                    gram_raw="sb.itk.sg.ubest",
                    form="glas",
                    norm="N",
                    lemma_idx=50306,
                    gram_code=120,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Neut|Number=Sing|Definite=Ind",
                    features={"Gender": "Neut", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
            ]
        }
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService(
            {
                "et glas": "a glass",
                "drikkeglas": "drinking glass",
                "brilleglas": "eyeglass lens",
            }
        ),
    )

    response = use_case.search_cor_form("glas", limit=100)

    assert response.groups[0].variants[0].gloss_translation == "drinking glass, eyeglass lens"


def test_add_word_persists_gemini_gloss_aware_translations(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "bog": [
                CORLocalEntry(
                    cor_id="COR.123.110.01",
                    lemma="bog",
                    gloss="book",
                    gram_raw="sb.fk.sg.ubest",
                    form="bog",
                    norm="N",
                    lemma_idx=123,
                    gram_code=110,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Ind",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
            ],
            "bogen": [
                CORLocalEntry(
                    cor_id="COR.123.111.01",
                    lemma="bog",
                    gloss="book",
                    gram_raw="sb.fk.sg.best",
                    form="bogen",
                    norm="N",
                    lemma_idx=123,
                    gram_code=111,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Def",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Def"},
                    extra_tags=[],
                ),
            ],
        }
    )
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService({"bog": "book-fallback", "bogen": "book-fallback"}),
        gemini_word_translation_service=FakeGeminiWordTranslationService(
            {
                ("bog", "bog", "book"): "book",
                ("bogen", "bog", "book"): "the book",
            }
        ),
    )

    use_case.add_word("Bogen", "bog")

    with get_connection(db_path) as conn:
        lexeme_row = conn.execute(
            "SELECT english_translation, translation_provider FROM lexemes WHERE lemma = ?",
            ("bog",),
        ).fetchone()
        surface_row = conn.execute(
            "SELECT english_translation, translation_provider FROM surface_forms WHERE form = ?",
            ("bogen",),
        ).fetchone()

    assert lexeme_row is not None
    assert lexeme_row["english_translation"] == "book"
    assert lexeme_row["translation_provider"] == "gemini_word_translation"
    assert surface_row is not None
    assert surface_row["english_translation"] == "the book"
    assert surface_row["translation_provider"] == "gemini_word_translation"


def test_wordbank_search_cor_form_consolidates_same_entry_with_multiple_grams(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "glas": [
                CORLocalEntry(
                    cor_id="COR.50306.120.01",
                    lemma="glas",
                    gloss="drikkeglas, brilleglas",
                    gram_raw="sb.itk.sg.ubest",
                    form="glas",
                    norm="N",
                    lemma_idx=50306,
                    gram_code=120,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Neut|Number=Sing|Definite=Ind",
                    features={"Gender": "Neut", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.50306.122.01",
                    lemma="glas",
                    gloss="drikkeglas, brilleglas",
                    gram_raw="sb.itk.pl.ubest",
                    form="glas",
                    norm="N",
                    lemma_idx=50306,
                    gram_code=122,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Neut|Number=Plur|Definite=Ind",
                    features={"Gender": "Neut", "Number": "Plur", "Definite": "Ind"},
                    extra_tags=[],
                ),
            ]
        }
    )
    use_case = WordbankUseCase(_db_path(tmp_path), cor_local_lexicon_service=local_cor)

    response = use_case.search_cor_form("glas", limit=100)

    assert len(response.groups) == 1
    assert len(response.groups[0].variants) == 1
    assert response.groups[0].variants[0].gram_raw == "sb.itk.sg.ubest | sb.itk.pl.ubest"


def test_wordbank_search_cor_form_prefers_glossed_entries_within_same_pos(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "glas": [
                CORLocalEntry(
                    cor_id="COR.50306.120.01",
                    lemma="glas",
                    gloss="drikkeglas, brilleglas",
                    gram_raw="sb.itk.sg.ubest",
                    form="glas",
                    norm="N",
                    lemma_idx=50306,
                    gram_code=120,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Neut|Number=Sing|Definite=Ind",
                    features={"Gender": "Neut", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.46180.120.01",
                    lemma="glas",
                    gloss=None,
                    gram_raw="sb.itk.sg.ubest",
                    form="glas",
                    norm="N",
                    lemma_idx=46180,
                    gram_code=120,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Neut|Number=Sing|Definite=Ind",
                    features={"Gender": "Neut", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
            ]
        }
    )
    use_case = WordbankUseCase(_db_path(tmp_path), cor_local_lexicon_service=local_cor)

    response = use_case.search_cor_form("glas", limit=100)

    assert len(response.groups) == 1
    assert len(response.groups[0].variants) == 1
    assert response.groups[0].variants[0].gloss == "drikkeglas, brilleglas"


def test_wordbank_search_cor_lemma_paradigm_returns_all_forms(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_lemma_idx={
            49032: [
                CORLocalEntry(
                    cor_id="COR.49032.110.01",
                    lemma="lærer",
                    gloss="teacher",
                    gram_raw="sb.fk.sg.ubest",
                    form="lærer",
                    norm="N",
                    lemma_idx=49032,
                    gram_code=110,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Ind",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.49032.112.01",
                    lemma="lærer",
                    gloss="teacher",
                    gram_raw="sb.fk.pl.ubest",
                    form="lærere",
                    norm="N",
                    lemma_idx=49032,
                    gram_code=112,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Plur|Definite=Ind",
                    features={"Gender": "Com", "Number": "Plur", "Definite": "Ind"},
                    extra_tags=[],
                ),
            ]
        }
    )
    use_case = WordbankUseCase(_db_path(tmp_path), cor_local_lexicon_service=local_cor)

    response = use_case.search_cor_lemma_paradigm(49032, limit=1000)

    assert response.lemma_idx == 49032
    assert [variant.form for variant in response.variants] == ["lærer", "lærere"]


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


def test_wordbank_resolve_query_prefers_cor_metadata_over_runtime_nlp(tmp_path: Path) -> None:
    class ContradictingNLPAdapter:
        def tokenize(self, text: str) -> list[NLPToken]:
            return [
                NLPToken(
                    text=text,
                    lemma=text.lower(),
                    pos="NOUN",
                    morphology="Gender=Neut|Number=Sing",
                    is_punctuation=False,
                )
            ]

        def lemma_candidates_for_token(self, token: str) -> list[str]:
            return [token.lower()]

        def lemma_for_token(self, token: str) -> str | None:
            return token.lower()

        def metadata(self) -> dict[str, str]:
            return {"adapter": "contradicting"}

    cor_service = FakeCORLexiconService(
        {
            "løb": [
                COREntry(
                    cor_id="COR.3",
                    lemma="løbe",
                    full_form="løb",
                    ordklasse="vb",
                    grammatical_function="vb.præt.akt",
                    glosse=None,
                    norm_status="N",
                    pos_tag="VERB",
                    morphology="Tense=Past|VerbForm=Fin|Voice=Act",
                )
            ]
        }
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        nlp_adapter=ContradictingNLPAdapter(),
        cor_lexicon_service=cor_service,
    )

    resolved = use_case.resolve_query("løb", include_translations=False, include_language_detection=False)

    assert resolved.query_pos_tag == "VERB"
    assert resolved.query_morphology == "Tense=Past|VerbForm=Fin|Voice=Act"




def test_wordbank_resolve_query_strips_inline_comments(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    resolved = use_case.resolve_query("House # comment")

    assert resolved.query_surface == "house"

def test_wordbank_resolve_query_skips_short_letter_words(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"is": "ice"}, detected_languages={"is": "EN"}),
    )

    resolved = use_case.resolve_query("is")

    assert resolved.query_surface == "is"
    assert resolved.classification == "uncertain"
    assert resolved.word_actions == []
    assert resolved.da_to_en_translation is None
    assert resolved.en_to_da_translation is None


def test_wordbank_resolve_query_supports_optional_flags(tmp_path: Path) -> None:
    translation_service = FakeTranslationService(
        {"house": "hus"},
        detected_languages={"house": "EN"},
    )
    use_case = WordbankUseCase(_db_path(tmp_path), translation_service=translation_service)

    resolved = use_case.resolve_query(
        "House",
        include_translations=False,
        include_language_detection=False,
    )

    assert resolved.en_to_da_translation is None
    assert resolved.da_to_en_translation is None
    assert resolved.query_language is None
    assert resolved.query_language_confidence is None




def test_wordbank_action_payload_is_consistent_between_resolve_query_and_analyze(tmp_path: Path) -> None:
    class HouseNLPAdapter:
        def tokenize(self, text: str) -> list[NLPToken]:
            return [
                NLPToken(
                    text=text,
                    lemma=text.lower(),
                    pos="NOUN",
                    morphology="Gender=Neut|Number=Sing",
                    is_punctuation=False,
                )
            ]

        def lemma_candidates_for_token(self, token: str) -> list[str]:
            return [token.lower()]

        def lemma_for_token(self, token: str) -> str | None:
            return token.lower()

        def metadata(self) -> dict[str, str]:
            return {"adapter": "house-fake"}

    nlp_adapter = HouseNLPAdapter()
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        translation_service=FakeTranslationService({"house": "hus"}, detected_languages={"house": "EN"}),
        nlp_adapter=nlp_adapter,
    )
    analyze_use_case = AnalyzeNoteUseCase(db_path, nlp_adapter=nlp_adapter)

    resolved = use_case.resolve_query("House", include_translations=False, include_language_detection=False)
    analyzed_tokens = analyze_use_case.execute("House")

    assert len(analyzed_tokens) == 1
    assert resolved.word_actions == analyzed_tokens[0].word_actions
    assert [action.action_type for action in resolved.word_actions] == ["add_as_new"]
    assert resolved.word_actions[0].surface == "house"
    assert resolved.word_actions[0].lemma == "house"

def test_sentencebank_use_case_add_and_list(tmp_path: Path) -> None:
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"Jeg elsker dansk": "i love danish"}),
    )

    inserted = use_case.add_sentence("Jeg elsker dansk")
    duplicate = use_case.add_sentence("  jeg elsker   dansk ")
    listing = use_case.list_sentences()

    assert inserted.status == "inserted"
    assert inserted.source_text == "Jeg elsker dansk"
    assert inserted.english_translation == "i love danish"
    assert duplicate.status == "exists"
    assert listing.items[0].source_text == "Jeg elsker dansk"


def test_sentencebank_translation_is_normalized_to_lowercase(tmp_path: Path) -> None:
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"Jeg elsker dansk": "I LOVE DANISH"}),
    )

    inserted = use_case.add_sentence("Jeg elsker dansk")

    assert inserted.status == "inserted"
    assert inserted.english_translation == "i love danish"




def test_analyze_use_case_propagates_pos_and_morphology(tmp_path: Path) -> None:
    use_case = AnalyzeNoteUseCase(
        _db_path(tmp_path),
        nlp_adapter=FakeNLPAdapter(),
        typo_engine=None,
    )

    tokens = use_case.execute("Hej bog")

    assert tokens[0].surface_token == "Hej"
    assert tokens[0].pos_tag == "INTJ"
    assert tokens[0].morphology == "PronType=Prs"
    assert tokens[1].surface_token == "bog"
    assert tokens[1].pos_tag == "NOUN"
    assert tokens[1].morphology == "Definite=Ind|Gender=Com"

def test_analyze_use_case_skips_short_letter_words(tmp_path: Path) -> None:
    use_case = AnalyzeNoteUseCase(
        _db_path(tmp_path),
        nlp_adapter=FakeNLPAdapter(),
        typo_engine=None,
    )

    tokens = use_case.execute("i to hej bog")
    surfaces = [token.surface_token for token in tokens]
    assert surfaces == ["Hej", "bog"]


def test_analyze_use_case_filters_non_word_tokens(tmp_path: Path) -> None:
    use_case = AnalyzeNoteUseCase(
        _db_path(tmp_path),
        nlp_adapter=FakeNLPAdapter(),
        typo_engine=None,
    )

    tokens = use_case.execute("Hej, bog")
    surfaces = [token.surface_token for token in tokens]
    assert surfaces == ["Hej", "bog"]



def test_analyze_use_case_includes_pos_and_morphology(tmp_path: Path) -> None:
    use_case = AnalyzeNoteUseCase(
        _db_path(tmp_path),
        nlp_adapter=FakeNLPAdapter(),
        typo_engine=None,
    )

    tokens = use_case.execute("Hej, bog")
    assert tokens[0].pos_tag == "INTJ"
    assert tokens[0].morphology == "PronType=Prs"
    assert tokens[1].pos_tag == "NOUN"
    assert tokens[1].morphology == "Definite=Ind|Gender=Com"


def test_strip_inline_comments_removes_text_after_hash_per_line() -> None:
    text = "hej # ignore this\nverden\n# full line comment\nigen # skip"
    stripped = strip_inline_comments(text)
    assert stripped == "hej \nverden\n\nigen "


def test_analyze_use_case_ignores_comment_text_after_hash(tmp_path: Path) -> None:
    class WhitespaceNLPAdapter:
        def tokenize(self, text: str) -> list[NLPToken]:
            return [
                NLPToken(
                    text=part,
                    lemma=part.lower(),
                    pos="X",
                    morphology=None,
                    is_punctuation=False,
                )
                for part in text.split()
            ]

        def lemma_candidates_for_token(self, token: str) -> list[str]:
            return [token.lower()]

        def lemma_for_token(self, token: str) -> str | None:
            return token.lower()

        def metadata(self) -> dict[str, str]:
            return {"adapter": "whitespace-fake"}

    use_case = AnalyzeNoteUseCase(
        _db_path(tmp_path),
        nlp_adapter=WhitespaceNLPAdapter(),
        typo_engine=None,
    )

    tokens = use_case.execute("hej # ignore me\nverden")
    surfaces = [token.surface_token for token in tokens]
    assert surfaces == ["hej", "verden"]

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
    assert details_first.surface_forms[0].pos_tag == "NOUN"

    details_second = use_case.get_lemma_details("bog")
    assert details_second.pos_tag == "NOUN"
    assert details_second.surface_forms[0].morphology == "Number=Sing"
    assert adapter.calls == calls_after_add
