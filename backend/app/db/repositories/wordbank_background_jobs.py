from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.db.sqlite import get_connection, timed_db_operation


@dataclass(frozen=True, slots=True)
class WordbankBackgroundJobRecord:
    id: int
    owner_user_id: int
    job_type: str
    dedupe_key: str
    payload: dict[str, object]
    status: str
    attempt_count: int
    max_attempts: int
    rerun_requested: bool
    last_error: str | None = None
    completed_at: str | None = None


class WordbankBackgroundJobRepository:
    def __init__(self, db_path: Path, *, owner_user_id: int = 1) -> None:
        self._db_path = db_path
        self._owner_user_id = owner_user_id

    def enqueue(
        self,
        *,
        job_type: str,
        dedupe_key: str,
        payload: dict[str, object],
        max_attempts: int = 3,
    ) -> bool:
        with timed_db_operation("wordbank_background_jobs.enqueue"), get_connection(self._db_path) as conn:
            payload_json = json.dumps(payload, ensure_ascii=True, sort_keys=True)
            existing = conn.execute(
                """
                SELECT id, status
                FROM wordbank_background_jobs
                WHERE owner_user_id = ? AND dedupe_key = ?
                LIMIT 1
                """,
                (self._owner_user_id, dedupe_key),
            ).fetchone()
            if existing is None:
                cursor = conn.execute(
                    """
                    INSERT INTO wordbank_background_jobs (
                        owner_user_id,
                        job_type,
                        dedupe_key,
                        payload_json,
                        max_attempts
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (self._owner_user_id, job_type, dedupe_key, payload_json, max_attempts),
                )
                return cursor.rowcount == 1

            existing_status = str(existing["status"])
            if existing_status == "running":
                conn.execute(
                    """
                    UPDATE wordbank_background_jobs
                    SET job_type = ?,
                        payload_json = ?,
                        max_attempts = ?,
                        rerun_requested = 1,
                        last_error = NULL,
                        completed_at = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (job_type, payload_json, max_attempts, int(existing["id"])),
                )
                return False

            conn.execute(
                """
                UPDATE wordbank_background_jobs
                SET job_type = ?,
                    payload_json = ?,
                    status = 'pending',
                    attempt_count = 0,
                    max_attempts = ?,
                    available_at = CURRENT_TIMESTAMP,
                    last_error = NULL,
                    completed_at = NULL,
                    rerun_requested = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (job_type, payload_json, max_attempts, int(existing["id"])),
            )
        return True

    def enqueue_pronunciation_job(
        self,
        *,
        stored_lemma: str,
        requested_forms: list[str],
        force: bool = False,
        max_attempts: int = 3,
    ) -> bool:
        dedupe_key = f"generate_pronunciation::{stored_lemma}"
        with timed_db_operation("wordbank_background_jobs.enqueue_pronunciation"), get_connection(self._db_path) as conn:
            existing = conn.execute(
                """
                SELECT id, status, payload_json
                FROM wordbank_background_jobs
                WHERE owner_user_id = ? AND dedupe_key = ?
                LIMIT 1
                """,
                (self._owner_user_id, dedupe_key),
            ).fetchone()
            payload = {
                "stored_lemma": stored_lemma,
                "requested_forms": requested_forms,
                "force": bool(force),
            }
            payload_json = json.dumps(payload, ensure_ascii=True, sort_keys=True)
            if existing is None:
                cursor = conn.execute(
                    """
                    INSERT INTO wordbank_background_jobs (
                        owner_user_id,
                        job_type,
                        dedupe_key,
                        payload_json,
                        max_attempts
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (self._owner_user_id, "generate_pronunciation", dedupe_key, payload_json, max_attempts),
                )
                return cursor.rowcount == 1

            existing_status = str(existing["status"])
            merged_payload = _merge_pronunciation_payload(
                existing["payload_json"],
                stored_lemma=stored_lemma,
                requested_forms=requested_forms,
                force=force,
            )
            merged_payload_json = json.dumps(merged_payload, ensure_ascii=True, sort_keys=True)
            payload_changed = merged_payload_json != str(existing["payload_json"])

            if existing_status == "running":
                if not payload_changed:
                    return False
                conn.execute(
                    """
                    UPDATE wordbank_background_jobs
                    SET job_type = ?,
                        payload_json = ?,
                        max_attempts = ?,
                        rerun_requested = 1,
                        last_error = NULL,
                        completed_at = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    ("generate_pronunciation", merged_payload_json, max_attempts, int(existing["id"])),
                )
                return True

            should_reset = existing_status in {"completed", "failed"}
            if not payload_changed and not should_reset:
                return False

            conn.execute(
                """
                UPDATE wordbank_background_jobs
                SET job_type = ?,
                    payload_json = ?,
                    status = 'pending',
                    attempt_count = 0,
                    max_attempts = ?,
                    available_at = CURRENT_TIMESTAMP,
                    last_error = NULL,
                    completed_at = NULL,
                    rerun_requested = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                ("generate_pronunciation", merged_payload_json, max_attempts, int(existing["id"])),
            )
        return True

    def claim_next(self) -> WordbankBackgroundJobRecord | None:
        with get_connection(self._db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT
                    id,
                    owner_user_id,
                    job_type,
                    dedupe_key,
                    payload_json,
                    status,
                    attempt_count,
                    max_attempts,
                    rerun_requested
                FROM wordbank_background_jobs
                WHERE status = 'pending'
                  AND available_at <= CURRENT_TIMESTAMP
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None
            cursor = conn.execute(
                """
                UPDATE wordbank_background_jobs
                SET status = 'running',
                    attempt_count = attempt_count + 1,
                    rerun_requested = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'pending'
                """,
                (int(row["id"]),),
            )
            if cursor.rowcount != 1:
                return None
        return _job_from_row(
            {
                **dict(row),
                "status": "running",
                "attempt_count": int(row["attempt_count"]) + 1,
                "rerun_requested": False,
            }
        )

    def get_by_dedupe_key(self, dedupe_key: str) -> WordbankBackgroundJobRecord | None:
        with timed_db_operation("wordbank_background_jobs.get_by_dedupe_key"), get_connection(self._db_path) as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    owner_user_id,
                    job_type,
                    dedupe_key,
                    payload_json,
                    status,
                    attempt_count,
                    max_attempts,
                    rerun_requested,
                    last_error,
                    completed_at
                FROM wordbank_background_jobs
                WHERE owner_user_id = ? AND dedupe_key = ?
                LIMIT 1
                """,
                (self._owner_user_id, dedupe_key),
            ).fetchone()
        return _job_from_row(dict(row)) if row is not None else None

    def mark_completed(self, job_id: int) -> bool:
        with timed_db_operation("wordbank_background_jobs.mark_completed"), get_connection(self._db_path) as conn:
            row = conn.execute(
                """
                SELECT rerun_requested
                FROM wordbank_background_jobs
                WHERE id = ?
                LIMIT 1
                """,
                (job_id,),
            ).fetchone()
            if row is not None and bool(row["rerun_requested"]):
                conn.execute(
                    """
                    UPDATE wordbank_background_jobs
                    SET status = 'pending',
                        attempt_count = 0,
                        updated_at = CURRENT_TIMESTAMP,
                        available_at = CURRENT_TIMESTAMP,
                        last_error = NULL,
                        completed_at = NULL,
                        rerun_requested = 0
                    WHERE id = ?
                    """,
                    (job_id,),
                )
                return True
            conn.execute(
                """
                UPDATE wordbank_background_jobs
                SET status = 'completed',
                    updated_at = CURRENT_TIMESTAMP,
                    completed_at = CURRENT_TIMESTAMP,
                    last_error = NULL
                WHERE id = ?
                """,
                (job_id,),
            )
        return False

    def mark_retryable_failure(self, job: WordbankBackgroundJobRecord, *, error_message: str, retry_delay_seconds: int = 1) -> bool:
        next_status = "pending" if job.attempt_count < job.max_attempts else "failed"
        with timed_db_operation("wordbank_background_jobs.mark_retryable_failure"), get_connection(self._db_path) as conn:
            row = conn.execute(
                """
                SELECT rerun_requested
                FROM wordbank_background_jobs
                WHERE id = ?
                LIMIT 1
                """,
                (job.id,),
            ).fetchone()
            if row is not None and bool(row["rerun_requested"]):
                conn.execute(
                    """
                    UPDATE wordbank_background_jobs
                    SET status = 'pending',
                        attempt_count = 0,
                        last_error = NULL,
                        updated_at = CURRENT_TIMESTAMP,
                        available_at = CURRENT_TIMESTAMP,
                        completed_at = NULL,
                        rerun_requested = 0
                    WHERE id = ?
                    """,
                    (job.id,),
                )
                return True
            conn.execute(
                """
                UPDATE wordbank_background_jobs
                SET status = ?,
                    last_error = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    available_at = CASE
                        WHEN ? = 'pending' THEN DATETIME(CURRENT_TIMESTAMP, ?)
                        ELSE available_at
                    END
                WHERE id = ?
                """,
                (next_status, error_message, next_status, f"+{retry_delay_seconds} seconds", job.id),
            )
        return False


def _job_from_row(row: dict[str, object]) -> WordbankBackgroundJobRecord:
    return WordbankBackgroundJobRecord(
        id=_required_int(row, "id"),
        owner_user_id=_required_int(row, "owner_user_id"),
        job_type=str(row["job_type"]),
        dedupe_key=str(row["dedupe_key"]),
        payload=json.loads(str(row["payload_json"])),
        status=str(row["status"]),
        attempt_count=_required_int(row, "attempt_count"),
        max_attempts=_required_int(row, "max_attempts"),
        rerun_requested=bool(row.get("rerun_requested", False)),
        last_error=str(row["last_error"]) if row.get("last_error") is not None else None,
        completed_at=str(row["completed_at"]) if row.get("completed_at") is not None else None,
    )


def _required_int(row: dict[str, object], key: str) -> int:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Background job row is missing '{key}'.")
    return value


def _merge_pronunciation_payload(
    raw_payload_json: object,
    *,
    stored_lemma: str,
    requested_forms: list[str],
    force: bool,
) -> dict[str, object]:
    existing_payload = json.loads(str(raw_payload_json))
    existing_forms = existing_payload.get("requested_forms") if isinstance(existing_payload, dict) else None
    merged_forms: list[str] = []
    seen: set[str] = set()
    for value in existing_forms if isinstance(existing_forms, list) else []:
        if not isinstance(value, str) or not value or value in seen:
            continue
        seen.add(value)
        merged_forms.append(value)
    for value in requested_forms:
        if not value or value in seen:
            continue
        seen.add(value)
        merged_forms.append(value)

    existing_force = bool(existing_payload.get("force")) if isinstance(existing_payload, dict) else False
    return {
        "stored_lemma": stored_lemma,
        "requested_forms": merged_forms,
        "force": existing_force or force,
    }
