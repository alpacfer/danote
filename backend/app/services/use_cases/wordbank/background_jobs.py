from __future__ import annotations

import logging
import threading
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any

from app.api.schemas.v1.wordbank import VerificationResult
from app.db.repositories import WordbankBackgroundJobRepository
from app.db.repositories.wordbank import WordbankRepository
from app.db.repositories.wordbank_background_jobs import WordbankBackgroundJobRecord
from app.services.use_cases.sentencebank import SentencebankUseCase
from app.services.use_cases.wordbank import WordbankUseCase
from app.services.use_cases.wordbank.verification_records import persist_verification_result

logger = logging.getLogger(__name__)


class WordbankBackgroundJobRunner:
    def __init__(
        self,
        *,
        db_path: Path,
        services: Any,
        gemini_changes_log_path: Path | None,
        user_service_resolver: Any = None,
        max_workers: int = 4,
        poll_interval_seconds: float = 0.25,
    ) -> None:
        self._db_path = db_path
        self._repository = WordbankBackgroundJobRepository(db_path)
        self._services = services
        self._user_service_resolver = user_service_resolver
        self._gemini_changes_log_path = gemini_changes_log_path
        self._max_workers = max(1, int(max_workers))
        self._poll_interval_seconds = poll_interval_seconds
        self._stop_event = threading.Event()
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_workers,
            thread_name_prefix="wordbank-job",
        )
        self._thread = threading.Thread(
            target=self._run,
            name="wordbank-background-jobs",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=2)
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _run(self) -> None:
        in_flight: dict[Future[None], object] = {}
        try:
            while not self._stop_event.is_set() or in_flight:
                self._collect_completed_jobs(in_flight)
                if self._stop_event.is_set():
                    if in_flight:
                        self._wait_for_completion(in_flight)
                    continue
                while len(in_flight) < self._max_workers:
                    job = self._repository.claim_next()
                    if job is None:
                        break
                    future = self._executor.submit(
                        self._handle_job,
                        job.job_type,
                        job.payload,
                        job.owner_user_id,
                    )
                    in_flight[future] = job
                if in_flight:
                    self._wait_for_completion(in_flight)
                else:
                    self._stop_event.wait(self._poll_interval_seconds)
        finally:
            self._executor.shutdown(wait=True, cancel_futures=False)

    def _collect_completed_jobs(self, in_flight: dict[Future[None], object]) -> None:
        completed = [future for future in in_flight if future.done()]
        for future in completed:
            job = in_flight.pop(future)
            try:
                future.result()
            except Exception as exc:
                logger.exception(
                    "wordbank_background_job_failed",
                    extra={"job_type": job.job_type, "job_id": job.id},
                )
                is_final_attempt = job.attempt_count >= job.max_attempts
                was_requeued = self._repository.mark_retryable_failure(job, error_message=str(exc))
                if is_final_attempt and not was_requeued and job.job_type == "verify_word":
                    self._persist_verify_word_error(job)
                continue
            self._repository.mark_completed(job.id)

    def _persist_verify_word_error(self, job: WordbankBackgroundJobRecord) -> None:
        """After a verify_word job fails permanently, set the verification record to 'error'."""
        try:
            payload = job.payload
            stored_lemma = str(payload.get("stored_lemma", ""))
            stored_surface_form = payload.get("stored_surface_form")
            meaning_id = payload.get("meaning_id")
            if not stored_lemma:
                return

            repository = WordbankRepository(self._db_path, owner_user_id=job.owner_user_id)
            lexeme = repository.get_lexeme(stored_lemma)
            if lexeme is None:
                return

            normalized_surface = (
                str(stored_surface_form).strip() or None
                if stored_surface_form
                else None
            )
            existing = repository.get_verification_record(
                lexeme_id=lexeme.id,
                meaning_id=meaning_id if isinstance(meaning_id, int) else None,
                stored_surface_form=normalized_surface,
            )
            if existing is None or existing.status != "queued":
                return  # Already resolved by another path

            provider = existing.provider or "gemini"
            reviewer_role = existing.reviewer_role or "Professional Danish Language Expert"
            error_result = VerificationResult(
                status="error",
                provider=provider,
                reviewer_role=reviewer_role,
                review_intent=existing.review_intent,
                message="Verification failed after all retries.",
                problem="The verification service could not be reached.",
                change_to_implement="Retry verification manually.",
            )
            persist_verification_result(
                repository,
                lexeme_id=lexeme.id,
                meaning_id=existing.meaning_id,
                stored_surface_form=existing.stored_surface_form,
                verification=error_result,
                latest_snapshot_hash=existing.latest_snapshot_hash,
                request_generation=existing.request_generation,
            )
        except Exception:
            logger.exception("wordbank_background_job_error_persist_failed", extra={"job_id": job.id})

    def _wait_for_completion(self, in_flight: dict[Future[None], object]) -> None:
        if not in_flight:
            return
        wait(
            tuple(in_flight),
            timeout=self._poll_interval_seconds,
            return_when=FIRST_COMPLETED,
        )
        self._collect_completed_jobs(in_flight)

    def _resolve_services(self, owner_user_id: int) -> Any:
        resolver = self._user_service_resolver
        if resolver is None:
            return self._services
        return resolver.resolve(owner_user_id)

    def _handle_job(self, job_type: str, payload: dict[str, object], owner_user_id: int = 1) -> None:
        services = self._resolve_services(owner_user_id)
        use_case = WordbankUseCase(
            self._db_path,
            owner_user_id=owner_user_id,
            translation_service=services.translation_service,
            gemini_word_translation_service=services.gemini_word_translation_service,
            gemini_related_words_service=services.gemini_related_words_service,
            nlp_adapter=services.nlp_adapter,
            cor_lexicon_service=services.cor_lexicon_service,
            cor_local_lexicon_service=services.cor_local_lexicon_service,
            en_local_lexicon_service=services.en_local_lexicon_service,
            en_gemini_translation_service=services.en_gemini_translation_service,
            verification_service=services.word_verification_service,
            tts_service=services.tts_service,
            gemini_changes_log_path=self._gemini_changes_log_path,
        )
        if job_type == "verify_word":
            stored_lemma = _string_value(payload, "stored_lemma")
            stored_surface_form = _optional_string_value(payload, "stored_surface_form")
            result = use_case.process_queued_verification_if_current(
                stored_lemma,
                stored_surface_form,
                meaning_id=_optional_int_value(payload, "meaning_id"),
                expected_snapshot_hash=_string_value(payload, "snapshot_hash"),
                expected_generation=_optional_int_value(payload, "request_generation"),
                review_intent=_optional_string_value(payload, "review_intent") or "general",
            )
            if result == "stale":
                self._requeue_stale_verify_word_job(
                    use_case,
                    stored_lemma=stored_lemma,
                    stored_surface_form=stored_surface_form,
                    meaning_id=_optional_int_value(payload, "meaning_id"),
                    review_intent=_optional_string_value(payload, "review_intent") or "general",
                )
            return
        if job_type == "generate_pronunciation":
            stored_lemma = _string_value(payload, "stored_lemma")
            stored_surface_form = _optional_string_value(payload, "stored_surface_form")
            requested_forms = _optional_string_list(payload, "requested_forms")
            use_case.process_queued_pronunciations(
                stored_lemma,
                requested_forms=requested_forms or ([stored_surface_form] if stored_surface_form else []),
                force=_optional_bool_value(payload, "force") or False,
            )
            return
        if job_type == "generate_sentence_pronunciation":
            sentence_use_case = SentencebankUseCase(
                db_path=self._db_path,
                owner_user_id=owner_user_id,
                translation_service=services.translation_service,
                nlp_adapter=services.nlp_adapter,
                wordbank_use_case=use_case,
                sentence_verification_service=services.sentence_verification_service,
                tts_service=services.tts_service,
            )
            sentence_use_case.process_queued_pronunciation(
                _required_int_value(payload, "sentence_id"),
                force=_optional_bool_value(payload, "force") or False,
            )
            return
        if job_type == "verify_sentence_tokens":
            sentence_use_case = SentencebankUseCase(
                db_path=self._db_path,
                owner_user_id=owner_user_id,
                translation_service=services.translation_service,
                nlp_adapter=services.nlp_adapter,
                wordbank_use_case=use_case,
                sentence_verification_service=services.sentence_verification_service,
                tts_service=services.tts_service,
            )
            sentence_use_case.process_queued_sentence_token_verification(
                new_token_metadata=_metadata_list_value(payload, "new_token_metadata"),
                sentence_context=_string_value(payload, "sentence_context"),
            )
            return
        if job_type == "resolve_related_words":
            stored_lemma = _string_value(payload, "stored_lemma")
            use_case.process_queued_related_words(stored_lemma)
            return
        raise ValueError(f"Unsupported background job type: {job_type}")

    def _requeue_stale_verify_word_job(
        self,
        use_case: WordbankUseCase,
        *,
        stored_lemma: str,
        stored_surface_form: str | None,
        meaning_id: int | None,
        review_intent: str,
    ) -> None:
        repository = WordbankRepository(self._db_path, owner_user_id=use_case.runtime.owner_user_id)
        lexeme = repository.get_lexeme(stored_lemma)
        if lexeme is None:
            return
        current_record = repository.get_verification_record(
            lexeme_id=lexeme.id,
            meaning_id=meaning_id,
            stored_surface_form=stored_surface_form,
        )
        if current_record is None or current_record.status != "queued":
            return
        use_case.queue_verification(
            stored_lemma,
            stored_surface_form,
            meaning_id=meaning_id,
            review_intent=review_intent,
        )


def _string_value(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Background job payload is missing '{key}'.")
    return value


def _optional_string_value(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Background job payload field '{key}' is invalid.")
    cleaned = value.strip()
    return cleaned or None


def _optional_int_value(payload: dict[str, object], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f"Background job payload field '{key}' is invalid.")
    return value


def _required_int_value(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise ValueError(f"Background job payload is missing '{key}'.")
    return value


def _optional_bool_value(payload: dict[str, object], key: str) -> bool | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError(f"Background job payload field '{key}' is invalid.")
    return value


def _optional_string_list(payload: dict[str, object], key: str) -> list[str] | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"Background job payload field '{key}' is invalid.")
    return [item for item in value if item.strip()]


def _metadata_list_value(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"Background job payload field '{key}' is invalid.")
    metadata: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"Background job payload field '{key}' is invalid.")
        stored_lemma = item.get("stored_lemma")
        stored_surface_form = item.get("stored_surface_form")
        meaning_id = item.get("meaning_id")
        if not isinstance(stored_lemma, str) or not stored_lemma.strip():
            raise ValueError(f"Background job payload field '{key}' is invalid.")
        if stored_surface_form is not None and not isinstance(stored_surface_form, str):
            raise ValueError(f"Background job payload field '{key}' is invalid.")
        if meaning_id is not None and not isinstance(meaning_id, int):
            raise ValueError(f"Background job payload field '{key}' is invalid.")
        metadata.append(
            {
                "stored_lemma": stored_lemma,
                "stored_surface_form": stored_surface_form,
                "meaning_id": meaning_id,
            }
        )
    return metadata
