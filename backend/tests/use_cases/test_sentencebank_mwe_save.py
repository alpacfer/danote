"""Tests for the MWE-specific slice of the sentence-save flow.

Companions to ``test_sentencebank_use_case.py``: the existing file covers the
end-to-end happy paths (`pas på`, `gav ikke op`, `kigger efter`). This file
focuses on the helpers added during the MWE feature review — meaning section
creation, COR-aware dictionary status, orphan-free re-save, surface morphology
inference (including multi-particle phrasal verbs), and the related-words seed
that intentionally does NOT mark the Gemini job complete.
"""

from __future__ import annotations

from pathlib import Path

from app.nlp.adapter import NLPToken
from app.services.sentence_verification import (
    SentenceMWESpan,
    SentenceVerificationResult,
)
from app.services.use_cases.sentencebank import SentencebankUseCase
from app.services.use_cases.wordbank import WordbankUseCase
from tests.helpers.factories import _cor_local_entry, _db_path
from tests.helpers.fakes import (
    FakeCORLocalLexiconService,
    FakeGeminiRelatedWordsService,
    FakeTranslationService,
)
from tests.use_cases.test_sentencebank_use_case import (
    FakeSentenceVerificationService,
    MappingNLPAdapter,
)


def _make_use_cases(
    db_path: Path,
    *,
    nlp_map: dict[str, list[NLPToken]],
    translations: dict[str, str],
    verification: dict[str, SentenceVerificationResult],
    cor_local_lexicon_service: FakeCORLocalLexiconService | None = None,
    gemini_related_words_service: FakeGeminiRelatedWordsService | None = None,
) -> tuple[SentencebankUseCase, WordbankUseCase, FakeSentenceVerificationService]:
    nlp_adapter = MappingNLPAdapter(nlp_map)
    translation_service = FakeTranslationService(translations)
    verification_service = FakeSentenceVerificationService(results=verification)
    wordbank_use_case = WordbankUseCase(
        db_path,
        translation_service=translation_service,
        nlp_adapter=nlp_adapter,
        cor_local_lexicon_service=cor_local_lexicon_service,
        gemini_related_words_service=gemini_related_words_service,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        translation_service=translation_service,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
        sentence_verification_service=verification_service,
    )
    return sentencebank_use_case, wordbank_use_case, verification_service


def test_mwe_save_creates_meaning_section_and_links_surface_forms(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    sb, wb, _ = _make_use_cases(
        db_path,
        nlp_map={
            "Pas på bilen!": [
                NLPToken(text="Pas", lemma="passe", pos="VERB", morphology=None, is_punctuation=False),
                NLPToken(text="på", lemma="på", pos="ADP", morphology=None, is_punctuation=False),
                NLPToken(text="bilen", lemma="bil", pos="NOUN", morphology=None, is_punctuation=False),
                NLPToken(text="!", lemma="!", pos="PUNCT", morphology=None, is_punctuation=True),
            ],
        },
        translations={"Pas på bilen!": "Watch out for the car!", "bilen": "the car"},
        verification={
            "Pas på bilen!": SentenceVerificationResult(
                is_valid=True,
                errors=[],
                corrected_text=None,
                language="da",
                mwe_spans=[
                    SentenceMWESpan(
                        start=0,
                        end=6,
                        surface="Pas på",
                        lemma="passe på",
                        pos_tag="VERB",
                        gloss="watch out for",
                        english_translation="watch out for",
                    )
                ],
            )
        },
    )

    sb.add_sentence("Pas på bilen!")

    lexeme = wb.runtime.repository.get_lexeme("passe på")
    assert lexeme is not None

    meanings = wb.runtime.repository.list_lexeme_meanings(lexeme.id)
    assert len(meanings) == 1
    meaning = meanings[0]
    assert meaning.meaning_key == "passe på"
    assert (meaning.pos_tag or "").upper() == "VERB"
    # No COR entry fixture wired in this test — should fall back to generated_non_cor.
    assert meaning.dictionary_status == "generated_non_cor"
    assert meaning.cor_lemma_idx is None

    surface_forms = wb.runtime.repository.list_surface_forms(lexeme.id)
    # All MWE surface forms must be linked to the meaning (no orphans).
    for row in surface_forms:
        assert row.meaning_id == meaning.id, f"orphan surface form: {row.form}"


def test_mwe_save_does_not_create_orphan_on_resave(tmp_path: Path) -> None:
    """Saving the same MWE twice must not leave stale meaning_id=NULL rows behind."""
    db_path = _db_path(tmp_path)
    sb, wb, _ = _make_use_cases(
        db_path,
        nlp_map={
            "Pas på bilen!": [
                NLPToken(text="Pas", lemma="passe", pos="VERB", morphology=None, is_punctuation=False),
                NLPToken(text="på", lemma="på", pos="ADP", morphology=None, is_punctuation=False),
                NLPToken(text="bilen", lemma="bil", pos="NOUN", morphology=None, is_punctuation=False),
                NLPToken(text="!", lemma="!", pos="PUNCT", morphology=None, is_punctuation=True),
            ],
            "Pas på bilen i dag!": [
                NLPToken(text="Pas", lemma="passe", pos="VERB", morphology=None, is_punctuation=False),
                NLPToken(text="på", lemma="på", pos="ADP", morphology=None, is_punctuation=False),
                NLPToken(text="bilen", lemma="bil", pos="NOUN", morphology=None, is_punctuation=False),
                NLPToken(text="i", lemma="i", pos="ADP", morphology=None, is_punctuation=False),
                NLPToken(text="dag", lemma="dag", pos="NOUN", morphology=None, is_punctuation=False),
                NLPToken(text="!", lemma="!", pos="PUNCT", morphology=None, is_punctuation=True),
            ],
        },
        translations={
            "Pas på bilen!": "Watch out for the car!",
            "Pas på bilen i dag!": "Watch out for the car today!",
        },
        verification={
            text: SentenceVerificationResult(
                is_valid=True,
                errors=[],
                corrected_text=None,
                language="da",
                mwe_spans=[
                    SentenceMWESpan(
                        start=0,
                        end=6,
                        surface="Pas på",
                        lemma="passe på",
                        pos_tag="VERB",
                        gloss="watch out for",
                        english_translation="watch out for",
                    )
                ],
            )
            for text in ("Pas på bilen!", "Pas på bilen i dag!")
        },
    )

    sb.add_sentence("Pas på bilen!")
    # Second save reuses the existing MWE lexeme — this is the path the orphan-free
    # upsert protects.
    sb.add_sentence("Pas på bilen i dag!")

    lexeme = wb.runtime.repository.get_lexeme("passe på")
    assert lexeme is not None
    surface_forms = wb.runtime.repository.list_surface_forms(lexeme.id)
    pas_paa_rows = [row for row in surface_forms if row.form == "pas på"]
    # Exactly one "pas på" row (no orphan duplicate).
    assert len(pas_paa_rows) == 1
    assert pas_paa_rows[0].meaning_id is not None


def test_mwe_save_seeds_related_words_without_marking_gemini_complete(tmp_path: Path) -> None:
    """Seed writes component rows so the UI has something immediately, but must
    leave the Gemini related-words job pending so the worker can replace the
    seed with the richer Gemini result."""
    from app.db.repositories.wordbank_background_jobs import WordbankBackgroundJobRepository

    db_path = _db_path(tmp_path)
    # Wire a real (fake) Gemini related-words service so the queue actually enqueues.
    # The worker isn't driven synchronously here, so the job stays "pending" — that's
    # exactly what we're asserting (seed did NOT mark it complete).
    sb, wb, _ = _make_use_cases(
        db_path,
        nlp_map={
            "Pas på bilen!": [
                NLPToken(text="Pas", lemma="passe", pos="VERB", morphology=None, is_punctuation=False),
                NLPToken(text="på", lemma="på", pos="ADP", morphology=None, is_punctuation=False),
                NLPToken(text="bilen", lemma="bil", pos="NOUN", morphology=None, is_punctuation=False),
                NLPToken(text="!", lemma="!", pos="PUNCT", morphology=None, is_punctuation=True),
            ],
        },
        translations={"Pas på bilen!": "Watch out for the car!"},
        verification={
            "Pas på bilen!": SentenceVerificationResult(
                is_valid=True,
                errors=[],
                corrected_text=None,
                language="da",
                mwe_spans=[
                    SentenceMWESpan(
                        start=0,
                        end=6,
                        surface="Pas på",
                        lemma="passe på",
                        pos_tag="VERB",
                        gloss=None,
                        english_translation="watch out for",
                    )
                ],
            )
        },
        gemini_related_words_service=FakeGeminiRelatedWordsService(mapping={}),
    )

    sb.add_sentence("Pas på bilen!")

    lexeme = wb.runtime.repository.get_lexeme("passe på")
    assert lexeme is not None

    # Seed rows are present.
    seed_rows = wb.runtime.repository.list_related_words(lexeme.id)
    seed_lemmas = {row.related_lemma for row in seed_rows}
    assert "passe" in seed_lemmas and "på" in seed_lemmas

    # The Gemini related-words job is still pending — the seed must not have marked it complete.
    jobs_repo = WordbankBackgroundJobRepository(db_path, owner_user_id=1)
    job = jobs_repo.get_by_dedupe_key("resolve_related_words::passe på")
    assert job is not None, "expected the Gemini related-words job to be enqueued for the MWE"
    assert job.status in {"pending", "running"}, (
        f"Gemini related-words job for MWE should remain queued, got status={job.status}"
    )


def test_mwe_save_infers_surface_morphology_for_multi_particle_verb(tmp_path: Path) -> None:
    """For "tage af sted" → surface "tog af sted", the head verb's COR entry
    must supply morphology so the surface slots into the Past row instead of
    falling into Other Forms.

    The MWE branch only looks up the *head verb* (first word) — particles like
    "af sted" are not COR-resolved. So the fake COR just needs to know "tog".
    """
    tog_past = _cor_local_entry(
        cor_id="COR.TAGE.PAST",
        lemma="tage",
        gloss=None,
        form="tog",
        lemma_idx=42,
        pos_tag="VERB",
        morphology="Tense=Past|VerbForm=Fin|Voice=Act",
    )
    cor_local = FakeCORLocalLexiconService(
        by_form={"tog": [tog_past]},
        by_lemma_idx={42: [tog_past]},
    )

    db_path = _db_path(tmp_path)
    sb, wb, _ = _make_use_cases(
        db_path,
        nlp_map={
            "Vi tog af sted i går.": [
                NLPToken(text="Vi", lemma="vi", pos="PRON", morphology=None, is_punctuation=False),
                NLPToken(text="tog", lemma="tage", pos="VERB", morphology=None, is_punctuation=False),
                NLPToken(text="af", lemma="af", pos="ADP", morphology=None, is_punctuation=False),
                NLPToken(text="sted", lemma="sted", pos="NOUN", morphology=None, is_punctuation=False),
                NLPToken(text="i", lemma="i", pos="ADP", morphology=None, is_punctuation=False),
                NLPToken(text="går", lemma="gå", pos="ADV", morphology=None, is_punctuation=False),
                NLPToken(text=".", lemma=".", pos="PUNCT", morphology=None, is_punctuation=True),
            ],
        },
        translations={"Vi tog af sted i går.": "We left yesterday."},
        verification={
            "Vi tog af sted i går.": SentenceVerificationResult(
                is_valid=True,
                errors=[],
                corrected_text=None,
                language="da",
                mwe_spans=[
                    SentenceMWESpan(
                        start=3,
                        end=14,
                        surface="tog af sted",
                        lemma="tage af sted",
                        pos_tag="VERB",
                        gloss=None,
                        english_translation="to leave",
                    )
                ],
            )
        },
        cor_local_lexicon_service=cor_local,
    )

    sb.add_sentence("Vi tog af sted i går.")

    lexeme = wb.runtime.repository.get_lexeme("tage af sted")
    assert lexeme is not None
    surface_forms = wb.runtime.repository.list_surface_forms(lexeme.id)
    tog_rows = [row for row in surface_forms if row.form == "tog af sted"]
    assert len(tog_rows) == 1
    assert tog_rows[0].morphology is not None, "expected morphology to be inferred from head verb"
    assert "Tense=Past" in (tog_rows[0].morphology or ""), (
        f"expected Tense=Past in inferred morphology, got {tog_rows[0].morphology!r}"
    )


def test_search_preview_returns_one_variant_per_mwe_meaning(tmp_path: Path) -> None:
    """Polysemous MWE lemmas like "tage på" come back with one CORSearchVariant per
    distinct sense in `mwe_meanings`. Each variant has a distinct cor_id and its own
    gloss / saveable_translation so the frontend can render and save each card
    independently (saves land as distinct lexeme_meanings rows under the same MWE
    lexeme via the existing `add_word_from_search_seed` flow).
    """
    from app.services.sentence_verification import SentenceMWEMeaning

    db_path = _db_path(tmp_path)
    wordbank_use_case = WordbankUseCase(
        db_path,
        translation_service=FakeTranslationService({"tage på": "to put on"}),
        nlp_adapter=MappingNLPAdapter({}),
    )
    sb = SentencebankUseCase(
        db_path,
        translation_service=FakeTranslationService({"tage på": "to put on"}),
        nlp_adapter=MappingNLPAdapter({}),
        wordbank_use_case=wordbank_use_case,
        sentence_verification_service=FakeSentenceVerificationService(results={
            "tage på": SentenceVerificationResult(
                is_valid=True,
                errors=[],
                corrected_text=None,
                language="da",
                is_multi_word_expression=True,
                mwe_lemma="tage på",
                mwe_pos_tag="VERB",
                mwe_gloss="iføre sig tøj",
                mwe_english_translation="to put on (clothes)",
                mwe_meanings=[
                    SentenceMWEMeaning(
                        gloss="iføre sig tøj",
                        english_translation="to put on (clothes)",
                        pos_tag="VERB",
                        meaning_key="iføre sig tøj",
                    ),
                    SentenceMWEMeaning(
                        gloss="forøge sin kropsvægt",
                        english_translation="to gain weight",
                        pos_tag="VERB",
                        meaning_key="tage på i vægt",
                    ),
                    SentenceMWEMeaning(
                        gloss="tage afsted",
                        english_translation="to go somewhere",
                        pos_tag="VERB",
                        meaning_key="tage afsted",
                    ),
                ],
            ),
        }),
    )

    preview = sb.preview_sentence_search("tage på")

    assert preview.is_multi_word_expression is True
    assert preview.mwe_lemma == "tage på"
    # One variant per meaning.
    assert len(preview.mwe_meanings) == 3
    # Distinct cor_ids — required so the frontend treats each as a distinct save target.
    cor_ids = [variant.cor_id for variant in preview.mwe_meanings]
    assert len(set(cor_ids)) == 3
    # Each card carries the SENSE-specific gloss + translation.
    glosses = {variant.gloss for variant in preview.mwe_meanings}
    translations = {variant.saveable_translation for variant in preview.mwe_meanings}
    assert glosses == {"iføre sig tøj", "forøge sin kropsvægt", "tage afsted"}
    assert translations == {"to put on (clothes)", "to gain weight", "to go somewhere"}
    # Back-compat: mwe_cor_match is the first meaning.
    assert preview.mwe_cor_match is not None
    assert preview.mwe_cor_match.saveable_translation == "to put on (clothes)"


def test_search_preview_falls_back_to_single_match_when_meanings_absent(tmp_path: Path) -> None:
    """Older Gemini responses without mwe_meanings still synthesize a one-element
    list (parser-level forward-compat), so the preview always exposes the saveable
    variant via mwe_meanings as well as mwe_cor_match."""
    db_path = _db_path(tmp_path)
    wordbank_use_case = WordbankUseCase(
        db_path,
        translation_service=FakeTranslationService({"se efter": "look after"}),
        nlp_adapter=MappingNLPAdapter({}),
    )
    sb = SentencebankUseCase(
        db_path,
        translation_service=FakeTranslationService({"se efter": "look after"}),
        nlp_adapter=MappingNLPAdapter({}),
        wordbank_use_case=wordbank_use_case,
        sentence_verification_service=FakeSentenceVerificationService(results={
            "se efter": SentenceVerificationResult(
                is_valid=True,
                errors=[],
                corrected_text=None,
                language="da",
                is_multi_word_expression=True,
                mwe_lemma="se efter",
                mwe_pos_tag="VERB",
                mwe_gloss="undersøge",
                mwe_english_translation="look after",
                mwe_meanings=[],  # Older response shape, parser-level synthesis takes over.
            ),
        }),
    )

    preview = sb.preview_sentence_search("se efter")

    assert preview.is_multi_word_expression is True
    assert preview.mwe_cor_match is not None
    # Even with no explicit mwe_meanings, the preview returns one variant for rendering.
    assert len(preview.mwe_meanings) == 1
    assert preview.mwe_meanings[0].lemma == "se efter"
    assert preview.mwe_meanings[0].saveable_translation == "look after"


def test_search_preview_populates_saved_meaning_id_on_matching_mwe_variant(tmp_path: Path) -> None:
    """If an MWE has a saved meaning in the database, the search preview must stamp
    its `saved_meaning_id` on the matching variant and leave it as None on other variants.
    """
    from app.services.sentence_verification import SentenceMWEMeaning

    db_path = _db_path(tmp_path)
    wordbank_use_case = WordbankUseCase(
        db_path,
        translation_service=FakeTranslationService({"tage på": "to put on"}),
        nlp_adapter=MappingNLPAdapter({}),
    )
    sb = SentencebankUseCase(
        db_path,
        translation_service=FakeTranslationService({"tage på": "to put on"}),
        nlp_adapter=MappingNLPAdapter({}),
        wordbank_use_case=wordbank_use_case,
        sentence_verification_service=FakeSentenceVerificationService(results={
            "tage på": SentenceVerificationResult(
                is_valid=True,
                errors=[],
                corrected_text=None,
                language="da",
                is_multi_word_expression=True,
                mwe_lemma="tage på",
                mwe_pos_tag="VERB",
                mwe_gloss="iføre sig tøj",
                mwe_english_translation="to put on (clothes)",
                mwe_meanings=[
                    SentenceMWEMeaning(
                        gloss="iføre sig tøj",
                        english_translation="to put on (clothes)",
                        pos_tag="VERB",
                        meaning_key="iføre sig tøj",
                    ),
                    SentenceMWEMeaning(
                        gloss="forøge sin kropsvægt",
                        english_translation="to gain weight",
                        pos_tag="VERB",
                        meaning_key="tage på i vægt",
                    ),
                    SentenceMWEMeaning(
                        gloss="tage afsted",
                        english_translation="to go somewhere",
                        pos_tag="VERB",
                        meaning_key="tage afsted",
                    ),
                ],
            ),
        }),
    )

    # First, let's explicitly save the "to gain weight" meaning.
    wordbank_use_case.add_word(
        "tage på",
        "tage på",
        search_seed={
            "lemma": "tage på", "surface": "tage på",
            "dictionary_status": "generated_non_cor",
            "cor_id": None, "cor_lemma_idx": None,
            "meaning_key": "tage på i vægt",
            "gloss": "forøge sin kropsvægt",
            "english_translation": "to gain weight",
            "pos_tag": "VERB", "morphology": None, "target_meaning_id": None,
        },
    )

    # Retrieve saved meanings to get the ID.
    lexeme = wordbank_use_case.runtime.repository.get_lexeme("tage på")
    assert lexeme is not None
    saved_meanings = wordbank_use_case.runtime.repository.list_lexeme_meanings(lexeme.id)
    assert len(saved_meanings) == 1
    saved_meaning_id = saved_meanings[0].id

    # Call preview.
    preview = sb.preview_sentence_search("tage på")

    assert preview.is_multi_word_expression is True
    assert len(preview.mwe_meanings) == 3

    # Check stamped saved_meaning_id on each meaning.
    variants_by_key = {variant.meaning_key: variant for variant in preview.mwe_meanings}

    # "tage på i vægt" should have the saved_meaning_id stamped.
    assert variants_by_key["tage på i vægt"].saved_meaning_id == saved_meaning_id

    # The other two should be None.
    assert variants_by_key["iføre sig tøj"].saved_meaning_id is None
    assert variants_by_key["tage afsted"].saved_meaning_id is None


def test_mwe_search_save_after_sentence_save_replaces_auto_meaning(tmp_path: Path) -> None:
    """The sentence-save flow auto-creates an MWE meaning (meaning_key == lemma) so
    the word page renders and "Complete variations" can open. When the user later
    opens search and explicitly saves a specific sense, that explicit save must
    *replace* the auto placeholder rather than add a duplicate row — otherwise
    every MWE the user touched via sentence-save and then search would end up
    with two meaning sections covering the same lemma.
    """
    db_path = _db_path(tmp_path)
    sb, wb, _ = _make_use_cases(
        db_path,
        nlp_map={
            "Pas på bilen!": [
                NLPToken(text="Pas", lemma="passe", pos="VERB", morphology=None, is_punctuation=False),
                NLPToken(text="på", lemma="på", pos="ADP", morphology=None, is_punctuation=False),
                NLPToken(text="bilen", lemma="bil", pos="NOUN", morphology=None, is_punctuation=False),
                NLPToken(text="!", lemma="!", pos="PUNCT", morphology=None, is_punctuation=True),
            ],
        },
        translations={"Pas på bilen!": "Watch out for the car!", "bilen": "the car"},
        verification={
            "Pas på bilen!": SentenceVerificationResult(
                is_valid=True, errors=[], corrected_text=None, language="da",
                mwe_spans=[SentenceMWESpan(
                    start=0, end=6, surface="Pas på", lemma="passe på",
                    pos_tag="VERB",
                    gloss="være opmærksom på",
                    english_translation="to watch out for",
                )],
            )
        },
    )
    sb.add_sentence("Pas på bilen!")

    # Sentinel: the sentence save created the auto MWE meaning (meaning_key == lemma).
    lexeme = wb.runtime.repository.get_lexeme("passe på")
    assert lexeme is not None
    before = wb.runtime.repository.list_lexeme_meanings(lexeme.id)
    assert len(before) == 1
    assert before[0].meaning_key == "passe på"
    auto_meaning_id = before[0].id

    # User now opens search, sees the MWE card with a more specific Gemini sense,
    # and saves it. The save seed carries a different meaning_key and gloss than
    # the auto row's placeholder values.
    wb.add_word(
        "passe på",
        "passe på",
        search_seed={
            "lemma": "passe på",
            "surface": "passe på",
            "dictionary_status": "generated_non_cor",
            "cor_id": None,
            "cor_lemma_idx": None,
            "meaning_key": "være forsigtig",
            "gloss": "være opmærksom eller forsigtig",
            "english_translation": "to watch out, to be careful",
            "pos_tag": "VERB",
            "morphology": None,
            "target_meaning_id": None,
        },
    )

    # Still exactly one meaning row, but its descriptor has been replaced.
    after = wb.runtime.repository.list_lexeme_meanings(lexeme.id)
    assert len(after) == 1, f"expected dedupe to keep one row, got {[m.meaning_key for m in after]}"
    assert after[0].id == auto_meaning_id
    assert after[0].meaning_key == "være forsigtig"
    assert after[0].gloss == "være opmærksom eller forsigtig"
    assert after[0].english_translation == "to watch out, to be careful"


def test_mwe_search_save_with_distinct_meaning_keys_creates_two_meaning_rows(tmp_path: Path) -> None:
    """Polysemous MWE (e.g. "tage på" → put on / gain weight) saves from two cards
    must create two distinct meaning rows. The dedupe only collapses the
    placeholder-shaped auto meaning; second + subsequent explicit saves with new
    meaning_keys always insert.
    """
    db_path = _db_path(tmp_path)
    sb, wb, _ = _make_use_cases(
        db_path,
        nlp_map={},
        translations={},
        verification={},
    )
    # Manually create the MWE lexeme + no auto meaning (search-only path).
    lex_id, _ = wb.runtime.repository.insert_or_load_lexeme(
        stored_lemma="tage på",
        translation=None,
        provider=None,
        pos_tag="VERB",
        morphology=None,
        source="search",
        dictionary_status="generated_non_cor",
    )

    # First explicit search save → meaning A.
    wb.add_word(
        "tage på",
        "tage på",
        search_seed={
            "lemma": "tage på", "surface": "tage på",
            "dictionary_status": "generated_non_cor",
            "cor_id": None, "cor_lemma_idx": None,
            "meaning_key": "iføre sig tøj",
            "gloss": "iføre sig tøj",
            "english_translation": "to put on (clothes)",
            "pos_tag": "VERB", "morphology": None, "target_meaning_id": None,
        },
    )
    # Second explicit save with different sense → meaning B.
    wb.add_word(
        "tage på",
        "tage på",
        search_seed={
            "lemma": "tage på", "surface": "tage på",
            "dictionary_status": "generated_non_cor",
            "cor_id": None, "cor_lemma_idx": None,
            "meaning_key": "tage på i vægt",
            "gloss": "forøge sin kropsvægt",
            "english_translation": "to gain weight",
            "pos_tag": "VERB", "morphology": None, "target_meaning_id": None,
        },
    )

    meanings = wb.runtime.repository.list_lexeme_meanings(lex_id)
    assert len(meanings) == 2
    keys = {m.meaning_key for m in meanings}
    assert keys == {"iføre sig tøj", "tage på i vægt"}
    translations = {m.english_translation for m in meanings}
    assert translations == {"to put on (clothes)", "to gain weight"}


def test_mwe_search_save_after_sentence_save_with_matching_key_reuses_via_upsert(tmp_path: Path) -> None:
    """When the user's explicit save happens to produce the same meaning_key as
    the sentence-auto placeholder ("passe på" == lemma), the underlying upsert
    matches it without going through the dedupe-replace path. Result is still a
    single meaning row."""
    db_path = _db_path(tmp_path)
    sb, wb, _ = _make_use_cases(
        db_path,
        nlp_map={
            "Pas på bilen!": [
                NLPToken(text="Pas", lemma="passe", pos="VERB", morphology=None, is_punctuation=False),
                NLPToken(text="på", lemma="på", pos="ADP", morphology=None, is_punctuation=False),
                NLPToken(text="bilen", lemma="bil", pos="NOUN", morphology=None, is_punctuation=False),
                NLPToken(text="!", lemma="!", pos="PUNCT", morphology=None, is_punctuation=True),
            ],
        },
        translations={"Pas på bilen!": "Watch out for the car!", "bilen": "the car"},
        verification={
            "Pas på bilen!": SentenceVerificationResult(
                is_valid=True, errors=[], corrected_text=None, language="da",
                mwe_spans=[SentenceMWESpan(
                    start=0, end=6, surface="Pas på", lemma="passe på",
                    pos_tag="VERB", gloss=None, english_translation="to watch out for",
                )],
            )
        },
    )
    sb.add_sentence("Pas på bilen!")

    wb.add_word(
        "passe på",
        "passe på",
        search_seed={
            "lemma": "passe på", "surface": "passe på",
            "dictionary_status": "generated_non_cor",
            "cor_id": None, "cor_lemma_idx": None,
            "meaning_key": "passe på",  # Matches the auto meaning's key — plain upsert path.
            "gloss": None,
            "english_translation": "to watch out for",
            "pos_tag": "VERB", "morphology": None, "target_meaning_id": None,
        },
    )

    lexeme = wb.runtime.repository.get_lexeme("passe på")
    assert lexeme is not None
    meanings = wb.runtime.repository.list_lexeme_meanings(lexeme.id)
    assert len(meanings) == 1
