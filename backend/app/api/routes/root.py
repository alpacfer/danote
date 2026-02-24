from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
def api_root() -> dict[str, str]:
    return {"status": "ok", "message": "danote backend scaffold"}


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    db_ready = bool(getattr(request.app.state, "db_ready", False))
    nlp_ready = bool(getattr(request.app.state, "nlp_ready", False))
    status = "ok" if db_ready and nlp_ready else "degraded"
    payload: dict[str, object] = {
        "status": status,
        "service": "backend",
        "components": {
            "database": "ok" if db_ready else "degraded",
            "nlp": "ok" if nlp_ready else "degraded",
        },
    }

    db_error = getattr(request.app.state, "db_error", None)
    nlp_error = getattr(request.app.state, "nlp_error", None)
    if db_error:
        payload["db_error"] = str(db_error)
    if nlp_error:
        payload["nlp_error"] = str(nlp_error)

    return payload
