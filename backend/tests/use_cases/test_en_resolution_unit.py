from __future__ import annotations

from app.services.cor import COREntry
from app.services.en_local import ENLocalEntry, ENLocalFormMatch
from app.services.use_cases.wordbank.collaborators.cor_resolution import resolve_query
from app.services.use_cases.wordbank.collaborators.en_resolution import resolve_en_query
from tests.helpers.factories import _db_path
from tests.helpers.fakes import FakeTranslationService


class _StubENLocalLexiconService:
    def __init__(
        self,
        *,
        matches: list[ENLocalFormMatch],
        senses_by_key: dict[tuple[str, str], list[ENLocalEntry]],
    ) -> None:
        self._matches = matches
        self._senses_by_key = senses_by_key
        self.lookup_form_calls: list[str] = []
        self.lookup_lemma_senses_calls: list[tuple[str, str | None]] = []

    def lookup_form(self, value: str) -> list[ENLocalFormMatch]:
        self.lookup_form_calls.append(value)
        return list(self._matches)

    def has_form(self, value: str) -> bool:
        normalized = " ".join(value.strip().lower().split())
        return any(match.form.strip().lower() == normalized for match in self._matches)

    def lookup_lemma_senses(self, lemma: str, pos_ud: str | None = None) -> list[ENLocalEntry]:
        self.lookup_lemma_senses_calls.append((lemma, pos_ud))
        return list(self._senses_by_key.get((lemma, pos_ud or ""), []))


class _StubENGeminiTranslationService:
    def __init__(self, mapping: dict[tuple[str, str | None, str | None], str | None]) -> None:
        self._mapping = mapping
        self.calls: list[tuple[str, str | None, str | None]] = []

    def translate_english_lemma(
        self, *, lemma: str, pos_ud: str | None, gloss: str | None
    ) -> str | None:
        key = (lemma, pos_ud, gloss)
        self.calls.append(key)
        return self._mapping.get(key)


class _StubTranslationCollaborator:
    def lookup_translation(self, source_word: str) -> str | None:
        return None

    def lookup_reverse_translation(self, source_word: str) -> str | None:
        return None

    def detect_word_language(self, source_word: str, *, cor_entries_lookup=None):
        return type("DetectedLanguage", (), {"language": "ambiguous", "confidence": 0.5})()

    def is_likely_english_word(self, source_word: str) -> bool:
        return True

    def normalize_comparable(self, value: str | None) -> str:
        return " ".join((value or "").strip().lower().split())


class _StubNLPCollaborator:
    def extract_pos_and_morphology(
        self,
        value: str,
        *,
        preferred_pos_tag: str | None = None,
    ) -> tuple[str | None, str | None]:
        return preferred_pos_tag, None


def _sense(*, lemma: str, pos_ud: str, sense_idx: int, gloss: str, examples: list[str] | None = None) -> ENLocalEntry:
    return ENLocalEntry(
        en_id=f"EN.{lemma}.{pos_ud}.{sense_idx:02d}",
        lemma=lemma,
        pos_raw=pos_ud.lower(),
        pos_ud=pos_ud,
        sense_idx=sense_idx,
        gloss=gloss,
        examples=list(examples or []),
        ipa=None,
    )


def test_resolve_en_query_orders_groups_by_pos_and_caps_senses_per_group() -> None:
    lexicon = _StubENLocalLexiconService(
        matches=[
            ENLocalFormMatch(form="light", lemma="light", pos_ud="ADV", tags=[]),
            ENLocalFormMatch(form="light", lemma="light", pos_ud="VERB", tags=[]),
            ENLocalFormMatch(form="light", lemma="light", pos_ud="NOUN", tags=[]),
        ],
        senses_by_key={
            ("light", "NOUN"): [
                _sense(lemma="light", pos_ud="NOUN", sense_idx=index, gloss=f"noun gloss {index}")
                for index in range(6)
            ],
            ("light", "VERB"): [_sense(lemma="light", pos_ud="VERB", sense_idx=0, gloss="ignite")],
            ("light", "ADV"): [_sense(lemma="light", pos_ud="ADV", sense_idx=0, gloss="lightly")],
        },
    )

    response = resolve_en_query(
        normalized_query="light",
        en_local_lexicon_service=lexicon,
        en_gemini_translation_service=None,
        translation_service=None,
        include_translations=False,
    )

    assert response.classification == "new"
    assert response.query_language == "en"
    assert response.query_language_confidence == 0.95
    assert response.query_surface == "light"
    assert response.query_lemma == "light"
    assert response.query_pos_tag is None
    assert response.resolved_surface == "light"
    assert response.resolved_lemma == "light"
    assert response.en_to_da_translation is None
    assert [(group.pos_ud, len(group.senses)) for group in response.en_pos_groups] == [
        ("NOUN", 5),
        ("VERB", 1),
        ("ADV", 1),
    ]
    assert [sense.sense_idx for sense in response.en_pos_groups[0].senses] == [0, 1, 2, 3, 4]


def test_resolve_en_query_reuses_translation_cache_and_falls_back_to_provider() -> None:
    lexicon = _StubENLocalLexiconService(
        matches=[
            ENLocalFormMatch(form="books", lemma="book", pos_ud="VERB", tags=["third-person singular"]),
            ENLocalFormMatch(form="books", lemma="book", pos_ud="NOUN", tags=["plural"]),
            ENLocalFormMatch(form="books", lemma="book", pos_ud="NOUN", tags=[]),
        ],
        senses_by_key={
            ("book", "NOUN"): [
                _sense(
                    lemma="book",
                    pos_ud="NOUN",
                    sense_idx=0,
                    gloss="printed work",
                    examples=["this book is long"],
                ),
                _sense(
                    lemma="book",
                    pos_ud="NOUN",
                    sense_idx=1,
                    gloss="printed work",
                    examples=["that book is short"],
                ),
            ],
            ("book", "VERB"): [
                _sense(lemma="book", pos_ud="VERB", sense_idx=0, gloss="reserve in advance")
            ],
        },
    )
    gemini = _StubENGeminiTranslationService(
        {
            ("book", "NOUN", "printed work"): None,
            ("book", "VERB", "reserve in advance"): "reservere",
        }
    )
    translation_service = FakeTranslationService({"book": "bog"})

    response = resolve_en_query(
        normalized_query="books",
        en_local_lexicon_service=lexicon,
        en_gemini_translation_service=gemini,
        translation_service=translation_service,
        include_translations=True,
    )

    assert response.query_lemma == "book"
    assert response.query_pos_tag == "NOUN"
    assert response.resolved_surface == "bog"
    assert response.resolved_lemma == "bog"
    assert response.en_to_da_translation == "bog"
    assert response.en_to_da_lemma == "bog"
    assert response.en_to_da_pos_tag == "NOUN"
    assert [(group.pos_ud, group.danish_translation) for group in response.en_pos_groups] == [
        ("NOUN", "bog"),
        ("VERB", "reservere"),
    ]
    assert [sense.danish_translation for sense in response.en_pos_groups[0].senses] == ["bog", "bog"]
    assert gemini.calls == [
        ("book", "NOUN", "printed work"),
        ("book", "VERB", "reserve in advance"),
    ]
    assert translation_service.calls == ["book"]


def test_resolve_en_query_discards_self_translated_echoes() -> None:
    lexicon = _StubENLocalLexiconService(
        matches=[ENLocalFormMatch(form="notebook", lemma="notebook", pos_ud="NOUN", tags=[])],
        senses_by_key={
            ("notebook", "NOUN"): [
                _sense(lemma="notebook", pos_ud="NOUN", sense_idx=0, gloss="bound book for notes")
            ],
        },
    )
    gemini = _StubENGeminiTranslationService(
        {("notebook", "NOUN", "bound book for notes"): " notebook "}
    )

    response = resolve_en_query(
        normalized_query="notebook",
        en_local_lexicon_service=lexicon,
        en_gemini_translation_service=gemini,
        translation_service=None,
        include_translations=True,
    )

    assert response.resolved_surface == "notebook"
    assert response.resolved_lemma == "notebook"
    assert response.en_to_da_translation is None
    assert response.en_pos_groups[0].danish_translation is None
    assert response.en_pos_groups[0].senses[0].danish_translation is None


def test_resolve_query_keeps_danish_flow_and_attaches_english_groups_when_both_exist(tmp_path) -> None:
    db_path = _db_path(tmp_path)
    en_lexicon = _StubENLocalLexiconService(
        matches=[ENLocalFormMatch(form="gift", lemma="gift", pos_ud="NOUN", tags=[])],
        senses_by_key={
            ("gift", "NOUN"): [
                _sense(lemma="gift", pos_ud="NOUN", sense_idx=0, gloss="present")
            ],
        },
    )
    gemini = _StubENGeminiTranslationService(
        {("gift", "NOUN", "present"): "gave"}
    )

    response = resolve_query(
        db_path=db_path,
        translation=_StubTranslationCollaborator(),
        nlp=_StubNLPCollaborator(),
        cor_entries_lookup=lambda value: [
            COREntry(
                cor_id="COR.GIFT.NOUN",
                lemma="gift",
                full_form="gift",
                ordklasse="sb",
                grammatical_function="sb.fk.sg.ubest",
                glosse="poison",
                norm_status="N",
                pos_tag="NOUN",
                morphology="Gender=Com|Number=Sing|Definite=Ind",
            ),
        ] if value == "gift" else [],
        query_text="gift",
        include_translations=False,
        include_language_detection=False,
        en_local_lexicon_service=en_lexicon,
        en_gemini_translation_service=gemini,
        translation_service=None,
    )

    assert response.classification == "new"
    assert response.query_surface == "gift"
    assert response.query_lemma == "gift"
    assert response.en_pos_groups
    assert response.en_pos_groups[0].lemma == "gift"
    assert response.en_pos_groups[0].pos_ud == "NOUN"
