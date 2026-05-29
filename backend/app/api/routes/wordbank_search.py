from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.api.auth import require_current_user
from app.api.routes._runtime import run_db_operation
from app.api.routes._use_case_factories import build_trial_use_case, build_wordbank_use_case
from app.api.schemas.v1.wordbank import (
    CORLemmaParadigmResponse,
    CORSearchFormBatchRequest,
    CORSearchFormBatchResponse,
    CORSearchFormResponse,
    ENSearchFormResponse,
)
from app.core.app_state import get_runtime_state, get_settings

router = APIRouter()


def _guard_trial(request: Request, query_key: str | None) -> None:
    """Count one distinct word search against the free-trial daily cap.

    No-op when auth is disabled (local dev: the key gate is transparent) or
    when there is no query to meter. Raises 429 when a trial user (no own
    keys) exceeds the daily limit with a not-yet-searched word.
    """
    if not query_key or not query_key.strip():
        return
    if not get_settings(request).auth_enabled:
        return
    current_user = require_current_user(request)
    if current_user.auth_provider == "guest":
        decision = build_trial_use_case(request).check_and_consume_guest(
            current_user.guest_browser_id_hash or "",
            query_key,
        )
    else:
        decision = build_trial_use_case(request).check_and_consume(current_user.id, query_key)
    if not decision.allowed:
        raise HTTPException(status_code=429, detail="trial_daily_limit_reached")


def _batch_query_key(payload: CORSearchFormBatchRequest) -> str | None:
    for item in payload.items:
        if item.en_query and item.en_query.strip():
            return item.en_query
    for item in payload.items:
        if item.form and item.form.strip():
            return item.form
    return None


@router.get("/wordbank/search/cor-form", response_model=CORSearchFormResponse)
def search_cor_form(
    request: Request,
    form: str = Query(..., min_length=1),
    limit: int = Query(100, ge=1, le=500),
    include_translations: bool = Query(True),
    en_query: str | None = Query(None, min_length=1),
    en_pos_ud: str | None = Query(None, min_length=1),
) -> CORSearchFormResponse:
    _guard_trial(request, en_query or form)
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).search_cor_form(
            form,
            limit=limit,
            include_translations=include_translations,
            en_query=en_query,
            en_pos_ud=en_pos_ud,
        ),
        include_runtime_error=True,
        error_log_name="wordbank_db_operational_error",
    )


@router.post("/wordbank/search/cor-form-batch", response_model=CORSearchFormBatchResponse)
def search_cor_form_batch(
    payload: CORSearchFormBatchRequest,
    request: Request,
) -> CORSearchFormBatchResponse:
    _guard_trial(request, _batch_query_key(payload))
    return run_db_operation(
        request,
        lambda: CORSearchFormBatchResponse(
            items=build_wordbank_use_case(request).search_cor_form_batch(
                [(item.form, item.en_query, item.en_pos_ud) for item in payload.items],
                limit=payload.limit,
                include_translations=payload.include_translations,
            )
        ),
        include_runtime_error=True,
        error_log_name="wordbank_db_operational_error",
    )


@router.get("/wordbank/search/en-form", response_model=ENSearchFormResponse)
def search_en_form(
    request: Request,
    form: str = Query(..., min_length=1),
    include_translations: bool = Query(True),
) -> ENSearchFormResponse:
    _guard_trial(request, form)
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).search_en_form(
            form,
            include_translations=include_translations,
        ),
        include_runtime_error=True,
        error_log_name="wordbank_db_operational_error",
    )


@router.get("/wordbank/search/cor-lemma/{lemma_idx}", response_model=CORLemmaParadigmResponse)
def search_cor_lemma_paradigm(
    lemma_idx: int,
    request: Request,
    limit: int = Query(1000, ge=1, le=5000),
) -> CORLemmaParadigmResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).search_cor_lemma_paradigm(lemma_idx, limit=limit),
        include_runtime_error=True,
        error_log_name="wordbank_db_operational_error",
    )


@router.post("/admin/clear-search-cache")
def clear_search_cache(request: Request) -> dict[str, str]:
    runtime = get_runtime_state(request)
    if not runtime.settings.search_admin_enabled:
        raise HTTPException(status_code=404, detail="Not found")
    cleared = 0
    for service in (
        runtime.services.en_gemini_translation_service,
        runtime.services.gemini_word_translation_service,
    ):
        cache = getattr(service, "cache", None)
        clear = getattr(cache, "clear", None)
        if callable(clear):
            clear()
            cleared += 1
    resolver = runtime.user_service_resolver
    clear_all = getattr(resolver, "clear_all_cached_user_services", None)
    if callable(clear_all):
        clear_all()
    return {"status": "cleared", "caches": str(cleared)}
