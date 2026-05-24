from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.routes._runtime import run_db_operation
from app.api.routes._use_case_factories import build_wordbank_use_case
from app.api.schemas.v1.wordbank import (
    ExpandLemmaSensesRequest,
    ExpandLemmaSensesResponse,
)

router = APIRouter()


@router.post("/wordbank/lexemes/expand-senses", response_model=ExpandLemmaSensesResponse)
def expand_lemma_senses(
    payload: ExpandLemmaSensesRequest,
    request: Request,
) -> ExpandLemmaSensesResponse:
    return run_db_operation(
        request,
        lambda: _to_response(build_wordbank_use_case(request).expand_lemma_senses(payload.lemma)),
        include_lookup_error=True,
        error_log_name="wordbank_db_operational_error",
    )


def _to_response(result) -> ExpandLemmaSensesResponse:
    return ExpandLemmaSensesResponse(
        lemma=result.lemma,
        status=result.status,
        discovered_count=result.discovered_count,
        inserted_count=result.inserted_count,
        renamed_legacy=result.renamed_legacy,
    )
