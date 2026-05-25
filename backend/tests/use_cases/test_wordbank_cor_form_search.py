from __future__ import annotations

from pathlib import Path

from app.services.cor import COREntry
from app.services.cor_local import CORLocalEntry
from app.services.gemini_sense_discovery import DiscoveredSense, DiscoveredSenseSet
from app.services.use_cases.wordbank import WordbankUseCase
from tests.helpers.factories import _db_path
from tests.helpers.fakes import (
    FakeCORLexiconService,
    FakeCORLocalLexiconService,
    FakeGeminiWordTranslationService,
    FakeTranslationService,
)


class _NokSenseGeminiService(FakeGeminiWordTranslationService):
    def __init__(self) -> None:
        super().__init__({})
        self.discover_sense_calls = []

    def discover_senses(self, payload):
        self.discover_sense_calls.append(payload)
        return DiscoveredSenseSet(
            senses=[
                DiscoveredSense(
                    meaning_key="probably",
                    english_translation="probably",
                    gloss="sandsynligvis",
                    english_gloss="in all likelihood",
                    cor_lemma_idx=payload.cor_candidates[0].lemma_idx if payload.cor_candidates else None,
                )
            ]
        )


def test_wordbank_search_cor_form_uses_static_pronoun_without_cor_or_translation(tmp_path: Path) -> None:
    translation_service = FakeTranslationService({"du": "provider should not be used"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=translation_service,
        cor_local_lexicon_service=None,
    )

    response = use_case.search_cor_form("du")

    assert translation_service.calls == []
    assert response.groups[0].lemma == "du"
    assert response.groups[0].variants[0].lemma_translation == "you"
    assert response.groups[0].variants[0].saveable_translation == "you"
    assert response.groups[0].variants[0].pos_tag == "PRON"


def test_wordbank_search_en_form_uses_static_pronoun_without_en_lexicon(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    response = use_case.search_en_form("you")

    assert response.groups[0].danish_translation == "du"
    assert response.groups[0].pos_ud == "PRON"
    assert response.groups[0].senses[0].danish_translation == "du"


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
                "at lære": "learn",
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


def test_wordbank_search_cor_form_collapses_duplicate_same_translation_rows(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "tøj": [
                CORLocalEntry(
                    cor_id="COR.TOEJ.FABRIC",
                    lemma="tøj",
                    gloss="vævet stykke stof, klæde",
                    gram_raw="sb.itk.sg.ubest",
                    form="tøj",
                    norm="N",
                    lemma_idx=47212,
                    gram_code=120,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Neut|Number=Sing|Definite=Ind",
                    features={"Gender": "Neut", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.TOEJ.CLOTHING",
                    lemma="tøj",
                    gloss="klæder; ting af stof",
                    gram_raw="sb.itk.sg.ubest",
                    form="tøj",
                    norm="N",
                    lemma_idx=48541,
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
        translation_service=FakeTranslationService({"et tøj": "garment", "tøj": "garment"}),
    )

    response = use_case.search_cor_form("tøj", limit=100)

    assert len(response.groups) == 1
    assert response.groups[0].variants[0].cor_id == "COR.TOEJ.FABRIC"

def test_wordbank_search_cor_form_uses_frame_identity_for_homograph_lemma_translations(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "lærer": [
                CORLocalEntry(
                    cor_id="COR.100.203.01",
                    lemma="lære",
                    gloss=None,
                    gram_raw="vb.præs.akt",
                    form="lærer",
                    norm="N",
                    lemma_idx=100,
                    gram_code=203,
                    variation=1,
                    pos_tag="VERB",
                    morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
                    features={"Tense": "Pres", "VerbForm": "Fin", "Voice": "Act"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.200.110.01",
                    lemma="lære",
                    gloss=None,
                    gram_raw="sb.fk.sg.ubest",
                    form="lærer",
                    norm="N",
                    lemma_idx=200,
                    gram_code=110,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Ind",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
            ]
        }
    )
    translation_service = FakeTranslationService(
        {
            "at lære": "learn",
            "en lære": "a doctrine",
        }
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=translation_service,
    )

    response = use_case.search_cor_form("lærer", limit=100)
    by_pos = {group.pos_tag: group.variants[0].lemma_translation for group in response.groups}

    assert by_pos["VERB"] == "to learn"
    assert by_pos["NOUN"] == "doctrine"
    assert "at lære" in translation_service.calls
    assert "en lære" in translation_service.calls


def test_wordbank_search_cor_form_attaches_saved_state_to_matching_pos_only(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "nok": [
                CORLocalEntry(
                    cor_id="COR.NOK.ADV",
                    lemma="nok",
                    gloss="sandsynligvis",
                    gram_raw="adv",
                    form="nok",
                    norm="N",
                    lemma_idx=10200,
                    gram_code=900,
                    variation=1,
                    pos_tag="ADV",
                    morphology=None,
                    features={},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.NOK.ADJ",
                    lemma="nok",
                    gloss="sandsynligvis",
                    gram_raw="adj.sg.ubest",
                    form="nok",
                    norm="N",
                    lemma_idx=17872,
                    gram_code=300,
                    variation=1,
                    pos_tag="ADJ",
                    morphology="Number=Sing|Definite=Ind|Gender=Com",
                    features={"Number": "Sing", "Definite": "Ind", "Gender": "Com"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.NOK.NOUN",
                    lemma="nok",
                    gloss="sandsynligvis",
                    gram_raw="sb.fk.sg.ubest",
                    form="nok",
                    norm="N",
                    lemma_idx=45928,
                    gram_code=110,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Ind",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
            ]
        },
        by_lemma_idx={
            10200: [
                CORLocalEntry(
                    cor_id="COR.NOK.ADV",
                    lemma="nok",
                    gloss="sandsynligvis",
                    gram_raw="adv",
                    form="nok",
                    norm="N",
                    lemma_idx=10200,
                    gram_code=900,
                    variation=1,
                    pos_tag="ADV",
                    morphology=None,
                    features={},
                    extra_tags=[],
                )
            ]
        },
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_lexicon_service=FakeCORLexiconService(
            {
                "nok": [
                    COREntry(
                        cor_id="COR.NOK.ADV",
                        lemma="nok",
                        full_form="nok",
                        ordklasse="adv",
                        grammatical_function=None,
                        glosse="sandsynligvis",
                        norm_status="N",
                        pos_tag="ADV",
                        morphology=None,
                    ),
                    COREntry(
                        cor_id="COR.NOK.ADJ",
                        lemma="nok",
                        full_form="nok",
                        ordklasse="adj",
                        grammatical_function="sg.ubest",
                        glosse="sandsynligvis",
                        norm_status="N",
                        pos_tag="ADJ",
                        morphology="Number=Sing|Definite=Ind|Gender=Com",
                    ),
                    COREntry(
                        cor_id="COR.NOK.NOUN",
                        lemma="nok",
                        full_form="nok",
                        ordklasse="sb",
                        grammatical_function="fk.sg.ubest",
                        glosse="sandsynligvis",
                        norm_status="N",
                        pos_tag="NOUN",
                        morphology="Gender=Com|Number=Sing|Definite=Ind",
                    ),
                ]
            }
        ),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService({"sandsynligvis": "probably"}),
        gemini_word_translation_service=_NokSenseGeminiService(),
    )
    saved = use_case.add_word(
        "nok",
        "nok",
        search_seed={
            "lemma": "nok",
            "surface": "nok",
            "cor_id": "COR.NOK.ADV",
            "cor_lemma_idx": 10200,
            "dictionary_status": "cor",
            "meaning_key": "probably",
            "gloss": "sandsynligvis",
            "english_gloss": "in all likelihood",
            "english_translation": "probably",
            "pos_tag": "ADV",
        },
    )

    response = use_case.search_cor_form("nok", limit=100)
    saved_by_pos = {
        group.pos_tag: group.variants[0].saved_meaning_id
        for group in response.groups
    }
    actions_by_pos = {
        action.pos_tag: action
        for action in use_case.resolve_query("nok").word_actions
        if action.meaning_key == "probably"
    }

    assert saved.meaning is not None
    assert saved_by_pos == {
        "ADV": saved.meaning.id,
        "ADJ": None,
        "NOUN": None,
    }
    assert actions_by_pos["ADV"].action_type == "open_wordbank"
    assert actions_by_pos["ADV"].saved_meaning_id == saved.meaning.id
    assert actions_by_pos["ADJ"].action_type == "add_as_new"
    assert actions_by_pos["ADJ"].saved_meaning_id is None
    assert actions_by_pos["NOUN"].action_type == "add_as_new"
    assert actions_by_pos["NOUN"].saved_meaning_id is None


def test_search_seed_save_keeps_same_meaning_key_separate_across_pos(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    use_case.add_word(
        "nok",
        "nok",
        search_seed={
            "lemma": "nok",
            "surface": "nok",
            "cor_id": "COR.NOK.ADV",
            "cor_lemma_idx": 10200,
            "dictionary_status": "cor",
            "meaning_key": "probably",
            "gloss": "sandsynligvis",
            "english_translation": "probably",
            "pos_tag": "ADV",
        },
    )
    use_case.add_word(
        "nok",
        "nok",
        search_seed={
            "lemma": "nok",
            "surface": "nok",
            "cor_id": "COR.NOK.ADJ",
            "cor_lemma_idx": 17872,
            "dictionary_status": "cor",
            "meaning_key": "probably",
            "gloss": "sandsynligvis",
            "english_translation": "probably",
            "pos_tag": "ADJ",
            "morphology": "Number=Sing|Definite=Ind|Gender=Com",
        },
    )

    details = use_case.get_lemma_details("nok")

    assert [
        (section.meaning_key, section.pos_tag, section.english_translation)
        for section in details.meaning_sections
    ] == [
        ("probably", "ADV", "probably"),
        ("probably", "ADJ", "probably"),
    ]


def test_search_seed_save_persists_same_sense_alternative_translations(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    use_case.add_word(
        "nok",
        "nok",
        search_seed={
            "lemma": "nok",
            "surface": "nok",
            "cor_id": "COR.NOK.ADV",
            "cor_lemma_idx": 10200,
            "dictionary_status": "cor",
            "meaning_key": "enough",
            "gloss": "i tilstrækkelig grad",
            "english_gloss": "to a sufficient degree",
            "english_translation": "enough",
            "alternative_translations": ["sufficiently", "adequately", "enough"],
            "pos_tag": "ADV",
        },
    )

    details = use_case.get_lemma_details("nok")

    assert details.meaning_sections[0].english_translation == "enough"
    assert details.meaning_sections[0].additional_translations == ["sufficiently", "adequately"]


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

    response = use_case.search_cor_form("glas", limit=100, include_translations=False)

    assert len(response.groups) == 1
    assert len(response.groups[0].variants) == 1
    assert response.groups[0].variants[0].gram_raw == "sb.itk.sg.ubest | sb.itk.pl.ubest"


def test_wordbank_search_cor_form_generates_non_cor_result_for_sikkerhedszone(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(by_form={"sikkerhedszone": []})
    gemini = FakeGeminiWordTranslationService(
        {},
        non_cor_generation_overrides={
            ("sikkerhedszone", "sikkerhedszone", None): {
                "lemma": "sikkerhedszone",
                "english_translation": "security zone",
                "meaning_key": "security zone",
                "gloss": "security zone",
                "pos_tag": "NOUN",
                "morphology": "Gender=Com|Number=Sing|Definite=Ind",
                "surface_pos_tag": "NOUN",
                "surface_morphology": "Gender=Com|Number=Sing|Definite=Ind",
            },
        },
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        gemini_word_translation_service=gemini,
    )

    response = use_case.search_cor_form("sikkerhedszone", limit=100)

    assert gemini.non_cor_generation_calls == [("sikkerhedszone", "sikkerhedszone", None)]
    assert response.did_you_mean is None
    assert response.groups[0].lemma == "sikkerhedszone"
    variant = response.groups[0].variants[0]
    assert variant.dictionary_status == "generated_non_cor"
    assert variant.cor_id == "GENERATED.NON_COR.SIKKERHEDSZONE"
    assert variant.form == "sikkerhedszone"
    assert variant.lemma_translation == "security zone"
    assert variant.saveable_translation == "security zone"
    assert variant.pos_tag == "NOUN"
    assert variant.morphology == "Gender=Com|Number=Sing|Definite=Ind"


def test_wordbank_search_cor_form_generates_non_cor_result_for_noedaabning(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(by_form={"nødåbning": []})
    gemini = FakeGeminiWordTranslationService(
        {},
        non_cor_generation_overrides={
            ("nødåbning", "nødåbning", None): {
                "lemma": "nødåbning",
                "english_translation": "emergency opening",
                "meaning_key": "emergency opening",
                "gloss": "emergency opening",
                "pos_tag": "NOUN",
                "morphology": "Gender=Com|Number=Sing|Definite=Ind",
                "surface_pos_tag": "NOUN",
                "surface_morphology": "Gender=Com|Number=Sing|Definite=Ind",
            },
        },
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        gemini_word_translation_service=gemini,
    )

    response = use_case.search_cor_form("nødåbning", limit=100)

    assert response.groups[0].lemma == "nødåbning"
    assert response.groups[0].variants[0].dictionary_status == "generated_non_cor"
    assert response.groups[0].variants[0].saveable_translation == "emergency opening"


def test_wordbank_search_cor_form_skips_non_cor_generation_for_fast_lookup(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(by_form={"sikkerhedszone": []})
    gemini = FakeGeminiWordTranslationService(
        {},
        non_cor_generation_overrides={
            ("sikkerhedszone", "sikkerhedszone", None): {
                "lemma": "sikkerhedszone",
                "english_translation": "security zone",
            },
        },
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        gemini_word_translation_service=gemini,
    )

    response = use_case.search_cor_form("sikkerhedszone", limit=100, include_translations=False)

    assert response.groups == []
    assert gemini.non_cor_generation_calls == []

class _StubENGeminiForMatchFilter:
    def __init__(self, decisions: dict[str, bool]) -> None:
        self._decisions = decisions
        self.calls: list[tuple[str, list[dict[str, object]], str | None]] = []

    def select_translation_matches(
        self,
        *,
        query: str,
        choices: list[dict[str, object]],
        en_pos_ud: str | None = None,
    ) -> dict[str, bool]:
        self.calls.append((query, choices, en_pos_ud))
        return dict(self._decisions)

    # Other methods on ENGeminiTranslationService — not exercised here.
    def translate_english_lemma(self, *, lemma: str, pos_ud: str | None, gloss: str | None) -> str | None:
        return None

    def describe_translation_choices(self, *, query: str, choices: list[dict[str, object]]) -> dict[str, str]:
        return {}


class _BatchStubENGeminiForMatchFilter(_StubENGeminiForMatchFilter):
    def __init__(self, decisions: dict[str, bool]) -> None:
        super().__init__({})
        self._batch_decisions = decisions
        self.batch_calls: list[tuple[str, list[dict[str, object]], str | None]] = []

    def select_translation_matches_batch(
        self,
        *,
        query: str,
        en_pos_ud: str | None,
        lemma_choices: list[dict[str, object]],
    ) -> dict[str, bool]:
        self.batch_calls.append((query, lemma_choices, en_pos_ud))
        return dict(self._batch_decisions)


def _bord_homograph_lookup() -> dict[str, list[CORLocalEntry]]:
    return {
        "bord": [
            CORLocalEntry(
                cor_id="COR.44636.120.01",
                lemma="bord",
                gloss="et møbel",
                gram_raw="sb.itk.sg.ubest",
                form="bord",
                norm="N",
                lemma_idx=44636,
                gram_code=120,
                variation=1,
                pos_tag="NOUN",
                morphology="Gender=Neut|Number=Sing|Definite=Ind",
                features={"Gender": "Neut", "Number": "Sing", "Definite": "Ind"},
                extra_tags=[],
            ),
            CORLocalEntry(
                cor_id="COR.46065.120.01",
                lemma="bord",
                gloss="planke på skib el. båd",
                gram_raw="sb.itk.sg.ubest",
                form="bord",
                norm="N",
                lemma_idx=46065,
                gram_code=120,
                variation=1,
                pos_tag="NOUN",
                morphology="Gender=Neut|Number=Sing|Definite=Ind",
                features={"Gender": "Neut", "Number": "Sing", "Definite": "Ind"},
                extra_tags=[],
            ),
        ]
    }


def test_wordbank_search_cor_form_filters_competing_senses_via_en_query(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(by_form=_bord_homograph_lookup())
    gemini = _StubENGeminiForMatchFilter({"0": True, "1": False})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        en_gemini_translation_service=gemini,
    )

    response = use_case.search_cor_form(
        "bord",
        limit=100,
        include_translations=False,
        en_query="table",
    )

    assert len(response.groups) == 1
    assert response.groups[0].gloss == "et møbel"
    assert response.groups[0].variants[0].cor_id == "COR.44636.120.01"
    assert len(gemini.calls) == 1
    assert gemini.calls[0][0] == "table"
    assert {choice["danish_gloss"] for choice in gemini.calls[0][1]} == {
        "et møbel",
        "planke på skib el. båd",
    }


def test_wordbank_search_cor_form_passes_en_pos_to_gemini(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(by_form=_bord_homograph_lookup())
    gemini = _StubENGeminiForMatchFilter({"0": True, "1": False})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        en_gemini_translation_service=gemini,
    )

    use_case.search_cor_form(
        "bord",
        limit=100,
        include_translations=False,
        en_query="table",
        en_pos_ud="NOUN",
    )

    assert gemini.calls[0][2] == "NOUN"


def test_wordbank_search_cor_form_batch_preserves_order_and_filter_semantics(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(by_form=_bord_homograph_lookup())
    gemini = _StubENGeminiForMatchFilter({"0": True, "1": False})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        en_gemini_translation_service=gemini,
    )

    responses = use_case.search_cor_form_batch(
        [
            ("bord", "table", "NOUN"),
            ("bord", "table", None),
        ],
        limit=100,
        include_translations=False,
    )

    assert [response.form for response in responses] == ["bord", "bord"]
    assert [response.groups[0].variants[0].cor_id for response in responses] == [
        "COR.44636.120.01",
        "COR.44636.120.01",
    ]
    assert len(gemini.calls) == 2
    assert gemini.calls[0][2] in {"NOUN", None}


def test_wordbank_search_cor_form_batch_uses_single_batched_match_filter(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(by_form=_bord_homograph_lookup())
    gemini = _BatchStubENGeminiForMatchFilter(
        {
            "0:0": True,
            "0:1": False,
            "1:0": True,
            "1:1": False,
        }
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        en_gemini_translation_service=gemini,
    )

    responses = use_case.search_cor_form_batch(
        [
            ("bord", "table", "NOUN"),
            ("bord", "table", None),
        ],
        limit=100,
        include_translations=False,
    )

    assert [response.groups[0].variants[0].cor_id for response in responses] == [
        "COR.44636.120.01",
        "COR.44636.120.01",
    ]
    assert gemini.calls == []
    assert len(gemini.batch_calls) == 1
    query, choices, en_pos_ud = gemini.batch_calls[0]
    assert query == "table"
    assert en_pos_ud == "NOUN"
    assert {choice["id"] for choice in choices} == {"0:0", "0:1", "1:0", "1:1"}


def test_wordbank_search_cor_form_keeps_all_senses_when_gemini_marks_none_matching(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(by_form=_bord_homograph_lookup())
    gemini = _StubENGeminiForMatchFilter({"0": False, "1": False})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        en_gemini_translation_service=gemini,
    )

    response = use_case.search_cor_form(
        "bord",
        limit=100,
        include_translations=False,
        en_query="table",
    )

    # Empty filter result is treated as a Gemini failure: keep all senses rather than
    # leaving the user with zero results.
    assert {group.gloss for group in response.groups} == {"et møbel", "planke på skib el. båd"}


def test_wordbank_search_cor_form_falls_back_to_pos_filter_when_gemini_marks_none(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "bog": [
                CORLocalEntry(
                    cor_id="COR.BOG.VERB",
                    lemma="boge",
                    gloss=None,
                    gram_raw="vb.imp",
                    form="bog",
                    norm="N",
                    lemma_idx=34998,
                    gram_code=209,
                    variation=1,
                    pos_tag="VERB",
                    morphology="Mood=Imp|VerbForm=Fin",
                    features={"Mood": "Imp", "VerbForm": "Fin"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.BOG.NOUN",
                    lemma="bog",
                    gloss="til læsning",
                    gram_raw="sb.fk.sg.ubest",
                    form="bog",
                    norm="N",
                    lemma_idx=41274,
                    gram_code=110,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Ind",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
            ]
        }
    )
    gemini = _StubENGeminiForMatchFilter({"0": False})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        en_gemini_translation_service=gemini,
    )

    response = use_case.search_cor_form(
        "bog",
        limit=100,
        include_translations=False,
        en_query="books",
        en_pos_ud="NOUN",
    )

    assert [group.pos_tag for group in response.groups] == ["NOUN"]
    assert response.groups[0].variants[0].cor_id == "COR.BOG.NOUN"


def test_wordbank_search_cor_form_filters_cross_pos_homographs_via_en_query(tmp_path: Path) -> None:
    # Surface "kort" matches three unrelated paradigms in COR: the adjective kort ("short"),
    # the imperative of the verb korte ("shorten!"), and the noun kort ("card"/"map").
    # When the EN query is "card", only the noun is a real translation; the other two are
    # spelling collisions across POS and must be filtered out.
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "kort": [
                CORLocalEntry(
                    cor_id="COR.16064.300.01",
                    lemma="kort",
                    gloss=None,
                    gram_raw="adj.sg.ubest.fk",
                    form="kort",
                    norm="N",
                    lemma_idx=16064,
                    gram_code=300,
                    variation=1,
                    pos_tag="ADJ",
                    morphology="Gender=Com|Number=Sing|Definite=Ind",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.31921.209.01",
                    lemma="korte",
                    gloss=None,
                    gram_raw="vb.imp",
                    form="kort",
                    norm="N",
                    lemma_idx=31921,
                    gram_code=209,
                    variation=1,
                    pos_tag="VERB",
                    morphology="Mood=Imp|VerbForm=Fin",
                    features={"Mood": "Imp", "VerbForm": "Fin"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.53487.120.01",
                    lemma="kort",
                    gloss=None,
                    gram_raw="sb.itk.sg.ubest",
                    form="kort",
                    norm="N",
                    lemma_idx=53487,
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
    gemini = _StubENGeminiForMatchFilter({"0": False, "1": False, "2": True})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        en_gemini_translation_service=gemini,
    )

    response = use_case.search_cor_form(
        "kort",
        limit=100,
        include_translations=False,
        en_query="card",
    )

    assert [group.pos_tag for group in response.groups] == ["NOUN"]
    assert response.groups[0].variants[0].cor_id == "COR.53487.120.01"
    # All three candidates were sent to Gemini even though each was the sole group for its POS.
    assert len(gemini.calls) == 1
    assert {choice["pos"] for choice in gemini.calls[0][1]} == {"ADJ", "VERB", "NOUN"}


def test_wordbank_search_cor_form_does_not_call_gemini_without_en_query(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(by_form=_bord_homograph_lookup())
    gemini = _StubENGeminiForMatchFilter({"0": True, "1": False})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        en_gemini_translation_service=gemini,
    )

    response = use_case.search_cor_form("bord", limit=100, include_translations=False)

    assert len(response.groups) == 2
    assert gemini.calls == []


def test_wordbank_search_cor_form_keeps_finite_verb_separate_from_perfect_participle(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "råbte": [
                CORLocalEntry(
                    cor_id="COR.35978.206.01",
                    lemma="råbe",
                    gloss=None,
                    gram_raw="vb.præt.akt",
                    form="råbte",
                    norm="N",
                    lemma_idx=35978,
                    gram_code=206,
                    variation=1,
                    pos_tag="VERB",
                    morphology="Tense=Past|VerbForm=Fin|Voice=Act",
                    features={"Tense": "Past", "VerbForm": "Fin", "Voice": "Act"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.35978.214.01",
                    lemma="råbe",
                    gloss=None,
                    gram_raw="vb.perf.part.sg.best",
                    form="råbte",
                    norm="N",
                    lemma_idx=35978,
                    gram_code=214,
                    variation=1,
                    pos_tag="VERB",
                    morphology="VerbForm=Part|Number=Sing|Definite=Def",
                    features={"VerbForm": "Part", "Number": "Sing", "Definite": "Def"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.35978.215.01",
                    lemma="råbe",
                    gloss=None,
                    gram_raw="vb.perf.part.pl",
                    form="råbte",
                    norm="N",
                    lemma_idx=35978,
                    gram_code=215,
                    variation=1,
                    pos_tag="VERB",
                    morphology="VerbForm=Part|Number=Plur",
                    features={"VerbForm": "Part", "Number": "Plur"},
                    extra_tags=[],
                ),
            ]
        }
    )
    use_case = WordbankUseCase(_db_path(tmp_path), cor_local_lexicon_service=local_cor)

    response = use_case.search_cor_form("råbte", limit=100, include_translations=False)

    assert len(response.groups) == 1
    variants = response.groups[0].variants
    grams = [variant.gram_raw for variant in variants]
    assert "vb.præt.akt" in grams
    assert "vb.perf.part.sg.best | vb.perf.part.pl" in grams
    assert len(variants) == 2


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

    response = use_case.search_cor_form("glas", limit=100, include_translations=False)

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
