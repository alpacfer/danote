from __future__ import annotations

from app.api.schemas.v1.sentencebank import (
    AddSentenceResponse,
    GenerateExamplePreviewResponse,
    GenerateSentencePronunciationResponse,
    QueuedSentenceVerificationTarget,
    SaveSentenceTokenResponse,
    SentenceListResponse,
    SentenceSearchPreviewResponse,
    SentenceSummary,
    VerifySentenceResponse,
)
from app.db.repositories import SentencebankRepository
from app.db.repositories.wordbank_background_jobs import WordbankBackgroundJobRepository
from app.nlp.adapter import NLPAdapter
from app.services.concurrency import run_in_parallel
from app.services.sentence_verification import SentenceVerificationService
from app.services.token_classifier import normalize_token
from app.services.translation import TranslationService
from app.services.tts import PronunciationAudio, TTSService
from app.services.use_cases.sentencebank_examples import (
    generate_example_preview,
    generate_static_example_preview,
)
from app.services.use_cases.sentencebank_mappers import (
    sentence_response,
    sentence_summary,
    sentence_token_card,
)
from app.services.use_cases.sentencebank_preview import (
    build_sentence_search_preview,
    build_verify_sentence_response,
    lookup_phrase_translation,
    translation_provider_name,
)
from app.services.use_cases.sentencebank_pronunciation import SentencePronunciationCollaborator
from app.services.use_cases.sentencebank_text import normalize_sentence_text
from app.services.use_cases.sentencebank_token_persistence import (
    batch_verify_new_sentence_tokens,
)
from app.services.use_cases.sentencebank_token_resolution import (
    resolve_sentence_tokens,
    resolve_sentence_tokens_link_existing_only,
    resolve_unsaved_sentence_token,
)
from app.services.use_cases.wordbank import WordbankUseCase


class SentencebankUseCase:
    def __init__(
        self,
        db_path,
        owner_user_id: int = 1,
        translation_service: TranslationService | None = None,
        nlp_adapter: NLPAdapter | None = None,
        wordbank_use_case: WordbankUseCase | None = None,
        sentence_verification_service: SentenceVerificationService | None = None,
        tts_service: TTSService | None = None,
    ):
        self._owner_user_id = owner_user_id
        self._repository = SentencebankRepository(db_path, owner_user_id=owner_user_id)
        self._translation_service = translation_service
        self._nlp_adapter = nlp_adapter
        self._wordbank_use_case = wordbank_use_case
        self._sentence_verification_service = sentence_verification_service
        self._background_jobs = WordbankBackgroundJobRepository(db_path, owner_user_id=owner_user_id)
        self._pronunciation = SentencePronunciationCollaborator(
            tts_service,
            db_path,
            owner_user_id=owner_user_id,
        )

    def add_sentence(
        self,
        source_text: str,
        *,
        english_translation: str | None = None,
        token_persistence_mode: str = "auto_save_all",
        target: object | None = None,
    ) -> AddSentenceResponse:
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

        user_provided_translation = (
            normalize_sentence_text(english_translation)
            if english_translation is not None
            else None
        )

        def _resolve_translation() -> str | None:
            if user_provided_translation is not None:
                return user_provided_translation
            return lookup_phrase_translation(
                source_text=normalized_source_text,
                translation_service=self._translation_service,
                wordbank_use_case=self._wordbank_use_case,
            )

        def _resolve_tokens() -> tuple[list, list[dict[str, object]]]:
            if token_persistence_mode == "link_existing_only":
                if target is None:
                    raise ValueError("target is required for link_existing_only")
                tokens = resolve_sentence_tokens_link_existing_only(
                    self._wordbank_use_case.runtime if self._wordbank_use_case is not None else None,
                    source_text=normalized_source_text,
                    nlp_adapter=self._nlp_adapter,
                    stored_lemma=str(getattr(target, "stored_lemma", "")),
                    meaning_id=int(getattr(target, "meaning_id", 0)),
                )
                return tokens, []
            return resolve_sentence_tokens(
                self._wordbank_use_case.runtime if self._wordbank_use_case is not None else None,
                source_text=normalized_source_text,
                nlp_adapter=self._nlp_adapter,
                wordbank_use_case=self._wordbank_use_case,
            )

        normalized_english_translation, (token_records, new_token_metadata) = run_in_parallel(
            _resolve_translation, _resolve_tokens
        )
        provider = translation_provider_name(self._translation_service)
        sentence_id = self._repository.insert_sentence(
            source_text=normalized_source_text,
            normalized_sentence=normalized_key,
            english_translation=normalized_english_translation,
            translation_provider=provider if normalized_english_translation else None,
        )
        self._repository.replace_sentence_tokens(sentence_id=sentence_id, tokens=token_records)
        queued_verification_targets = self._queue_new_token_verification(
            sentence_id=sentence_id,
            scope="add",
            new_token_metadata=new_token_metadata,
            sentence_context=normalized_source_text,
        )
        queued_pronunciation = self._pronunciation.queued_pronunciation_result(sentence_id)
        if queued_pronunciation.status == "queued":
            self._background_jobs.enqueue(
                job_type="generate_sentence_pronunciation",
                dedupe_key=f"generate_sentence_pronunciation::{sentence_id}",
                payload={"sentence_id": sentence_id, "force": False},
            )
        saved = self._repository.find_by_normalized_sentence(normalized_key)
        if saved is None:
            raise RuntimeError("Sentence was saved but could not be reloaded.")
        return sentence_response(
            saved,
            status="inserted",
            message=f'Added "{normalized_source_text}" to sentencebank.',
            pronunciation=queued_pronunciation,
            queued_verification_targets=queued_verification_targets,
        )

    def _queue_new_token_verification(
        self,
        *,
        sentence_id: int,
        scope: str,
        new_token_metadata: list[dict[str, object]],
        sentence_context: str,
    ) -> list[QueuedSentenceVerificationTarget]:
        if not new_token_metadata or self._wordbank_use_case is None:
            return []
        payload_metadata = _verification_metadata_payload(new_token_metadata)
        if not payload_metadata:
            return []
        queued_targets = self._persist_sentence_token_verification_records(payload_metadata)
        self._background_jobs.enqueue(
            job_type="verify_sentence_tokens",
            dedupe_key=f"verify_sentence_tokens::{sentence_id}::{scope}",
            payload={
                "sentence_id": sentence_id,
                "sentence_context": sentence_context,
                "new_token_metadata": payload_metadata,
            },
        )
        return queued_targets

    def _persist_sentence_token_verification_records(
        self,
        payload_metadata: list[dict[str, object]],
    ) -> list[QueuedSentenceVerificationTarget]:
        if self._wordbank_use_case is None:
            return []
        runtime = self._wordbank_use_case.runtime
        queued_targets: list[QueuedSentenceVerificationTarget] = []
        seen: set[tuple[str, int | None, str | None]] = set()
        for meta in payload_metadata:
            stored_lemma = normalize_token(str(meta.get("stored_lemma", "")))
            if not stored_lemma:
                continue
            raw_surface = meta.get("stored_surface_form")
            stored_surface_form = normalize_token(str(raw_surface)) if raw_surface else None
            raw_meaning_id = meta.get("meaning_id")
            meaning_id = int(raw_meaning_id) if isinstance(raw_meaning_id, int) and raw_meaning_id else None
            key = (stored_lemma, meaning_id, stored_surface_form)
            if key in seen:
                continue
            seen.add(key)
            verification = runtime.verification.queued_verification_result(
                stored_surface_form=stored_surface_form,
            )
            snapshot_hash = runtime.verification.build_verification_snapshot_hash(
                stored_lemma=stored_lemma,
                stored_surface_form=stored_surface_form,
                meaning_id=meaning_id,
                review_intent="general",
            )
            runtime.verification.persist_queued_verification(
                stored_lemma=stored_lemma,
                stored_surface_form=stored_surface_form,
                meaning_id=meaning_id,
                verification=verification,
                review_intent="general",
                latest_snapshot_hash=snapshot_hash,
            )
            if verification.status == "queued":
                queued_targets.append(
                    QueuedSentenceVerificationTarget(
                        stored_lemma=stored_lemma,
                        meaning_id=meaning_id,
                        stored_surface_form=stored_surface_form,
                    )
                )
        return queued_targets

    def process_queued_sentence_token_verification(
        self,
        *,
        new_token_metadata: list[dict[str, object]],
        sentence_context: str,
    ) -> None:
        if self._wordbank_use_case is None:
            return
        payload_metadata = _verification_metadata_payload(new_token_metadata)
        if not payload_metadata:
            return
        batch_verify_new_sentence_tokens(
            self._wordbank_use_case.runtime,
            new_token_metadata=payload_metadata,
            sentence_context=sentence_context,
        )

    def list_sentences(self) -> SentenceListResponse:
        rows = self._repository.list_sentences()
        return SentenceListResponse(items=[sentence_summary(row) for row in rows])

    def list_linked_sentences(self, stored_lemma: str) -> list[SentenceSummary]:
        normalized_lemma = normalize_token(stored_lemma)
        if not normalized_lemma:
            return []
        return [sentence_summary(row) for row in self._repository.list_linked_sentences_for_lemma(normalized_lemma)]

    def save_sentence_token(self, sentence_id: int, token_index: int) -> SaveSentenceTokenResponse:
        sentence = self._repository.get_sentence(sentence_id)
        if sentence is None:
            raise ValueError("sentence was not found")
        existing_token = next((token for token in sentence.tokens if token.token_index == token_index), None)
        if existing_token is None:
            raise ValueError("sentence token was not found")
        if existing_token.save_status != "unsaved":
            return SaveSentenceTokenResponse(
                **sentence_summary(sentence).model_dump(),
                saved_token=sentence_token_card(existing_token),
                message=f'Already saved "{existing_token.surface_form}".',
            )
        saved_token, new_token_metadata = resolve_unsaved_sentence_token(
            self._wordbank_use_case.runtime if self._wordbank_use_case is not None else None,
            source_text=sentence.source_text,
            token=existing_token,
            wordbank_use_case=self._wordbank_use_case,
        )
        self._repository.replace_sentence_token(sentence_id=sentence.id, token=saved_token)
        queued_verification_targets = self._queue_new_token_verification(
            sentence_id=sentence.id,
            scope=f"token::{token_index}",
            new_token_metadata=new_token_metadata,
            sentence_context=sentence.source_text,
        )
        updated = self._repository.get_sentence(sentence.id)
        if updated is None:
            raise RuntimeError("Sentence token was saved but the sentence could not be reloaded.")
        updated_token = next((token for token in updated.tokens if token.token_index == token_index), saved_token)
        return SaveSentenceTokenResponse(
            **sentence_summary(updated).model_dump(),
            saved_token=sentence_token_card(updated_token),
            message=f'Added "{saved_token.surface_form}" to wordbank.',
            queued_verification_targets=queued_verification_targets,
        )

    def generate_example_preview(self, stored_lemma: str, meaning_id: int, *, tense_label: str | None = None) -> GenerateExamplePreviewResponse:
        existing = [
            s.source_text
            for s in self._repository.list_linked_sentences_for_lemma(stored_lemma)
            if any(t.meaning_id == meaning_id for t in s.tokens)
        ]
        return generate_example_preview(
            self._wordbank_use_case.runtime if self._wordbank_use_case is not None else None,
            stored_lemma=stored_lemma,
            meaning_id=meaning_id,
            tense_label=tense_label,
            existing_examples=existing,
        )

    def generate_static_example_preview(self, stored_lemma: str) -> GenerateExamplePreviewResponse:
        return generate_static_example_preview(
            self._wordbank_use_case.runtime if self._wordbank_use_case is not None else None,
            stored_lemma=stored_lemma,
        )

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

    def generate_pronunciation_for_sentence(
        self,
        sentence_id: int,
        *,
        force: bool = False,
    ) -> GenerateSentencePronunciationResponse:
        return self._pronunciation.generate_pronunciation_for_sentence(
            sentence_id,
            force=force,
        )

    def process_queued_pronunciation(
        self,
        sentence_id: int,
        *,
        force: bool = False,
    ) -> GenerateSentencePronunciationResponse:
        return self.generate_pronunciation_for_sentence(sentence_id, force=force)

    def get_pronunciation_audio(self, sentence_id: int) -> PronunciationAudio:
        return self._pronunciation.get_pronunciation_audio(sentence_id)

    def delete_sentence(self, sentence_id: int, delete_meanings: bool = False) -> None:
        """Delete a sentence and, optionally, meanings only used by that sentence."""
        if delete_meanings and self._wordbank_use_case is not None:
            meaning_ids = self._repository.list_meaning_ids_exclusive_to_sentence(sentence_id)
            for meaning_id in meaning_ids:
                try:
                    self._wordbank_use_case.delete_meaning(meaning_id)
                except LookupError:
                    pass

        self._repository.delete_sentence(sentence_id)



def _verification_metadata_payload(
    metadata_items: list[dict[str, object]],
) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for item in metadata_items:
        stored_lemma = item.get("stored_lemma")
        if not isinstance(stored_lemma, str) or not stored_lemma.strip():
            continue
        stored_surface_form = item.get("stored_surface_form")
        meaning_id = item.get("meaning_id")
        payload.append(
            {
                "stored_lemma": stored_lemma,
                "stored_surface_form": (
                    stored_surface_form
                    if isinstance(stored_surface_form, str) and stored_surface_form.strip()
                    else None
                ),
                "meaning_id": meaning_id if isinstance(meaning_id, int) else None,
            }
        )
    return payload
