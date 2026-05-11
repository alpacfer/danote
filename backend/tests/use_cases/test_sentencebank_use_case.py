from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.api.schemas.v1.sentencebank import SentenceVerificationErrorItem
from app.nlp.adapter import NLPToken
from app.services.sentence_verification import (
    SentenceVerificationErrorSpan,
    SentenceVerificationResult,
)
from app.services.use_cases.sentencebank import SentencebankUseCase
from app.services.use_cases.wordbank import WordbankUseCase
from app.services.verification import (
    GeminiWordVerificationService,
    WordCategoryClassificationResult,
    WordVerificationResult,
)
from tests.helpers.factories import _cor_local_entry, _db_path
from tests.helpers.fakes import (
    FakeCORLocalLexiconService,
    FakeGeminiWordTranslationService,
    FakeTranslationService,
)


class MappingNLPAdapter:
    def __init__(self, token_map: dict[str, list[NLPToken]]):
        self._token_map = token_map

    def tokenize(self, text: str) -> list[NLPToken]:
        return list(self._token_map.get(text, []))

    def lemma_candidates_for_token(self, token: str) -> list[str]:
        return [token.lower()]

    def lemma_for_token(self, token: str) -> str | None:
        return token.lower()

    def metadata(self) -> dict[str, str]:
        return {"adapter": "MappingNLPAdapter"}


class SelectingGeminiService:
    provider = "gemini_word_translation"

    def __init__(self, selected_id: int | None):
        self._selected_id = selected_id
        self.calls = []
        self.batch_calls = []

    def translate_word(self, _payload) -> str | None:
        return None

    def select_meaning_section(self, payload) -> int | None:
        self.calls.append(payload)
        return self._selected_id

    def select_meaning_sections_batch(self, payloads) -> list[int | None]:
        self.batch_calls.append(payloads)
        return [self._selected_id for _ in payloads]


def _run_pending_sentence_token_verifications(
    db_path: Path,
    *,
    translation_service=None,
    gemini_word_translation_service=None,
    nlp_adapter=None,
    cor_local_lexicon_service=None,
    verification_service=None,
) -> None:
    from app.services.use_cases.wordbank.background_jobs import WordbankBackgroundJobRunner

    services = SimpleNamespace(
        translation_service=translation_service,
        gemini_word_translation_service=gemini_word_translation_service,
        gemini_related_words_service=None,
        nlp_adapter=nlp_adapter,
        cor_lexicon_service=None,
        cor_local_lexicon_service=cor_local_lexicon_service,
        en_local_lexicon_service=None,
        en_gemini_translation_service=None,
        word_verification_service=verification_service,
        sentence_verification_service=None,
        tts_service=None,
    )
    runner = WordbankBackgroundJobRunner(
        db_path=db_path,
        services=services,
        gemini_changes_log_path=None,
    )
    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, payload_json
                FROM wordbank_background_jobs
                WHERE job_type = 'verify_sentence_tokens' AND status = 'pending'
                ORDER BY id ASC
                """
            ).fetchall()
        for job_id, payload_json in rows:
            runner._handle_job("verify_sentence_tokens", json.loads(str(payload_json)))
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    """
                    UPDATE wordbank_background_jobs
                    SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (int(job_id),),
                )
    finally:
        runner.stop()


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
    assert inserted.english_translation == "I love danish"
    assert duplicate.status == "exists"
    assert listing.items[0].source_text == "Jeg elsker dansk"
    assert duplicate.tokens == []


def test_sentencebank_translation_preserves_provider_text_without_forcing_lowercase(tmp_path: Path) -> None:
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"Jeg elsker dansk": "I LOVE DANISH"}),
    )

    inserted = use_case.add_sentence("Jeg elsker dansk")

    assert inserted.status == "inserted"
    assert inserted.english_translation == "I LOVE DANISH"


def test_sentencebank_save_resolves_translation_and_tokens_concurrently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleep_seconds = 0.2

    def slow_translation(**_kwargs) -> str:
        time.sleep(sleep_seconds)
        return "hello world"

    def slow_token_resolution(*_args, **_kwargs) -> tuple[list, list[dict[str, object]]]:
        time.sleep(sleep_seconds)
        return [], []

    monkeypatch.setattr(
        "app.services.use_cases.sentencebank.lookup_phrase_translation",
        slow_translation,
    )
    monkeypatch.setattr(
        "app.services.use_cases.sentencebank.resolve_sentence_tokens",
        slow_token_resolution,
    )
    use_case = SentencebankUseCase(_db_path(tmp_path))

    started = time.perf_counter()
    inserted = use_case.add_sentence("Hej verden")
    elapsed = time.perf_counter() - started

    assert inserted.status == "inserted"
    assert inserted.english_translation == "hello world"
    assert elapsed < sleep_seconds * 1.75


def test_sentencebank_save_reuses_cached_phrase_translation(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    translation_service = FakeTranslationService({"Jeg kan godt lide det": "i like it"})
    wordbank_use_case = WordbankUseCase(
        db_path,
        translation_service=translation_service,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        translation_service=translation_service,
        wordbank_use_case=wordbank_use_case,
    )

    preview = wordbank_use_case.generate_phrase_translation("Jeg kan godt lide det")
    inserted = sentencebank_use_case.add_sentence("  jeg   kan godt   lide det ")

    assert preview.status == "generated"
    assert inserted.status == "inserted"
    assert inserted.english_translation == "i like it"
    assert translation_service.calls == ["Jeg kan godt lide det"]


def test_sentencebank_save_persists_every_word_token_in_order_including_short_and_repeated_words(
    tmp_path: Path,
) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "Du og du": [
                NLPToken(text="Du", lemma="du", pos="PRON", morphology="PronType=Prs", is_punctuation=False),
                NLPToken(text="og", lemma="og", pos="CCONJ", morphology=None, is_punctuation=False),
                NLPToken(text="du", lemma="du", pos="PRON", morphology="PronType=Prs", is_punctuation=False),
            ],
        }
    )
    wordbank_use_case = WordbankUseCase(db_path, nlp_adapter=nlp_adapter)
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence("Du og du")
    duplicate = sentencebank_use_case.add_sentence("Du og du")

    assert [token.surface_form for token in inserted.tokens] == ["Du", "og", "du"]
    assert [token.stored_lemma for token in inserted.tokens] == ["du", "og", "du"]
    assert [token.token_index for token in inserted.tokens] == [0, 1, 2]
    assert [token.surface_form for token in duplicate.tokens] == ["Du", "og", "du"]


def test_sentencebank_save_uses_static_pronoun_metadata_without_translation_selection(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "Du ser hvad": [
                NLPToken(text="Du", lemma="du", pos="PRON", morphology=None, is_punctuation=False),
                NLPToken(text="ser", lemma="se", pos="VERB", morphology=None, is_punctuation=False),
                NLPToken(text="hvad", lemma="hvad", pos="PRON", morphology=None, is_punctuation=False),
            ],
        }
    )
    gemini_service = SelectingGeminiService(selected_id=1)
    wordbank_use_case = WordbankUseCase(
        db_path,
        gemini_word_translation_service=gemini_service,
        cor_local_lexicon_service=FakeCORLocalLexiconService(),
        nlp_adapter=nlp_adapter,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        translation_service=FakeTranslationService({"Du ser hvad": "you see what"}),
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence("Du ser hvad")
    details = wordbank_use_case.get_lemma_details("du")

    du_token = inserted.tokens[0]
    hvad_token = inserted.tokens[2]
    assert du_token.stored_lemma == "du"
    assert du_token.english_translation == "you"
    assert du_token.pos_tag == "PRON"
    assert du_token.morphology == "PronType=Prs|Case=Nom|Person=2|Number=Sing"
    assert hvad_token.stored_lemma == "hvad"
    assert hvad_token.english_translation == "what"
    assert details.english_translation == "you"
    assert gemini_service.batch_calls == []


def test_sentencebank_save_uses_static_hv_metadata_without_translation_selection(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "Hvor bor du": [
                NLPToken(text="Hvor", lemma="hvor", pos="ADV", morphology=None, is_punctuation=False),
                NLPToken(text="bor", lemma="bo", pos="VERB", morphology=None, is_punctuation=False),
                NLPToken(text="du", lemma="du", pos="PRON", morphology=None, is_punctuation=False),
            ],
        }
    )
    gemini_service = SelectingGeminiService(selected_id=1)
    wordbank_use_case = WordbankUseCase(
        db_path,
        gemini_word_translation_service=gemini_service,
        cor_local_lexicon_service=FakeCORLocalLexiconService(),
        nlp_adapter=nlp_adapter,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        translation_service=FakeTranslationService({"Hvor bor du": "where do you live"}),
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence("Hvor bor du")
    hvor_token = inserted.tokens[0]

    assert hvor_token.stored_lemma == "hvor"
    assert hvor_token.english_translation == "where"
    assert hvor_token.pos_tag == "ADV"
    assert hvor_token.morphology == "PronType=Int"
    assert gemini_service.batch_calls == []


def test_sentencebank_static_example_preview_returns_hv_example(tmp_path: Path) -> None:
    sentencebank_use_case = SentencebankUseCase(_db_path(tmp_path))

    preview = sentencebank_use_case.generate_static_example_preview("hvor")

    assert preview.source_text == "hvor bor du?"
    assert preview.english_translation == "Where do you live?"


def test_sentencebank_save_persists_word_tokens_when_nlp_is_unavailable(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    wordbank_use_case = WordbankUseCase(db_path)
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=None,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence("Jeg elsker dansk.")

    assert [token.surface_form for token in inserted.tokens] == ["Jeg", "elsker", "dansk"]
    assert [token.stored_lemma for token in inserted.tokens] == ["jeg", "elsker", "dansk"]
    assert [token.token_index for token in inserted.tokens] == [0, 1, 2]


def test_sentencebank_save_links_existing_saved_words_without_duplication(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "Huset huset": [
                NLPToken(text="Huset", lemma="hus", pos="NOUN", morphology="Gender=Neut|Number=Sing|Definite=Def", is_punctuation=False),
                NLPToken(text="huset", lemma="hus", pos="NOUN", morphology="Gender=Neut|Number=Sing|Definite=Def", is_punctuation=False),
            ],
        }
    )
    translation_service = FakeTranslationService({"hus": "house", "huset": "the house"})
    wordbank_use_case = WordbankUseCase(
        db_path,
        translation_service=translation_service,
        nlp_adapter=nlp_adapter,
    )
    added_word = wordbank_use_case.add_word("huset", "hus")
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        translation_service=translation_service,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence("Huset huset")

    assert added_word.meaning is not None
    assert [token.lexeme_id for token in inserted.tokens] == [inserted.tokens[0].lexeme_id, inserted.tokens[0].lexeme_id]
    assert [token.meaning_id for token in inserted.tokens] == [added_word.meaning.id, added_word.meaning.id]


def test_sentencebank_homograph_token_uses_gemini_sentence_selection(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "Min mor kommer": [
                NLPToken(text="mor", lemma="mor", pos="NOUN", morphology="Gender=Com|Number=Sing|Definite=Ind", is_punctuation=False),
            ],
        }
    )
    mother = _cor_local_entry(
        cor_id="COR.MOR.MOTHER.01",
        lemma="mor",
        gloss="person",
        form="mor",
        lemma_idx=51046,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    soil = _cor_local_entry(
        cor_id="COR.MOR.SOIL.01",
        lemma="mor",
        gloss="jordlag",
        form="mor",
        lemma_idx=51047,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    gemini_service = SelectingGeminiService(selected_id=1)
    wordbank_use_case = WordbankUseCase(
        db_path,
        translation_service=FakeTranslationService({"en mor": "a mother", "jordlag": "soil layer"}),
        gemini_word_translation_service=gemini_service,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"mor": [mother, soil]},
            by_lemma_idx={51046: [mother], 51047: [soil]},
        ),
        nlp_adapter=nlp_adapter,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence("Min mor kommer")

    assert gemini_service.batch_calls
    assert gemini_service.batch_calls[0][0].sentence_context == "Min mor kommer"
    assert inserted.tokens[0].meaning_id is not None
    assert inserted.tokens[0].gloss == "person"


def test_sentencebank_token_translation_uses_sentence_context_for_selected_meaning(
    tmp_path: Path,
) -> None:
    db_path = _db_path(tmp_path)
    sentence = "Militæret er et svært sted at være i"
    nlp_adapter = MappingNLPAdapter(
        {
            sentence: [
                NLPToken(text="sted", lemma="sted", pos="NOUN", morphology="Gender=Neut|Number=Sing", is_punctuation=False),
            ],
        }
    )
    place_entry = _cor_local_entry(
        cor_id="COR.STED.01",
        lemma="sted",
        gloss="somewhere",
        form="sted",
        lemma_idx=62001,
        pos_tag="NOUN",
        morphology="Gender=Neut|Number=Sing|Definite=Ind",
        gram_raw="sb.itk.sg.ubest",
    )
    gemini_translation = FakeGeminiWordTranslationService(
        {("sted", "sted", "somewhere"): "place"}
    )
    wordbank_use_case = WordbankUseCase(
        db_path,
        gemini_word_translation_service=gemini_translation,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"sted": [place_entry]},
            by_lemma_idx={62001: [place_entry]},
        ),
        nlp_adapter=nlp_adapter,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence(sentence)
    details = wordbank_use_case.get_lemma_details("sted")

    assert inserted.tokens[0].english_translation == "place"
    assert details.meaning_sections[0].english_translation == "place"
    assert gemini_translation.calls == [("sted", "sted", "somewhere")]


def test_sentencebank_static_der_uses_existential_sentence_context(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    sentence = "Der er noget skørt derovre"
    nlp_adapter = MappingNLPAdapter(
        {
            sentence: [
                NLPToken(text="Der", lemma="der", pos="PRON", morphology=None, is_punctuation=False),
                NLPToken(text="noget", lemma="noget", pos="PRON", morphology=None, is_punctuation=False),
            ],
        }
    )
    wordbank_use_case = WordbankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence(sentence)
    details = wordbank_use_case.get_lemma_details("der")

    der_token = inserted.tokens[0]
    assert der_token.stored_lemma == "der"
    assert der_token.meaning_id is not None
    assert der_token.english_translation == "there"
    assert details.is_sectioned is True
    assert [(section.pos_tag, section.english_translation) for section in details.meaning_sections] == [
        ("ADV", "there"),
        ("PRON", "who / which"),
    ]


def test_sentencebank_static_en_uses_article_sense_without_linking_et(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    sentence = "Der er en bil"
    nlp_adapter = MappingNLPAdapter(
        {
            sentence: [
                NLPToken(text="en", lemma="en", pos="DET", morphology="Gender=Com|Number=Sing", is_punctuation=False),
            ],
        }
    )
    wordbank_use_case = WordbankUseCase(db_path, nlp_adapter=nlp_adapter)
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence(sentence)
    en_details = wordbank_use_case.get_lemma_details("en")
    et_details = wordbank_use_case.get_lemma_details("et")

    assert inserted.tokens[0].stored_lemma == "en"
    assert inserted.tokens[0].english_translation == "a / an"
    assert [(section.pos_tag, section.english_translation) for section in en_details.meaning_sections] == [
        ("DET", "a / an"),
        ("NUM", "one"),
    ]
    assert all(form.form != "et" for form in en_details.surface_forms)
    assert et_details.lemma == "et"
    assert [(section.pos_tag, section.english_translation) for section in et_details.meaning_sections] == [
        ("DET", "a / an"),
        ("NUM", "one"),
    ]
    assert et_details.meaning_sections[1].reference_links[0].tab_id == "cardinal_numbers"


def test_sentencebank_static_et_uses_number_sense(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    sentence = "Jeg har et"
    nlp_adapter = MappingNLPAdapter(
        {
            sentence: [
                NLPToken(text="et", lemma="et", pos="NUM", morphology=None, is_punctuation=False),
            ],
        }
    )
    wordbank_use_case = WordbankUseCase(db_path, nlp_adapter=nlp_adapter)
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence(sentence)
    et_details = wordbank_use_case.get_lemma_details("et")

    assert inserted.tokens[0].stored_lemma == "et"
    assert inserted.tokens[0].meaning_id is not None
    assert inserted.tokens[0].english_translation == "one"
    assert et_details.meaning_sections[1].pos_tag == "NUM"
    assert et_details.meaning_sections[1].reference_links[0].tab_id == "cardinal_numbers"


def test_sentencebank_save_keeps_glossless_have_translation_when_provider_returns_valid_english_verb(
    tmp_path: Path,
) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "Vi har": [
                NLPToken(text="Vi", lemma="vi", pos="PRON", morphology="PronType=Prs", is_punctuation=False),
                NLPToken(text="har", lemma="have", pos="VERB", morphology="Tense=Pres|VerbForm=Fin|Voice=Act", is_punctuation=False),
            ],
        }
    )
    have_infinitive = _cor_local_entry(
        cor_id="COR.30035.200.01",
        lemma="have",
        gloss=None,
        form="have",
        lemma_idx=30035,
        pos_tag="VERB",
        morphology="VerbForm=Inf|Voice=Act",
        gram_raw="vb.inf.akt",
    )
    have_present = _cor_local_entry(
        cor_id="COR.30035.203.01",
        lemma="have",
        gloss=None,
        form="har",
        lemma_idx=30035,
        pos_tag="VERB",
        morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
        gram_raw="vb.præs.akt",
    )
    wordbank_use_case = WordbankUseCase(
        db_path,
        translation_service=FakeTranslationService({"at have": "to have"}),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"har": [have_present]},
            by_lemma_idx={30035: [have_infinitive, have_present]},
        ),
        nlp_adapter=nlp_adapter,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence("Vi har")
    details = wordbank_use_case.get_lemma_details("have")

    har_token = next(token for token in inserted.tokens if token.surface_form == "har")
    assert har_token.english_translation == "to have"
    assert details.meaning_sections[0].english_translation == "to have"


def test_sentencebank_batch_verification_auto_applies_gemini_translation_for_missing_have_translation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "Vi har": [
                NLPToken(text="Vi", lemma="vi", pos="PRON", morphology="PronType=Prs", is_punctuation=False),
                NLPToken(text="har", lemma="have", pos="VERB", morphology="Tense=Pres|VerbForm=Fin|Voice=Act", is_punctuation=False),
            ],
        }
    )
    have_infinitive = _cor_local_entry(
        cor_id="COR.30035.200.01",
        lemma="have",
        gloss=None,
        form="have",
        lemma_idx=30035,
        pos_tag="VERB",
        morphology="VerbForm=Inf|Voice=Act",
        gram_raw="vb.inf.akt",
    )
    have_present = _cor_local_entry(
        cor_id="COR.30035.203.01",
        lemma="have",
        gloss=None,
        form="har",
        lemma_idx=30035,
        pos_tag="VERB",
        morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
        gram_raw="vb.præs.akt",
    )
    verification_service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        verification_service,
        "_generate_content",
        lambda prompt, config=None: type("Response", (), {"text": '{"results":[{"word_id":0,"verdict":"correct","word_count":1,"problem":"","change_to_implement":"","suggested_actions":[]}]}'} )(),
    )
    gemini_translation = FakeGeminiWordTranslationService({("har", "have", None): "have"})
    wordbank_use_case = WordbankUseCase(
        db_path,
        gemini_word_translation_service=gemini_translation,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"har": [have_present]},
            by_lemma_idx={30035: [have_infinitive, have_present]},
        ),
        verification_service=verification_service,
        nlp_adapter=nlp_adapter,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence("Vi har")
    _run_pending_sentence_token_verifications(
        db_path,
        gemini_word_translation_service=gemini_translation,
        nlp_adapter=nlp_adapter,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"har": [have_present]},
            by_lemma_idx={30035: [have_infinitive, have_present]},
        ),
        verification_service=verification_service,
    )
    details = wordbank_use_case.get_lemma_details("have")

    har_token = next(token for token in inserted.tokens if token.surface_form == "har")
    assert har_token.english_translation == "to have"
    assert details.meaning_sections[0].english_translation == "to have"
    assert ("har", "have", None) in gemini_translation.calls


def test_sentencebank_homograph_token_without_confident_selection_skips_ambiguous_word_save(
    tmp_path: Path,
) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "Min mor kommer": [
                NLPToken(text="mor", lemma="mor", pos="NOUN", morphology="Gender=Com|Number=Sing|Definite=Ind", is_punctuation=False),
            ],
        }
    )
    mother = _cor_local_entry(
        cor_id="COR.MOR.MOTHER.01",
        lemma="mor",
        gloss="person",
        form="mor",
        lemma_idx=51046,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    soil = _cor_local_entry(
        cor_id="COR.MOR.SOIL.01",
        lemma="mor",
        gloss="jordlag",
        form="mor",
        lemma_idx=51047,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    wordbank_use_case = WordbankUseCase(
        db_path,
        translation_service=FakeTranslationService({"en mor": "a mother", "jordlag": "soil layer"}),
        gemini_word_translation_service=SelectingGeminiService(selected_id=None),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"mor": [mother, soil]},
            by_lemma_idx={51046: [mother], 51047: [soil]},
        ),
        nlp_adapter=nlp_adapter,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence("Min mor kommer")

    assert inserted.tokens == []


def test_sentencebank_batches_multiple_ambiguous_token_selections(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "Hvis at": [
                NLPToken(text="Hvis", lemma="hvis", pos="SCONJ", morphology=None, is_punctuation=False),
                NLPToken(text="at", lemma="at", pos="PART", morphology="PartType=Inf", is_punctuation=False),
            ],
        }
    )
    gemini_service = SelectingGeminiService(selected_id=1)
    wordbank_use_case = WordbankUseCase(
        db_path,
        translation_service=FakeTranslationService({}),
        gemini_word_translation_service=gemini_service,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={
                "hvis": [
                    _cor_local_entry(cor_id="COR.HVIS.1", lemma="hvis", gloss=None, form="hvis", lemma_idx=1, pos_tag="CCONJ", morphology=None, gram_raw="konj"),
                    _cor_local_entry(cor_id="COR.HVIS.2", lemma="hvis", gloss=None, form="hvis", lemma_idx=2, pos_tag="PRON", morphology=None, gram_raw="pron"),
                ],
                "at": [
                    _cor_local_entry(cor_id="COR.AT.1", lemma="at", gloss=None, form="at", lemma_idx=3, pos_tag="CCONJ", morphology=None, gram_raw="konj"),
                    _cor_local_entry(cor_id="COR.AT.2", lemma="at", gloss=None, form="at", lemma_idx=4, pos_tag=None, morphology=None, gram_raw="part"),
                ],
            },
            by_lemma_idx={1: [], 2: [], 3: [], 4: []},
        ),
        nlp_adapter=nlp_adapter,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence("Hvis at")

    assert inserted.status == "inserted"
    assert len(gemini_service.batch_calls) == 1
    assert len(gemini_service.batch_calls[0]) == 2
    assert wordbank_use_case.runtime.repository.get_lexeme("mor") is None


def test_sentencebank_exact_form_ambiguity_skips_persistence_without_gemini_selection(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "De bad": [
                NLPToken(text="bad", lemma="bede", pos="VERB", morphology="Tense=Past|VerbForm=Fin|Voice=Act", is_punctuation=False),
            ],
        }
    )
    bath = _cor_local_entry(
        cor_id="COR.BAD.NOUN.01",
        lemma="bad",
        gloss=None,
        form="bad",
        lemma_idx=50435,
        pos_tag="NOUN",
        morphology="Gender=Neut|Number=Sing|Definite=Ind",
        gram_raw="sb.itk.sg.ubest",
    )
    bathe = _cor_local_entry(
        cor_id="COR.BADE.IMP.01",
        lemma="bade",
        gloss=None,
        form="bad",
        lemma_idx=35531,
        pos_tag="VERB",
        morphology="Mood=Imp|VerbForm=Fin",
        gram_raw="vb.imp",
    )
    pray = _cor_local_entry(
        cor_id="COR.BEDE.PAST.01",
        lemma="bede",
        gloss=None,
        form="bad",
        lemma_idx=30669,
        pos_tag="VERB",
        morphology="Tense=Past|VerbForm=Fin|Voice=Act",
        gram_raw="vb.præt.akt",
    )
    gemini_service = SelectingGeminiService(selected_id=None)
    wordbank_use_case = WordbankUseCase(
        db_path,
        translation_service=FakeTranslationService({}),
        gemini_word_translation_service=gemini_service,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"bad": [bath, bathe, pray]},
            by_lemma_idx={50435: [bath], 35531: [bathe], 30669: [pray]},
        ),
        nlp_adapter=nlp_adapter,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence("De bad")

    assert gemini_service.batch_calls
    assert len(gemini_service.batch_calls[0][0].meaning_candidates) == 3
    assert {item.lemma for item in gemini_service.batch_calls[0][0].meaning_candidates} == {"bad", "bade", "bede"}
    assert inserted.tokens == []
    assert wordbank_use_case.runtime.repository.get_lexeme("bad") is None
    assert wordbank_use_case.runtime.repository.get_lexeme("bade") is None
    assert wordbank_use_case.runtime.repository.get_lexeme("bede") is None


def test_sentencebank_save_skips_proper_nouns_and_later_capitalized_tokens(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "Jeg møder Anders i Aarhus": [
                NLPToken(text="Jeg", lemma="jeg", pos="PRON", morphology="PronType=Prs", is_punctuation=False),
                NLPToken(text="møder", lemma="møde", pos="VERB", morphology="Tense=Pres|VerbForm=Fin", is_punctuation=False),
                NLPToken(text="Anders", lemma="anders", pos="PROPN", morphology=None, is_punctuation=False),
                NLPToken(text="i", lemma="i", pos="ADP", morphology=None, is_punctuation=False),
                NLPToken(text="Aarhus", lemma="aarhus", pos="PROPN", morphology=None, is_punctuation=False),
            ],
        }
    )
    translation_service = FakeTranslationService({"jeg": "i", "møde": "meet", "i": "in"})
    wordbank_use_case = WordbankUseCase(
        db_path,
        translation_service=translation_service,
        nlp_adapter=nlp_adapter,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence("Jeg møder Anders i Aarhus")
    saved_lemmas = {item.lemma for item in wordbank_use_case.list_lemmas().items}

    assert [token.surface_form for token in inserted.tokens] == ["Jeg", "møder", "i"]
    assert [token.stored_lemma for token in inserted.tokens] == ["jeg", "møde", "i"]
    assert "anders" not in saved_lemmas
    assert "aarhus" not in saved_lemmas


def test_sentencebank_save_skips_capitalized_name_after_punctuation(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "I elsker dig, Cornelius": [
                NLPToken(text="I", lemma="i", pos="PRON", morphology=None, is_punctuation=False),
                NLPToken(text="elsker", lemma="elske", pos="VERB", morphology="Tense=Pres|VerbForm=Fin", is_punctuation=False),
                NLPToken(text="dig", lemma="du", pos="PRON", morphology=None, is_punctuation=False),
                NLPToken(text=",", lemma=None, pos=None, morphology=None, is_punctuation=True),
                NLPToken(text="Cornelius", lemma="cornelius", pos="NOUN", morphology=None, is_punctuation=False),
            ],
        }
    )
    wordbank_use_case = WordbankUseCase(db_path, nlp_adapter=nlp_adapter)
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence("I elsker dig, Cornelius")

    assert [token.surface_form for token in inserted.tokens] == ["I", "elsker", "dig"]
    assert wordbank_use_case.runtime.repository.get_lexeme("cornelius") is None


def test_sentencebank_save_generates_non_cor_word_entry_for_missing_danish_word(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "Det er superstort": [
                NLPToken(text="Det", lemma="det", pos="PRON", morphology="PronType=Prs", is_punctuation=False),
                NLPToken(text="er", lemma="være", pos="AUX", morphology="Tense=Pres|VerbForm=Fin", is_punctuation=False),
                NLPToken(
                    text="superstort",
                    lemma="superstort",
                    pos="ADJ",
                    morphology="Degree=Pos|Gender=Neut|Number=Sing|Definite=Ind",
                    is_punctuation=False,
                ),
            ],
        }
    )
    gemini_service = FakeGeminiWordTranslationService(
        {},
        non_cor_generation_overrides={
            (
                "superstort",
                "superstort",
                "Det er superstort",
            ): {
                "lemma": "superstor",
                "english_translation": "super big",
                "meaning_key": "very large",
                "gloss": "very large",
                "pos_tag": "ADJ",
                "morphology": "Degree=Pos|Number=Sing|Definite=Ind",
                "surface_pos_tag": "ADJ",
                "surface_morphology": "Degree=Pos|Gender=Neut|Number=Sing|Definite=Ind",
            },
        },
    )
    wordbank_use_case = WordbankUseCase(
        db_path,
        gemini_word_translation_service=gemini_service,
        nlp_adapter=nlp_adapter,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence("Det er superstort")

    generated_token = next(token for token in inserted.tokens if token.surface_form == "superstort")
    assert generated_token.stored_lemma == "superstor"
    assert generated_token.meaning_id is not None
    assert gemini_service.non_cor_generation_calls == [
        ("superstort", "superstort", "Det er superstort")
    ]

    details = wordbank_use_case.get_lemma_details("superstor")
    assert details.dictionary_status == "generated_non_cor"
    assert details.meaning_sections[0].dictionary_status == "generated_non_cor"
    assert [item.form for item in details.meaning_sections[0].surface_forms] == ["superstort"]


def test_sentencebank_save_falls_back_to_unknown_root_entry_when_non_cor_generation_is_unavailable(
    tmp_path: Path,
) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "Det er superstort": [
                NLPToken(text="Det", lemma="det", pos="PRON", morphology="PronType=Prs", is_punctuation=False),
                NLPToken(text="er", lemma="være", pos="AUX", morphology="Tense=Pres|VerbForm=Fin", is_punctuation=False),
                NLPToken(
                    text="superstort",
                    lemma="superstort",
                    pos="ADJ",
                    morphology="Degree=Pos|Gender=Neut|Number=Sing|Definite=Ind",
                    is_punctuation=False,
                ),
            ],
        }
    )
    wordbank_use_case = WordbankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence("Det er superstort")

    fallback_token = next(token for token in inserted.tokens if token.surface_form == "superstort")
    assert fallback_token.stored_lemma == "superstort"
    assert fallback_token.meaning_id is None

    details = wordbank_use_case.get_lemma_details("superstort")
    assert details.dictionary_status == "unknown"
    assert details.meaning_sections == []


class FakeVerificationService:
    provider = "fake_verification"
    reviewer_role = "Fake Reviewer"
    batch_calls: list[tuple] = []

    def __init__(self, *, categories: tuple[str, ...] = ()) -> None:
        self._categories = categories

    def verify_word_entry(self, payload):
        return WordVerificationResult(
            verdict="verified", message="OK", composed_word_count=1,
        )

    def verify_word_entries_batch(self, payloads, sentence_context=None):
        self.batch_calls.append((payloads, sentence_context))
        return [
            WordVerificationResult(verdict="verified", message="OK", composed_word_count=1)
            for _ in payloads
        ]

    def classify_word_categories(self, payload):
        return WordCategoryClassificationResult(categories=self._categories)


def test_sentencebank_add_sentence_triggers_batch_verification(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "Huset er stort": [
                NLPToken(text="Huset", lemma="hus", pos="NOUN", morphology="Gender=Neut|Number=Sing|Definite=Def", is_punctuation=False),
                NLPToken(text="er", lemma="være", pos="AUX", morphology="Tense=Pres|VerbForm=Fin", is_punctuation=False),
                NLPToken(text="stort", lemma="stor", pos="ADJ", morphology="Degree=Pos|Gender=Neut|Number=Sing|Definite=Ind", is_punctuation=False),
            ],
        }
    )
    translation_service = FakeTranslationService({"Huset er stort": "the house is big", "hus": "house", "være": "be", "stor": "big"})
    verification_service = FakeVerificationService()
    wordbank_use_case = WordbankUseCase(
        db_path,
        translation_service=translation_service,
        nlp_adapter=nlp_adapter,
        verification_service=verification_service,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        translation_service=translation_service,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence("Huset er stort")

    assert inserted.status == "inserted"
    assert verification_service.batch_calls == []
    with sqlite3.connect(db_path) as conn:
        queued_batch_jobs = conn.execute(
            """
            SELECT COUNT(*)
            FROM wordbank_background_jobs
            WHERE job_type = 'verify_sentence_tokens' AND status = 'pending'
            """
        ).fetchone()[0]
    assert queued_batch_jobs == 1

    _run_pending_sentence_token_verifications(
        db_path,
        translation_service=translation_service,
        nlp_adapter=nlp_adapter,
        verification_service=verification_service,
    )

    assert len(verification_service.batch_calls) == 1
    batch_payloads, batch_context = verification_service.batch_calls[0]
    assert batch_context == "Huset er stort"
    assert len(batch_payloads) >= 1
    with sqlite3.connect(db_path) as conn:
        queued_verify_jobs = conn.execute(
            """
            SELECT COUNT(*)
            FROM wordbank_background_jobs
            WHERE job_type = 'verify_word' AND status = 'pending'
            """
        ).fetchone()[0]
        queued_verification_records = conn.execute(
            """
            SELECT COUNT(*)
            FROM wordbank_verification_records
            WHERE status = 'queued'
            """
        ).fetchone()[0]
    assert queued_verify_jobs == 0
    assert queued_verification_records == 0


class FakeSentenceVerificationService:
    def __init__(self, results: dict[str, SentenceVerificationResult] | None = None, *, should_raise: bool = False):
        self._results = results or {}
        self._should_raise = should_raise
        self.calls: list[str] = []

    def verify_sentence(self, source_text: str) -> SentenceVerificationResult:
        self.calls.append(source_text)
        if self._should_raise:
            raise RuntimeError("verification unavailable")
        return self._results.get(
            source_text,
            SentenceVerificationResult(
                is_valid=True,
                errors=[],
                corrected_text=None,
                language="unknown",
            ),
        )


def test_sentencebank_preview_sentence_search_returns_danish_correction(tmp_path: Path) -> None:
    verification_service = FakeSentenceVerificationService(
        results={
            "jeg er glat": SentenceVerificationResult(
                is_valid=False,
                errors=[SentenceVerificationErrorSpan(start=7, end=11, message="typo")],
                corrected_text="jeg er glad",
                language="da",
            ),
        }
    )
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"jeg er glad": "i am happy"}),
        sentence_verification_service=verification_service,
    )

    preview = use_case.preview_sentence_search("jeg er glat")

    assert preview.status == "ready"
    assert preview.query_language == "da"
    assert preview.source_text == "jeg er glad"
    assert preview.english_translation == "i am happy"
    assert preview.is_valid is False
    assert preview.errors == [SentenceVerificationErrorItem(start=7, end=11, message="typo")]


def test_sentencebank_preview_sentence_search_translates_english_input(tmp_path: Path) -> None:
    verification_service = FakeSentenceVerificationService(
        results={
            "I am happy": SentenceVerificationResult(
                is_valid=True,
                errors=[],
                corrected_text=None,
                language="en",
            ),
        }
    )
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService(
            {"I am happy": "jeg er glad"},
            detected_languages={"I am happy": "EN"},
        ),
        sentence_verification_service=verification_service,
    )

    preview = use_case.preview_sentence_search("I am happy")

    assert preview.status == "ready"
    assert preview.query_language == "en"
    assert preview.source_text == "jeg er glad"
    assert preview.english_translation == "I am happy"
    assert preview.is_valid is True
    assert preview.errors == []


def test_sentencebank_preview_sentence_search_strips_terminal_period_from_danish_translation(tmp_path: Path) -> None:
    verification_service = FakeSentenceVerificationService(
        results={
            "I am happy": SentenceVerificationResult(
                is_valid=True,
                errors=[],
                corrected_text=None,
                language="en",
            ),
        }
    )
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService(
            {"I am happy": "jeg er glad."},
            detected_languages={"I am happy": "EN"},
        ),
        sentence_verification_service=verification_service,
    )

    preview = use_case.preview_sentence_search("I am happy")

    assert preview.source_text == "jeg er glad"
    assert preview.english_translation == "I am happy"


def test_sentencebank_preview_sentence_search_en_uses_gemini_corrected_text(tmp_path: Path) -> None:
    verification_service = FakeSentenceVerificationService(
        results={
            "i am hapy": SentenceVerificationResult(
                is_valid=False,
                errors=[SentenceVerificationErrorSpan(start=5, end=9, message="typo")],
                corrected_text="I am happy",
                language="en",
            ),
        }
    )
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"i am happy": "jeg er glad"}),
        sentence_verification_service=verification_service,
    )

    preview = use_case.preview_sentence_search("i am hapy")

    assert preview.status == "ready"
    assert preview.query_language == "en"
    assert preview.source_text == "jeg er glad"
    assert preview.english_translation == "i am happy"
    assert preview.is_valid is True
    assert preview.errors == []


def test_sentencebank_preview_sentence_search_blocks_on_missing_english_translation(tmp_path: Path) -> None:
    verification_service = FakeSentenceVerificationService(
        results={
            "I am happy": SentenceVerificationResult(
                is_valid=True,
                errors=[],
                corrected_text=None,
                language="en",
            ),
        }
    )
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({}, detected_languages={"I am happy": "EN"}),
        sentence_verification_service=verification_service,
    )

    preview = use_case.preview_sentence_search("I am happy")

    assert preview.status == "blocked"
    assert preview.query_language == "en"
    assert preview.source_text is None
    assert preview.english_translation is None
    assert preview.is_valid is False
    assert preview.errors == []


def test_sentencebank_preview_sentence_search_degrades_when_verification_unavailable(tmp_path: Path) -> None:
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService(
            {"I am happy": "jeg er glad"},
            detected_languages={"I am happy": "EN"},
        ),
        sentence_verification_service=FakeSentenceVerificationService(should_raise=True),
    )

    preview = use_case.preview_sentence_search("I am happy")

    assert preview.status == "ready"
    assert preview.query_language == "en"
    assert preview.source_text == "jeg er glad"
    assert preview.english_translation == "I am happy"
    assert preview.is_valid is True
    assert preview.errors == []


def test_sentencebank_preview_sentence_fast_path_danish(tmp_path: Path) -> None:
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService(
            {"jeg er glad": "i am happy"},
            detected_languages={"jeg er glad": "DA"},
        ),
    )

    preview = use_case.preview_sentence_search("jeg er glad", fast=True)

    assert preview.status == "preview"
    assert preview.query_language == "da"
    assert preview.source_text == "jeg er glad"
    assert preview.english_translation == "i am happy"
    assert preview.is_valid is True
    assert preview.errors == []


def test_sentencebank_preview_sentence_fast_path_english(tmp_path: Path) -> None:
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"I am happy": "jeg er glad"}),
    )

    preview = use_case.preview_sentence_search("I am happy", fast=True)

    assert preview.status == "preview"
    assert preview.query_language == "en"
    assert preview.source_text == "jeg er glad"
    assert preview.english_translation == "I am happy"
    assert preview.is_valid is True
    assert preview.errors == []


def test_sentencebank_preview_sentence_fast_path_strips_terminal_period_from_danish_translation(
    tmp_path: Path,
) -> None:
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"I am happy": "jeg er glad."}),
    )

    preview = use_case.preview_sentence_search("I am happy", fast=True)

    assert preview.status == "preview"
    assert preview.query_language == "en"
    assert preview.source_text == "jeg er glad"
    assert preview.english_translation == "I am happy"


def test_sentencebank_preview_sentence_fast_path_unknown_language(tmp_path: Path) -> None:
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({}),
    )

    preview = use_case.preview_sentence_search("café au lait", fast=True)

    assert preview.status == "preview"
    assert preview.query_language == "unknown"
    assert preview.source_text == "café au lait"
    assert preview.english_translation is None
    assert preview.is_valid is True
    assert preview.errors == []


def test_sentencebank_preview_sentence_fast_path_skips_verification(tmp_path: Path) -> None:
    verification_service = FakeSentenceVerificationService(
        results={
            "jeg er glad": SentenceVerificationResult(
                is_valid=False,
                errors=[SentenceVerificationErrorSpan(start=0, end=3, message="error")],
                corrected_text="jeg er glad",
                language="da",
            ),
        }
    )
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"jeg er glad": "i am happy"}),
        sentence_verification_service=verification_service,
    )

    preview = use_case.preview_sentence_search("jeg er glad", fast=True)

    assert preview.status == "preview"
    assert preview.is_valid is True
    assert preview.errors == []
    assert verification_service.calls == []


def test_sentencebank_batch_verification_persists_lemma_targets_for_lemma_form_tokens(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "kat hund": [
                NLPToken(text="kat", lemma="kat", pos="NOUN", morphology="Gender=Com|Number=Sing|Definite=Ind", is_punctuation=False),
                NLPToken(text="hund", lemma="hund", pos="NOUN", morphology="Gender=Com|Number=Sing|Definite=Ind", is_punctuation=False),
            ],
        }
    )
    verification_service = FakeVerificationService()
    wordbank_use_case = WordbankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        verification_service=verification_service,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    sentencebank_use_case.add_sentence("kat hund")
    _run_pending_sentence_token_verifications(
        db_path,
        nlp_adapter=nlp_adapter,
        verification_service=verification_service,
    )

    with sqlite3.connect(db_path) as conn:
        verified_lemma_targets = conn.execute(
            """
            SELECT COUNT(*)
            FROM wordbank_verification_records
            WHERE status = 'verified' AND stored_surface_form IS NULL
            """
        ).fetchone()[0]
        verified_hidden_surface_targets = conn.execute(
            """
            SELECT COUNT(*)
            FROM wordbank_verification_records
            WHERE status = 'verified' AND stored_surface_form IN ('kat', 'hund')
            """
        ).fetchone()[0]
    assert verified_lemma_targets == 2
    assert verified_hidden_surface_targets == 0


def test_sentencebank_batch_verification_persists_root_and_surface_targets_for_inflected_verbs(
    tmp_path: Path,
) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "er": [
                NLPToken(text="er", lemma="være", pos="AUX", morphology="Tense=Pres|VerbForm=Fin", is_punctuation=False),
            ],
        }
    )
    verification_service = FakeVerificationService()
    verification_service.batch_calls = []
    wordbank_use_case = WordbankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        verification_service=verification_service,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    sentencebank_use_case.add_sentence("er")
    _run_pending_sentence_token_verifications(
        db_path,
        nlp_adapter=nlp_adapter,
        verification_service=verification_service,
    )

    assert len(verification_service.batch_calls) == 1
    batch_payloads, batch_context = verification_service.batch_calls[0]
    assert batch_context == "er"
    assert {(payload.stored_lemma, payload.stored_surface_form, payload.meaning_id) for payload in batch_payloads} == {
        ("være", None, None),
        ("være", "er", None),
    }

    details = wordbank_use_case.get_lemma_details("være")
    assert details.verification is not None
    assert details.verification.status == "verified"
    surface_form = next((item for item in details.surface_forms if item.form == "er"), None)
    assert surface_form is not None
    assert surface_form.verification is not None
    assert surface_form.verification.status == "verified"
    assert details.categories == []


def test_sentencebank_batch_verification_assigns_categories_to_new_words(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "er": [
                NLPToken(text="er", lemma="være", pos="AUX", morphology="Tense=Pres|VerbForm=Fin", is_punctuation=False),
            ],
        }
    )
    verification_service = FakeVerificationService(categories=("Actions", "Grammar"))
    verification_service.batch_calls = []
    wordbank_use_case = WordbankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        verification_service=verification_service,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    sentencebank_use_case.add_sentence("er")
    _run_pending_sentence_token_verifications(
        db_path,
        nlp_adapter=nlp_adapter,
        verification_service=verification_service,
    )

    details = wordbank_use_case.get_lemma_details("være")
    assert details.categories == ["Actions", "Grammar"]
    surface_form = next((item for item in details.surface_forms if item.form == "er"), None)
    assert surface_form is not None


def test_sentencebank_batch_verification_persists_meaning_and_surface_targets_for_sectioned_verbs(
    tmp_path: Path,
) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "elsker": [
                NLPToken(text="elsker", lemma="elske", pos="VERB", morphology="Tense=Pres|VerbForm=Fin|Voice=Act", is_punctuation=False),
            ],
        }
    )
    verb_entry = _cor_local_entry(
        cor_id="COR.ELSKE.PRES.01",
        lemma="elske",
        gloss="love",
        form="elsker",
        lemma_idx=62001,
        pos_tag="VERB",
        morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
        gram_raw="vb.prs.akt",
    )
    lemma_entry = _cor_local_entry(
        cor_id="COR.ELSKE.INF.01",
        lemma="elske",
        gloss="love",
        form="elske",
        lemma_idx=62001,
        pos_tag="VERB",
        morphology="VerbForm=Inf|Voice=Act",
        gram_raw="vb.inf.akt",
    )
    verification_service = FakeVerificationService()
    verification_service.batch_calls = []
    wordbank_use_case = WordbankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        verification_service=verification_service,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"elsker": [verb_entry]},
            by_lemma_idx={62001: [lemma_entry, verb_entry]},
        ),
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    sentencebank_use_case.add_sentence("elsker")
    _run_pending_sentence_token_verifications(
        db_path,
        nlp_adapter=nlp_adapter,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"elsker": [verb_entry]},
            by_lemma_idx={62001: [lemma_entry, verb_entry]},
        ),
        verification_service=verification_service,
    )

    assert len(verification_service.batch_calls) == 1
    batch_payloads, batch_context = verification_service.batch_calls[0]
    assert batch_context == "elsker"

    details = wordbank_use_case.get_lemma_details("elske")
    assert len(details.meaning_sections) == 1
    meaning = details.meaning_sections[0]
    assert meaning.verification is not None
    assert meaning.verification.status == "verified"
    surface_form = next((item for item in meaning.surface_forms if item.form == "elsker"), None)
    assert surface_form is not None
    assert surface_form.verification is not None
    assert surface_form.verification.status == "verified"
    assert {(payload.stored_lemma, payload.stored_surface_form, payload.meaning_id) for payload in batch_payloads} == {
        ("elske", None, meaning.id),
        ("elske", "elsker", meaning.id),
    }


def test_sentencebank_add_sentence_falls_back_on_batch_failure(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "Huset er stort": [
                NLPToken(text="Huset", lemma="hus", pos="NOUN", morphology="Gender=Neut|Number=Sing|Definite=Def", is_punctuation=False),
                NLPToken(text="er", lemma="være", pos="AUX", morphology="Tense=Pres|VerbForm=Fin", is_punctuation=False),
                NLPToken(text="stort", lemma="stor", pos="ADJ", morphology="Degree=Pos|Gender=Neut|Number=Sing|Definite=Ind", is_punctuation=False),
            ],
        }
    )
    translation_service = FakeTranslationService({"Huset er stort": "the house is big"})

    class FailingBatchVerificationService:
        provider = "fake"
        reviewer_role = "Fake"
        batch_called = False

        def verify_word_entry(self, payload):
            return WordVerificationResult(verdict="verified", message="OK", composed_word_count=1)

        def verify_word_entries_batch(self, payloads, sentence_context=None):
            self.batch_called = True
            raise RuntimeError("Gemini overloaded")

        def classify_word_categories(self, payload):
            return WordCategoryClassificationResult(categories=())

    verification_service = FailingBatchVerificationService()
    wordbank_use_case = WordbankUseCase(
        db_path,
        translation_service=translation_service,
        nlp_adapter=nlp_adapter,
        verification_service=verification_service,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        translation_service=translation_service,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence("Huset er stort")

    assert inserted.status == "inserted"
    assert not verification_service.batch_called
    _run_pending_sentence_token_verifications(
        db_path,
        translation_service=translation_service,
        nlp_adapter=nlp_adapter,
        verification_service=verification_service,
    )
    assert verification_service.batch_called
    with sqlite3.connect(db_path) as conn:
        queued_verify_jobs = conn.execute(
            """
            SELECT COUNT(*)
            FROM wordbank_background_jobs
            WHERE job_type = 'verify_word' AND status = 'pending'
            """
        ).fetchone()[0]
        queued_verification_records = conn.execute(
            """
            SELECT COUNT(*)
            FROM wordbank_verification_records
            WHERE status = 'queued'
            """
        ).fetchone()[0]
    assert queued_verify_jobs >= 1
    assert queued_verification_records >= 1


def test_sentencebank_example_preview_uses_saved_meaning_context(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    gemini_service = FakeGeminiWordTranslationService({})
    wordbank_use_case = WordbankUseCase(
        db_path,
        gemini_word_translation_service=gemini_service,
    )
    added = wordbank_use_case.add_word(
        "bog",
        "bog",
        search_seed={
            "lemma": "bog",
            "surface": "bog",
            "cor_id": "COR.BOG.BOOK.LEM",
            "cor_lemma_idx": 123,
            "meaning_key": "book",
            "gloss": "book for reading",
            "english_translation": "book",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )
    assert added.meaning is not None
    gemini_service._example_overrides = {
        ("bog", added.meaning.id): ("Jeg læser en bog.", "I am reading a book.")
    }
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        wordbank_use_case=wordbank_use_case,
    )

    preview = sentencebank_use_case.generate_example_preview("bog", added.meaning.id)

    assert preview.source_text == "jeg læser en bog"
    assert preview.english_translation == "I am reading a book."
    payload = gemini_service.example_calls[0]
    assert payload.stored_lemma == "bog"
    assert payload.meaning_id == added.meaning.id
    assert payload.gloss == "book for reading"
    assert payload.english_translation == "book"
    assert payload.pos_tag == "NOUN"
    assert payload.morphology == "Gender=Com|Number=Sing|Definite=Ind"
    assert payload.cor_lemma_idx == 123


def test_generated_example_save_links_only_target_and_preserves_translation(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "Jeg læser en bog": [
                NLPToken(text="Jeg", lemma="jeg", pos="PRON", morphology=None, is_punctuation=False),
                NLPToken(text="læser", lemma="læse", pos="VERB", morphology=None, is_punctuation=False),
                NLPToken(text="en", lemma="en", pos="DET", morphology=None, is_punctuation=False),
                NLPToken(text="bog", lemma="bog", pos="NOUN", morphology=None, is_punctuation=False),
            ],
        }
    )
    translation_service = FakeTranslationService({"Jeg læser en bog": "provider should not be used"})
    wordbank_use_case = WordbankUseCase(
        db_path,
        translation_service=translation_service,
        nlp_adapter=nlp_adapter,
    )
    added = wordbank_use_case.add_word(
        "bog",
        "bog",
        search_seed={
            "lemma": "bog",
            "surface": "bog",
            "cor_id": "COR.BOG.BOOK.LEM",
            "cor_lemma_idx": 123,
            "meaning_key": "book",
            "gloss": "book",
            "english_translation": "book",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )
    assert added.meaning is not None
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        translation_service=translation_service,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence(
        "Jeg læser en bog",
        english_translation="I am reading a book.",
        token_persistence_mode="link_existing_only",
        target=type("Target", (), {"stored_lemma": "bog", "meaning_id": added.meaning.id})(),
    )

    assert inserted.english_translation == "I am reading a book."
    assert translation_service.calls == []
    assert [token.surface_form for token in inserted.tokens] == ["Jeg", "læser", "en", "bog"]
    assert [token.save_status for token in inserted.tokens] == ["unsaved", "unsaved", "unsaved", "saved"]
    assert inserted.tokens[1].lemma_candidate == "læse"
    assert inserted.tokens[1].pos_tag == "VERB"
    assert inserted.tokens[-1].stored_lemma == "bog"
    assert inserted.tokens[-1].meaning_id == added.meaning.id
    assert [item.lemma for item in wordbank_use_case.list_lemmas().items] == ["bog"]


def test_generated_example_unsaved_token_save_uses_normal_sentence_resolution_for_verbs(
    tmp_path: Path,
) -> None:
    db_path = _db_path(tmp_path)
    bjerg_entry = _cor_local_entry(
        cor_id="COR.BJERG.01",
        lemma="bjerg",
        gloss="mountain",
        form="bjerg",
        lemma_idx=61001,
        pos_tag="NOUN",
        morphology="Gender=Neut|Number=Sing|Definite=Ind",
        gram_raw="sb.et",
    )
    besteg_surface = _cor_local_entry(
        cor_id="COR.BESTIGE.PAST.01",
        lemma="bestige",
        gloss="climb",
        form="besteg",
        lemma_idx=61002,
        pos_tag="VERB",
        morphology="Tense=Past|VerbForm=Fin|Voice=Act",
        gram_raw="vb.præt.akt",
    )
    bestige_lemma = _cor_local_entry(
        cor_id="COR.BESTIGE.INF.01",
        lemma="bestige",
        gloss="climb",
        form="bestige",
        lemma_idx=61002,
        pos_tag="VERB",
        morphology="VerbForm=Inf|Voice=Act",
        gram_raw="vb.inf.akt",
    )
    wordbank_use_case = WordbankUseCase(
        db_path,
        translation_service=FakeTranslationService({"at bestige": "to climb"}),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"bjerg": [bjerg_entry], "besteg": [besteg_surface]},
            by_lemma_idx={61002: [bestige_lemma, besteg_surface]},
        ),
    )
    added = wordbank_use_case.add_word(
        "bjerg",
        "bjerg",
        search_seed={
            "lemma": "bjerg",
            "surface": "bjerg",
            "cor_id": "COR.BJERG.01",
            "cor_lemma_idx": 61001,
            "meaning_key": "mountain",
            "gloss": "mountain",
            "english_translation": "mountain",
            "pos_tag": "NOUN",
            "morphology": "Gender=Neut|Number=Sing|Definite=Ind",
        },
    )
    assert added.meaning is not None
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        wordbank_use_case=wordbank_use_case,
    )
    inserted = sentencebank_use_case.add_sentence(
        "vi besteg et højt bjerg",
        english_translation="we climbed a high mountain",
        token_persistence_mode="link_existing_only",
        target=type("Target", (), {"stored_lemma": "bjerg", "meaning_id": added.meaning.id})(),
    )
    besteg_token = next(token for token in inserted.tokens if token.surface_form == "besteg")
    wrong_lexeme_id, _inserted = wordbank_use_case.runtime.repository.insert_or_load_lexeme(
        stored_lemma="besteg",
        translation="climber",
        provider="test",
        pos_tag="VERB",
        morphology="Tense=Past|VerbForm=Fin|Voice=Act",
        source="manual",
    )
    wordbank_use_case.runtime.repository.insert_or_update_surface_form(
        lexeme_id=wrong_lexeme_id,
        meaning_id=None,
        form="besteg",
        pos_tag="VERB",
        morphology="Tense=Past|VerbForm=Fin|Voice=Act",
    )

    updated = sentencebank_use_case.save_sentence_token(inserted.id, besteg_token.token_index)

    assert updated.saved_token.surface_form == "besteg"
    assert updated.saved_token.stored_lemma == "bestige"
    assert updated.saved_token.meaning_id is not None
    details = wordbank_use_case.get_lemma_details("bestige")
    assert details.is_sectioned is True
    assert details.meaning_sections[0].surface_forms[0].form == "besteg"


def test_generated_example_duplicate_is_idempotent(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    wordbank_use_case = WordbankUseCase(db_path)
    added = wordbank_use_case.add_word(
        "bog",
        "bog",
        search_seed={
            "lemma": "bog",
            "surface": "bog",
            "meaning_key": "book",
            "gloss": "book",
            "english_translation": "book",
            "pos_tag": "NOUN",
            "morphology": None,
        },
    )
    assert added.meaning is not None
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        wordbank_use_case=wordbank_use_case,
    )
    target = type("Target", (), {"stored_lemma": "bog", "meaning_id": added.meaning.id})()

    first = sentencebank_use_case.add_sentence(
        "Her er en bog",
        english_translation="Here is a book.",
        token_persistence_mode="link_existing_only",
        target=target,
    )
    second = sentencebank_use_case.add_sentence(
        "  her   er en bog ",
        english_translation="Here is a book.",
        token_persistence_mode="link_existing_only",
        target=target,
    )

    assert first.status == "inserted"
    assert second.status == "exists"
    assert second.id == first.id
