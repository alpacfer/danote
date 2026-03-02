from __future__ import annotations

from pathlib import Path

from app.api.schemas.v1.wordbank import LemmaDetailsResponse
from app.db.migrations import apply_migrations, get_connection
from app.services.use_cases.analyze import AnalyzeNoteUseCase, strip_inline_comments
from app.services.use_cases.sentencebank import SentencebankUseCase
from app.services.use_cases.wordbank import WordbankUseCase
from app.nlp.adapter import NLPToken
from app.services.tts import PronunciationAudio




class FakeTranslationService:
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
            form="bogen",
            english_translation=None,
        )
    ]

    listing = use_case.list_lemmas()
    assert listing.items[0].lemma == "bog"
    assert listing.items[0].display_lemma == "bog"
    assert listing.items[0].variation_count == 1
    assert listing.items[0].english_translation is None


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
            form="bogen",
            english_translation="the book",
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
            form="bogen",
            english_translation=None,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing",
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
    assert audio.audio_bytes == b"wav-2"
    assert tts_service.calls == ["bogen", "bogen"]


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
