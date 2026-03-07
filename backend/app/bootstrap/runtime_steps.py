from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import FastAPI

from app.core.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StartupStep:
    name: str
    run: Callable[[FastAPI, Settings], None]


def run_startup_step(step: StartupStep, app: FastAPI, settings: Settings) -> None:
    started_at = time.perf_counter()
    step.run(app, settings)
    logger.info(
        "backend_startup_step_completed",
        extra={"step": step.name, "duration_ms": round((time.perf_counter() - started_at) * 1000, 2)},
    )
