from __future__ import annotations

from pathlib import Path
import pytest

from app.nlp.adapter import NLPToken
from app.services.use_cases.sentencebank import SentencebankUseCase
from app.services.use_cases.wordbank import WordbankUseCase
from app.services.verification import WordVerificationResult, WordCategoryClassificationResult
from tests.helpers.factories import _cor_local_entry, _db_path
from tests.helpers.fakes import (
    FakeCORLocalLexiconService,
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

    def translate_word(self, _payload) -> str | None:
        return None

    def select_meaning_section(self, payload) -> int | None:
        self.calls.append(payload)
        return self._selected_id


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
    assert inserted.english_translation == "I like it"
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

    assert gemini_service.calls
    assert gemini_service.calls[0].sentence_context == "Min mor kommer"
    assert inserted.tokens[0].meaning_id is not None
    assert inserted.tokens[0].gloss == "person"


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

    assert gemini_service.calls
    assert len(gemini_service.calls[0].meaning_candidates) == 3
    assert {item.lemma for item in gemini_service.calls[0].meaning_candidates} == {"bad", "bade", "bede"}
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


class FakeVerificationService:
    provider = "fake_verification"
    reviewer_role = "Fake Reviewer"
    batch_calls: list[tuple] = []

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
        return WordCategoryClassificationResult(categories=())


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
    assert len(verification_service.batch_calls) == 1
    batch_payloads, batch_context = verification_service.batch_calls[0]
    assert batch_context == "Huset er stort"
    assert len(batch_payloads) >= 1


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
    assert verification_service.batch_called
