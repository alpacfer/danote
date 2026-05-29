from __future__ import annotations

from pathlib import Path

from app.services.cor_local import CORLocalEntry
from app.services.gemini_sense_discovery import DiscoveredSense, DiscoveredSenseSet
from app.services.use_cases.wordbank import WordbankUseCase
from tests.helpers.factories import _db_path
from tests.helpers.fakes import (
    FakeCORLocalLexiconService,
    FakeGeminiWordTranslationService,
    FakeTranslationService,
)


class _LaveSenseGeminiService(FakeGeminiWordTranslationService):
    def __init__(self) -> None:
        super().__init__({})

    def discover_senses(self, payload):
        return DiscoveredSenseSet(
            senses=[
                DiscoveredSense(
                    meaning_key="make-create",
                    english_translation="to make",
                    gloss="fremstille eller skabe noget",
                    english_gloss="to produce or create something",
                    cor_lemma_idx=payload.cor_candidates[0].lemma_idx if payload.cor_candidates else None,
                ),
                DiscoveredSense(
                    meaning_key="do-perform",
                    english_translation="to do",
                    gloss="udføre en handling eller opgave",
                    english_gloss="to perform an action or task",
                    cor_lemma_idx=payload.cor_candidates[0].lemma_idx if payload.cor_candidates else None,
                ),
                DiscoveredSense(
                    meaning_key="prepare-food",
                    english_translation="to prepare",
                    gloss="tilberede mad",
                    english_gloss="to cook or get food ready",
                    cor_lemma_idx=payload.cor_candidates[0].lemma_idx if payload.cor_candidates else None,
                ),
            ]
        )


class _GoSenseGeminiService(FakeGeminiWordTranslationService):
    def __init__(self) -> None:
        super().__init__({})

    def discover_senses(self, payload):
        return DiscoveredSenseSet(
            senses=[
                DiscoveredSense(
                    meaning_key="walk",
                    english_translation="to walk",
                    gloss="bevæge sig til fods",
                    english_gloss="move on foot",
                    cor_lemma_idx=payload.cor_candidates[0].lemma_idx if payload.cor_candidates else None,
                ),
                DiscoveredSense(
                    meaning_key="leave",
                    english_translation="to leave",
                    gloss="forlade et sted",
                    english_gloss="depart from a place",
                    cor_lemma_idx=payload.cor_candidates[0].lemma_idx if payload.cor_candidates else None,
                ),
            ]
        )


def test_cor_form_saved_state_attaches_to_matching_sense_only(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={"lave": [_lave_cor_entry()]},
        by_lemma_idx={30755: [_lave_cor_entry()]},
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService({"at lave": "to make"}),
        gemini_word_translation_service=_LaveSenseGeminiService(),
    )
    saved = use_case.add_word(
        "lave",
        "lave",
        search_seed={
            "lemma": "lave",
            "surface": "lave",
            "cor_id": "COR.30755.200.01",
            "cor_lemma_idx": 30755,
            "dictionary_status": "cor",
            "meaning_key": "make-create",
            "gloss": "fremstille eller skabe noget",
            "english_gloss": "to produce or create something",
            "english_translation": "to make",
            "pos_tag": "VERB",
        },
    )

    response = use_case.search_cor_form("lave", limit=100)

    assert saved.meaning is not None
    assert [
        (group.variants[0].meaning_key, group.variants[0].saved_meaning_id)
        for group in response.groups
    ] == [
        ("make-create", saved.meaning.id),
        ("do-perform", None),
        ("prepare-food", None),
    ]


def test_cor_form_collapses_duplicate_rows_for_same_sense_identity(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={"gå": [_go_cor_entry("COR.30234.200.01", 200), _go_cor_entry("COR.30234.209.01", 209)]},
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService({"at gå": "to walk"}),
        gemini_word_translation_service=_GoSenseGeminiService(),
    )

    response = use_case.search_cor_form("gå", limit=100)

    assert [
        (group.variants[0].meaning_key, group.variants[0].cor_id)
        for group in response.groups
    ] == [
        ("walk", "COR.30234.200.01"),
        ("leave", "COR.30234.200.01"),
    ]


def _lave_cor_entry() -> CORLocalEntry:
    return CORLocalEntry(
        cor_id="COR.30755.200.01",
        lemma="lave",
        gloss="fremstille eller skabe noget",
        gram_raw="vb.inf.akt",
        form="lave",
        norm="N",
        lemma_idx=30755,
        gram_code=200,
        variation=1,
        pos_tag="VERB",
        morphology="Voice=Act",
        features={"Voice": "Act"},
        extra_tags=[],
    )


def _go_cor_entry(cor_id: str, gram_code: int) -> CORLocalEntry:
    return CORLocalEntry(
        cor_id=cor_id,
        lemma="gå",
        gloss="bevæge sig til fods",
        gram_raw="vb.inf.akt" if gram_code == 200 else "vb.imp",
        form="gå",
        norm="N",
        lemma_idx=30234,
        gram_code=gram_code,
        variation=1,
        pos_tag="VERB",
        morphology="VerbForm=Inf|Voice=Act" if gram_code == 200 else "Mood=Imp|VerbForm=Fin",
        features={"VerbForm": "Inf", "Voice": "Act"} if gram_code == 200 else {"Mood": "Imp", "VerbForm": "Fin"},
        extra_tags=[],
    )
