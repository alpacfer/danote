from __future__ import annotations

from fastapi import FastAPI

from app.core.app_state import get_runtime_state, set_runtime_field
from app.core.config import Settings
from app.services.use_cases.wordbank.background_jobs import WordbankBackgroundJobRunner


def initialize_wordbank_background_jobs(app: FastAPI, settings: Settings) -> None:
    runtime = get_runtime_state(app)
    worker = runtime.background_worker
    stop = getattr(worker, "stop", None)
    if callable(stop):
        stop()

    runner = WordbankBackgroundJobRunner(
        db_path=settings.db_path,
        services=runtime.services,
        user_service_resolver=runtime.user_service_resolver,
        gemini_changes_log_path=settings.gemini_changes_log_path,
        max_workers=settings.wordbank_background_job_workers,
    )
    runner.start()
    set_runtime_field(app, "background_worker", runner)
