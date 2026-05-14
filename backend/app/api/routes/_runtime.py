from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from typing import TypeVar

from fastapi import HTTPException, Request

from app.core.app_state import (
    get_runtime_state,
    get_services,
    get_settings,
    resolve_services_for_user,
)
from app.core.errors import ConflictError

logger = logging.getLogger(__name__)
T = TypeVar("T")


def require_db_ready(request: Request) -> None:
    if not get_runtime_state(request).db_ready:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Check backend logs and DB path configuration.",
        )


def require_nlp_ready(request: Request) -> None:
    runtime = get_runtime_state(request)
    if not runtime.nlp_ready or get_services(request).nlp_adapter is None:
        raise HTTPException(
            status_code=503,
            detail="NLP unavailable. The previous DaCy NLP stack is retired and no adapter is configured.",
        )


def run_db_operation(
    request: Request,
    operation: Callable[[], T],
    *,
    include_lookup_error: bool = False,
    include_runtime_error: bool = False,
    error_log_name: str = "db_operational_error",
) -> T:
    require_db_ready(request)
    try:
        return operation()
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        if include_lookup_error:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise
    except RuntimeError as exc:
        if include_runtime_error:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        raise
    except sqlite3.OperationalError as exc:
        logger.exception(error_log_name)
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc


__all__ = [
    "get_runtime_state",
    "get_services",
    "get_settings",
    "resolve_services_for_user",
    "ConflictError",
    "require_db_ready",
    "require_nlp_ready",
    "run_db_operation",
]
