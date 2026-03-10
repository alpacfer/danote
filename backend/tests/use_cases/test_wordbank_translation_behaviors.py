from __future__ import annotations

from pathlib import Path

from app.api.schemas.v1.wordbank import LemmaDetailsResponse
from app.db.migrations import get_connection
from app.services.cor_local import CORLocalEntry
from app.services.use_cases.wordbank import WordbankUseCase
from tests.helpers.factories import _cor_local_entry, _db_path
from tests.helpers.fakes import (
    FakeCORLocalLexiconService,
    FakeGeminiWordTranslationService,
    FakeTranslationService,
)


def test_wordbank_use_case_stores_lemma_translation_on_meaning_sections_only(
    tmp_path: Path,
) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"bog": "book", "bogen": "the book"}),
    )

    use_case.add_word("Bogen", "bog")

    details = use_case.get_lemma_details("bog")
    assert details.english_translation == "book"
    assert details.is_sectioned is True
    assert details.surface_forms == []
    assert len(details.meaning_sections) == 1
    assert details.meaning_sections[0].english_translation == "book"
    assert details.meaning_sections[0].surface_forms == [
        LemmaDetailsResponse.SurfaceFormDetails(
            form="bogen",
            lemma="bog",
            lemma_translation="book",
        )
    ]

def test_wordbank_sectioned_add_prefers_cor_lemma_translation_and_skips_variation_translation(
    tmp_path: Path,
) -> None:
    db_path = _db_path(tmp_path)
    noun_lemma = _cor_local_entry(
        cor_id="COR.49032.110.01",
        lemma="lærer",
        gloss="teacher",
        form="lærer",
        lemma_idx=49032,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    noun_plural = _cor_local_entry(
        cor_id="COR.49032.112.01",
        lemma="lærer",
        gloss="teacher",
        form="lærere",
        lemma_idx=49032,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Plur|Definite=Ind",
        gram_raw="sb.fk.pl.ubest",
    )
    translation_service = FakeTranslationService({"en lærer": "a teacher"})
    gemini_translation = FakeGeminiWordTranslationService(
        {
            ("lærer", "lærer", "teacher"): "apprenticeship",
            ("lærere", "lærer", "teacher"): "teachers",
        }
    )
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={
                "lærer": [noun_lemma],
                "lærere": [noun_plural],
            },
            by_lemma_idx={
                49032: [noun_lemma, noun_plural],
            },
        ),
        translation_service=translation_service,
        gemini_word_translation_service=gemini_translation,
    )

    added = use_case.add_word(
        "lærere",
        "lærer",
        cor_id="COR.49032.112.01",
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Plur|Definite=Ind",
    )

    calls_after_add = list(translation_service.calls)
    gemini_calls_after_add = list(gemini_translation.calls)
    gemini_batch_calls_after_add = [list(batch) for batch in gemini_translation.batch_calls]
    details = use_case.get_lemma_details("lærer")
    assert added.meaning is not None
    assert details.is_sectioned is True
    assert details.english_translation == "teacher"
    assert len(details.meaning_sections) == 1
    assert details.meaning_sections[0].english_translation == "teacher"
    assert details.meaning_sections[0].surface_forms == [
        LemmaDetailsResponse.SurfaceFormDetails(
            form="lærere",
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Plur|Definite=Ind",
            lemma="lærer",
            lemma_translation="teacher",
            gloss="teacher",
            gloss_translation="teacher",
            gram_raw="sb.fk.pl.ubest",
        )
    ]
    assert translation_service.calls == calls_after_add
    assert gemini_translation.calls == gemini_calls_after_add
    assert gemini_translation.batch_calls == gemini_batch_calls_after_add

    with get_connection(db_path) as conn:
        surface_row = conn.execute(
            """
            SELECT form
            FROM surface_forms
            WHERE meaning_id = ? AND form = ?
            LIMIT 1
            """,
            (added.meaning.id, "lærere"),
        ).fetchone()

    assert surface_row is not None
    assert surface_row["form"] == "lærere"

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

def test_wordbank_generate_translation_calls_gemini_once_when_unavailable(tmp_path: Path) -> None:
    gemini_translation = FakeGeminiWordTranslationService({})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"mere": "mere"}),
        gemini_word_translation_service=gemini_translation,
    )

    generated = use_case.generate_translation("Mere", "mere")

    assert generated.status == "unavailable"
    assert generated.english_translation is None
    assert gemini_translation.batch_calls == []
    assert gemini_translation.calls == [("mere", "mere", None)]

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

    details = use_case.get_lemma_details("bog")

    with get_connection(db_path) as conn:
        meaning_row = conn.execute(
            """
            SELECT english_translation
            FROM lexeme_meanings
            WHERE lexeme_id = (SELECT id FROM lexemes WHERE lemma = ?)
            """,
            ("bog",),
        ).fetchone()
        surface_row = conn.execute(
            """
            SELECT form
            FROM surface_forms
            WHERE meaning_id = (SELECT id FROM lexeme_meanings WHERE lexeme_id = (SELECT id FROM lexemes WHERE lemma = ?))
              AND form = ?
            """,
            ("bog", "bogen"),
        ).fetchone()

    assert meaning_row is not None
    assert meaning_row["english_translation"] == "book"
    assert details.english_translation == "book"
    assert surface_row is not None
    assert surface_row["form"] == "bogen"

def test_wordbank_sectioned_details_keep_lemma_translation_and_expose_translated_gloss(
    tmp_path: Path,
) -> None:
    db_path = _db_path(tmp_path)
    reading_lemma = _cor_local_entry(
        cor_id="COR.BOG.READING.LEM",
        lemma="bog",
        gloss="til læsning",
        form="bog",
        lemma_idx=123,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    reading_surface = _cor_local_entry(
        cor_id="COR.BOG.READING.DEF",
        lemma="bog",
        gloss="til læsning",
        form="bogen",
        lemma_idx=123,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Def",
        gram_raw="sb.fk.sg.best",
    )
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={
                "bog": [reading_lemma],
                "bogen": [reading_surface],
            },
            by_lemma_idx={123: [reading_lemma, reading_surface]},
        ),
        translation_service=FakeTranslationService({
            "en bog": "book",
            "til læsning": "for reading",
        }),
    )

    use_case.add_word("Bogen", "bog")

    details = use_case.get_lemma_details("bog")

    with get_connection(db_path) as conn:
        meaning_row = conn.execute(
            """
            SELECT gloss, english_translation
            FROM lexeme_meanings
            WHERE lexeme_id = (SELECT id FROM lexemes WHERE lemma = ?)
            """,
            ("bog",),
        ).fetchone()

    assert meaning_row is not None
    assert meaning_row["gloss"] == "til læsning"
    assert meaning_row["english_translation"] == "book"
    assert details.meaning_sections[0].gloss == "til læsning"
    assert details.meaning_sections[0].english_translation == "book"
    assert details.meaning_sections[0].gloss_translation == "for reading"
    assert details.meaning_sections[0].surface_forms == [
        LemmaDetailsResponse.SurfaceFormDetails(
            form="bogen",
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing|Definite=Def",
            lemma="bog",
            lemma_translation="book",
            gloss="til læsning",
            gloss_translation="for reading",
            gram_raw="sb.fk.sg.best",
            has_pronunciation=False,
        )
    ]

def test_wordbank_sectioned_details_do_not_overwrite_lemma_translation_with_english_gloss(
    tmp_path: Path,
) -> None:
    db_path = _db_path(tmp_path)
    mother_lemma = _cor_local_entry(
        cor_id="COR.MOR.LEM",
        lemma="mor",
        gloss="person",
        form="mor",
        lemma_idx=51046,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"mor": [mother_lemma]},
            by_lemma_idx={51046: [mother_lemma]},
        ),
        translation_service=FakeTranslationService({"en mor": "a mother", "person": "person"}),
    )

    use_case.add_word("Mor", "mor")
    details = use_case.get_lemma_details("mor")

    with get_connection(db_path) as conn:
        meaning_row = conn.execute(
            """
            SELECT gloss, english_translation
            FROM lexeme_meanings
            WHERE lexeme_id = (SELECT id FROM lexemes WHERE lemma = ?)
            """,
            ("mor",),
        ).fetchone()

    assert meaning_row is not None
    assert meaning_row["gloss"] == "person"
    assert meaning_row["english_translation"] == "mother"
    assert details.english_translation == "mother"
    assert details.meaning_sections[0].english_translation == "mother"
    assert details.meaning_sections[0].gloss_translation == "person"
    assert details.meaning_sections[0].surface_forms == []

def test_add_word_batches_gemini_only_for_lemma_translation(tmp_path: Path) -> None:
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
    gemini_translation = FakeGeminiWordTranslationService(
        {
            ("bog", "bog", "book"): "book",
            ("bogen", "bog", "book"): "the book",
        }
    )
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService({"bog": "book-fallback", "bogen": "book-fallback"}),
        gemini_word_translation_service=gemini_translation,
    )

    use_case.add_word("Bogen", "bog")

    assert gemini_translation.batch_calls == [[("bog", "bog", "book")]]
    assert gemini_translation.calls == []

