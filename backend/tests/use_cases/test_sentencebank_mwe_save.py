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
