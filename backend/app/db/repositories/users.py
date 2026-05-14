from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.db.sqlite import get_connection


@dataclass(frozen=True)
class AppUserRecord:
    id: int
    auth_provider: str
    auth_subject: str
    email: str | None
    display_name: str | None
    created_at: str
    last_seen_at: str


def _row_to_record(row) -> AppUserRecord:
    return AppUserRecord(
        id=int(row["id"]),
        auth_provider=str(row["auth_provider"]),
        auth_subject=str(row["auth_subject"]),
        email=row["email"],
        display_name=row["display_name"],
        created_at=str(row["created_at"]),
        last_seen_at=str(row["last_seen_at"]),
    )


class AppUserRepository:
    """Identity records for authenticated users.

    Upserts on first sign-in so we always have a local row for an auth token.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def upsert_user(
        self,
        *,
        auth_provider: str,
        auth_subject: str,
        email: str | None,
        display_name: str | None,
    ) -> AppUserRecord:
        with get_connection(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO app_users (auth_provider, auth_subject, email, display_name, last_seen_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(auth_provider, auth_subject) DO UPDATE SET
                    email = excluded.email,
                    display_name = excluded.display_name,
                    last_seen_at = CURRENT_TIMESTAMP
                """,
                (auth_provider, auth_subject, email, display_name),
            )
            row = conn.execute(
                """
                SELECT id, auth_provider, auth_subject, email, display_name, created_at, last_seen_at
                FROM app_users
                WHERE auth_provider = ? AND auth_subject = ?
                """,
                (auth_provider, auth_subject),
            ).fetchone()
        if row is None:
            raise RuntimeError("user upsert failed to return a row")
        return _row_to_record(row)

    def get_by_id(self, user_id: int) -> AppUserRecord | None:
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT id, auth_provider, auth_subject, email, display_name, created_at, last_seen_at FROM app_users WHERE id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return _row_to_record(row)
