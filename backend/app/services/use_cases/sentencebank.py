from __future__ import annotations

from app.api.schemas.v1.sentencebank import (
    AddSentenceResponse,
    SentenceListResponse,
    SentenceSearchPreviewResponse,
    SentenceSummary,
    VerifySentenceResponse,
)
from app.db.repositories import SentencebankRepository
from app.nlp.adapter import NLPAdapter
from app.services.sentence_verification import SentenceVerificationService
from app.services.token_classifier import normalize_token
from app.services.translation import TranslationService
from app.services.use_cases.sentencebank_mappers import sentence_response, sentence_summary
from app.services.use_cases.sentencebank_preview import (
    build_sentence_search_preview,
    build_verify_sentence_response,
    lookup_phrase_translation,
    translation_provider_name,
)
from app.services.use_cases.sentencebank_text import normalize_sentence_text
from app.services.use_cases.sentencebank_token_persistence import (
    batch_verify_new_sentence_tokens,
)
from app.services.use_cases.sentencebank_token_resolution import resolve_sentence_tokens
from app.services.use_cases.wordbank import WordbankUseCase


class SentencebankUseCase:
    def __init__(
        self,
        db_path,
        translation_service: TranslationService | None = None,
        nlp_adapter: NLPAdapter | None = None,
        wordbank_use_case: WordbankUseCase | None = None,
        sentence_verification_service: SentenceVerificationService | None = None,
    ):
        self._repository = SentencebankRepository(db_path)
        self._translation_service = translation_service
        self._nlp_adapter = nlp_adapter
        self._wordbank_use_case = wordbank_use_case
        self._sentence_verification_service = sentence_verification_service

    def add_sentence(self, source_text: str) -> AddSentenceResponse:
        normalized_source_text = normalize_sentence_text(source_text)
        normalized_key = normalize_token(source_text)
        if not normalized_source_text or not normalized_key:
            raise ValueError("source_text is required")

        existing = self._repository.find_by_normalized_sentence(normalized_key)
        if existing is not None:
            return sentence_response(
                existing,
                status="exists",
                message=f'"{existing.source_text}" is already in sentencebank.',
            )

        english_translation = lookup_phrase_translation(
            source_text=normalized_source_text,
            translation_service=self._translation_service,
            wordbank_use_case=self._wordbank_use_case,
        )
        provider = translation_provider_name(self._translation_service)
        sentence_id = self._repository.insert_sentence(
            source_text=normalized_source_text,
            normalized_sentence=normalized_key,
            english_translation=english_translation,
            translation_provider=provider if english_translation else None,
        )
        token_records, new_token_metadata = resolve_sentence_tokens(
            self._wordbank_use_case.runtime if self._wordbank_use_case is not None else None,
            source_text=normalized_source_text,
            nlp_adapter=self._nlp_adapter,
            wordbank_use_case=self._wordbank_use_case,
        )
        self._repository.replace_sentence_tokens(sentence_id=sentence_id, tokens=token_records)
        if new_token_metadata and self._wordbank_use_case is not None:
            batch_verify_new_sentence_tokens(
                self._wordbank_use_case.runtime,
                new_token_metadata=new_token_metadata,
                sentence_context=normalized_source_text,
            )
        saved = self._repository.find_by_normalized_sentence(normalized_key)
        if saved is None:
            raise RuntimeError("Sentence was saved but could not be reloaded.")
        return sentence_response(
            saved,
            status="inserted",
            message=f'Added "{normalized_source_text}" to sentencebank.',
        )

    def list_sentences(self) -> SentenceListResponse:
        rows = self._repository.list_sentences()
        return SentenceListResponse(items=[sentence_summary(row) for row in rows])

    def list_linked_sentences(self, stored_lemma: str) -> list[SentenceSummary]:
        normalized_lemma = normalize_token(stored_lemma)
        if not normalized_lemma:
            return []
        return [sentence_summary(row) for row in self._repository.list_linked_sentences_for_lemma(normalized_lemma)]

    def verify_sentence(self, source_text: str) -> VerifySentenceResponse:
        normalized = normalize_sentence_text(source_text)
        if not normalized:
            raise ValueError("source_text is required")
        return build_verify_sentence_response(
            normalized_text=normalized,
            sentence_verification_service=self._sentence_verification_service,
        )

    def preview_sentence_search(self, source_text: str, *, fast: bool = False) -> SentenceSearchPreviewResponse:
        normalized_query = normalize_sentence_text(source_text)
        if not normalized_query:
            raise ValueError("source_text is required")
        return build_sentence_search_preview(
            normalized_query=normalized_query,
            translation_service=self._translation_service,
            wordbank_use_case=self._wordbank_use_case,
            sentence_verification_service=self._sentence_verification_service,
            fast=fast,
        )
