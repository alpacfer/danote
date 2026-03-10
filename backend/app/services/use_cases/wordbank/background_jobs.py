from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from app.db.repositories import WordbankBackgroundJobRepository
from app.services.use_cases.wordbank import WordbankUseCase

logger = logging.getLogger(__name__)


class WordbankBackgroundJobRunner:
    def __init__(
        self,
        *,
        db_path: Path,
        services: Any,
        gemini_changes_log_path: Path | None,
        poll_interval_seconds: float = 0.25,
    ) -> None:
        self._db_path = db_path
        self._repository = WordbankBackgroundJobRepository(db_path)
        self._services = services
        self._gemini_changes_log_path = gemini_changes_log_path
        self._poll_interval_seconds = poll_interval_seconds
        self._stop_event = threading.Event()
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

    def _run(self) -> None:
        while not self._stop_event.is_set():
            job = self._repository.claim_next()
            if job is None:
                self._stop_event.wait(self._poll_interval_seconds)
                continue
            try:
                self._handle_job(job.job_type, job.payload)
            except Exception as exc:  # pragma: no cover - exercised through queue state assertions
                logger.exception(
                    "wordbank_background_job_failed",
                    extra={"job_type": job.job_type, "job_id": job.id},
                )
                self._repository.mark_retryable_failure(job, error_message=str(exc))
                continue
            self._repository.mark_completed(job.id)

    def _handle_job(self, job_type: str, payload: dict[str, object]) -> None:
        use_case = WordbankUseCase(
            self._db_path,
            typo_engine=self._services.typo_engine,
            translation_service=self._services.translation_service,
            gemini_word_translation_service=self._services.gemini_word_translation_service,
            nlp_adapter=self._services.nlp_adapter,
            cor_lexicon_service=self._services.cor_lexicon_service,
            cor_local_lexicon_service=self._services.cor_local_lexicon_service,
            verification_service=self._services.word_verification_service,
            tts_service=self._services.tts_service,
            gemini_changes_log_path=self._gemini_changes_log_path,
        )
        stored_lemma = _string_value(payload, "stored_lemma")
        stored_surface_form = _optional_string_value(payload, "stored_surface_form")
        if job_type == "verify_word":
            use_case.verify_added_word(
                stored_lemma,
                stored_surface_form,
                meaning_id=_optional_int_value(payload, "meaning_id"),
            )
            return
        if job_type == "generate_pronunciation":
            use_case.generate_pronunciation_for_added_word(
                stored_lemma,
                stored_surface_form,
            )
            return
        raise ValueError(f"Unsupported background job type: {job_type}")


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
