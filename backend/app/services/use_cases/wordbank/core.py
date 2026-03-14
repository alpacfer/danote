from __future__ import annotations

from pathlib import Path

from app.api.schemas.v1.wordbank import (
    CORLemmaParadigmResponse,
    CORSearchFormResponse,
    DetectWordLanguageResponse,
    GeneratePhraseTranslationResponse,
    GeneratePronunciationResponse,
    GenerateReverseTranslationResponse,
    GenerateTranslationResponse,
    LemmaDetailsResponse,
    LemmaListResponse,
    ResetDatabaseResponse,
    ResolveQueryResponse,
    WordbankSearchResponse,
)
from app.db.repositories import WordbankRepository
from app.nlp.adapter import NLPAdapter
from app.services.cor import CORLexiconService
from app.services.cor_local import CORLocalLexiconService
from app.services.gemini_translation import GeminiWordTranslationService
from app.services.translation import TranslationService
from app.services.tts import PronunciationAudio, TTSService
from app.services.use_cases.wordbank.commands_add_word import add_word
from app.services.use_cases.wordbank.commands_database import reset_database
from app.services.use_cases.wordbank.collaborators.cor import CorResolutionCollaborator
from app.services.use_cases.wordbank.collaborators.nlp import NLPCollaborator
from app.services.use_cases.wordbank.collaborators.pronunciation import PronunciationCollaborator
from app.services.use_cases.wordbank.collaborators.translation import TranslationCollaborator
from app.services.use_cases.wordbank.collaborators.verification import VerificationCollaborator
from app.services.use_cases.wordbank.queries_details import get_lemma_details
from app.services.use_cases.wordbank.queries_lemmas import list_lemmas, search_lemmas
from app.services.use_cases.wordbank.runtime import WordbankRuntime
from app.services.verification import WordVerificationService


class WordbankUseCase:
    def __init__(
        self,
        db_path,
        typo_engine=None,
        translation_service: TranslationService | None = None,
        gemini_word_translation_service: GeminiWordTranslationService | None = None,
        nlp_adapter: NLPAdapter | None = None,
        cor_lexicon_service: CORLexiconService | None = None,
        cor_local_lexicon_service: CORLocalLexiconService | None = None,
        verification_service: WordVerificationService | None = None,
        tts_service: TTSService | None = None,
        gemini_changes_log_path: Path | None = None,
    ):
        nlp = NLPCollaborator(nlp_adapter, typo_engine, cor_lexicon_service)
        pronunciation = PronunciationCollaborator(tts_service, db_path)
        translation = TranslationCollaborator(
            translation_service,
            gemini_word_translation_service,
            cor_local_lexicon_service,
            db_path,
        )
        cor = CorResolutionCollaborator(
            cor_lexicon_service,
            cor_local_lexicon_service,
            db_path,
            translation,
            nlp,
        )
        verification = VerificationCollaborator(
            verification_service,
            db_path,
            gemini_changes_log_path,
            nlp,
            cor,
        )
        self._runtime = WordbankRuntime(
            db_path=db_path,
            repository=WordbankRepository(db_path),
            nlp=nlp,
            pronunciation=pronunciation,
            translation=translation,
            cor=cor,
            verification=verification,
        )

    def add_word(
        self,
        surface_token: str,
        lemma_candidate: str | None,
        *,
        cor_id: str | None = None,
        pos_tag: str | None = None,
        morphology: str | None = None,
        search_seed: dict[str, object] | None = None,
    ):
        return add_word(
            self._runtime,
            surface_token,
            lemma_candidate,
            cor_id=cor_id,
            pos_tag=pos_tag,
            morphology=morphology,
            search_seed=search_seed,
        )

    def generate_pronunciation_for_added_word(
        self,
        stored_lemma: str,
        stored_surface_form: str | None,
        *,
        force: bool = False,
    ) -> GeneratePronunciationResponse:
        return self._runtime.pronunciation.generate_pronunciation_for_added_word(
            stored_lemma, stored_surface_form, force=force
        )

    def verify_added_word(
        self,
        stored_lemma: str,
        stored_surface_form: str | None,
        *,
        meaning_id: int | None = None,
    ):
        return self._runtime.verification.verify_added_word(
            stored_lemma,
            stored_surface_form,
            meaning_id=meaning_id,
        )

    def verify_added_word_if_current(
        self,
        stored_lemma: str,
        stored_surface_form: str | None,
        *,
        meaning_id: int | None = None,
        expected_snapshot_hash: str,
    ) -> bool:
        return self._runtime.verification.verify_added_word_if_current(
            stored_lemma,
            stored_surface_form,
            meaning_id=meaning_id,
            expected_snapshot_hash=expected_snapshot_hash,
        )

    def apply_verification_changes(
        self,
        *,
        stored_lemma: str,
        stored_surface_form: str | None,
        meaning_id: int | None = None,
        action: dict[str, object],
        provider: str | None = None,
    ):
        return self._runtime.verification.apply_verification_changes(
            stored_lemma=stored_lemma,
            stored_surface_form=stored_surface_form,
            meaning_id=meaning_id,
            action=action,
            provider=provider,
        )

    def reset_database(self) -> ResetDatabaseResponse:
        return reset_database(self._runtime)

    def list_lemmas(self) -> LemmaListResponse:
        return list_lemmas(self._runtime)

    def search_lemmas(self, query: str, *, limit: int = 8) -> WordbankSearchResponse:
        return search_lemmas(self._runtime, query, limit=limit)

    def get_lemma_details(self, lemma: str) -> LemmaDetailsResponse:
        return get_lemma_details(self._runtime, lemma)

    def get_pronunciation_audio(self, form: str) -> PronunciationAudio:
        return self._runtime.pronunciation.get_pronunciation_audio(form)

    def search_cor_form(self, form: str, *, limit: int = 100, include_translations: bool = True) -> CORSearchFormResponse:
        return self._runtime.cor.search_cor_form(form, limit=limit, include_translations=include_translations)

    def search_cor_lemma_paradigm(
        self, lemma_idx: int, *, limit: int = 1000
    ) -> CORLemmaParadigmResponse:
        return self._runtime.cor.search_cor_lemma_paradigm(lemma_idx, limit=limit)

    def resolve_query(self, query_text: str, *, include_translations: bool = True, include_language_detection: bool = True) -> ResolveQueryResponse:
        return self._runtime.cor.resolve_query(
            query_text,
            include_translations=include_translations,
            include_language_detection=include_language_detection,
        )

    def generate_translation(
        self, surface_token: str, lemma_candidate: str | None
    ) -> GenerateTranslationResponse:
        return self._runtime.translation.generate_translation(surface_token, lemma_candidate)

    def generate_phrase_translation(self, source_text: str) -> GeneratePhraseTranslationResponse:
        return self._runtime.translation.generate_phrase_translation(source_text)

    def generate_reverse_translation(self, source_word: str) -> GenerateReverseTranslationResponse:
        return self._runtime.translation.generate_reverse_translation(source_word)

    def detect_word_language(self, source_word: str) -> DetectWordLanguageResponse:
        return self._runtime.translation.detect_word_language(
            source_word,
            cor_entries_lookup=self._runtime.cor.cor_entries_for_surface,
        )
