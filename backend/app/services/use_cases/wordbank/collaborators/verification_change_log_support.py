from __future__ import annotations

from dataclasses import asdict
import json
import logging
from pathlib import Path

from app.db.repositories.wordbank import WordbankRepository
from app.services.verification import WordVerificationInput
from app.services.use_cases.wordbank.verification_change_log import build_change_log_before_json


def append_gemini_change_log(
    *,
    gemini_changes_log_path: Path | None,
    payload: dict[str, object],
    logger: logging.Logger,
) -> None:
    if gemini_changes_log_path is None:
        return
    try:
        gemini_changes_log_path.parent.mkdir(parents=True, exist_ok=True)
        with gemini_changes_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True))
            handle.write("\n")
    except Exception:
        logger.exception(
            "wordbank_gemini_change_log_write_failed",
            extra={"gemini_changes_log_path": str(gemini_changes_log_path)},
        )


def write_change_log_db_entry(
    *,
    db_path: Path,
    stored_lemma: str,
    stored_surface_form: str | None,
    meaning_id: int | None,
    result,
    pre_apply_surfaces: list[dict[str, object]] | None,
    provider_name: str,
    applied_at: str,
    logger: logging.Logger,
) -> None:
    if result.log_payload is None or result.status != "applied":
        return
    action_type = str(result.log_payload.get("action_type", ""))
    if action_type not in {"fix_translation", "fix_variations"}:
        return
    before_json = build_change_log_before_json(
        action_type=action_type,
        meaning_id=meaning_id,
        before_snapshot=dict(result.log_payload.get("before") or {}),
        pre_apply_surfaces=pre_apply_surfaces,
    )
    after_json = dict(result.log_payload.get("after") or {})
    repository = WordbankRepository(db_path)
    try:
        repository.insert_change_log_entry(
            stored_lemma=stored_lemma,
            stored_surface_form=stored_surface_form,
            meaning_id=meaning_id,
            action_type=action_type,
            before_json=before_json,
            after_json=after_json,
            applied_at=applied_at,
            provider=provider_name,
        )
    except Exception:
        logger.exception("wordbank_change_log_db_write_failed", extra={"stored_lemma": stored_lemma})


def verification_payload_hash(payload: WordVerificationInput) -> str:
    serialized = {key: value for key, value in asdict(payload).items()}
    return json.dumps(serialized, ensure_ascii=True, sort_keys=True)
