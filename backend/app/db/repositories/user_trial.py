from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.db.sqlite import get_connection


@dataclass(frozen=True)
class TrialReservation:
    """Outcome of attempting to count one word search against the daily cap.

    `used` is the distinct-word count for the day after this call. When the
    word was already searched today (free repeat) or the cap was hit, no row
    is inserted and `used` reflects the unchanged total.
    """

    allowed: bool
    used: int
    limit: int


class UserTrialRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def opt_in(self, *, user_id: int) -> None:
        with get_connection(self._db_path) as conn:
            conn.execute(
                """
                UPDATE app_users
                SET trial_opted_in_at = CURRENT_TIMESTAMP
                WHERE id = ? AND trial_opted_in_at IS NULL
                """,
                (user_id,),
            )

    def is_opted_in(self, *, user_id: int) -> bool:
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT trial_opted_in_at FROM app_users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return row is not None and row["trial_opted_in_at"] is not None

    def count_for_day(self, *, user_id: int, usage_date: str) -> int:
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS n
                FROM user_search_usage
                WHERE owner_user_id = ? AND usage_date = ?
                """,
                (user_id, usage_date),
            ).fetchone()
        return int(row["n"]) if row is not None else 0

    def count_guest_for_day(self, *, browser_id_hash: str, usage_date: str) -> int:
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS n
                FROM guest_search_usage
                WHERE browser_id_hash = ? AND usage_date = ?
                """,
                (browser_id_hash, usage_date),
            ).fetchone()
        return int(row["n"]) if row is not None else 0

    def reserve(
        self,
        *,
        user_id: int,
        usage_date: str,
        query_key: str,
        limit: int,
    ) -> TrialReservation:
        with get_connection(self._db_path) as conn:
            existing = conn.execute(
                """
                SELECT 1 FROM user_search_usage
                WHERE owner_user_id = ? AND usage_date = ? AND query_key = ?
                """,
                (user_id, usage_date, query_key),
            ).fetchone()
            count_row = conn.execute(
                """
                SELECT COUNT(*) AS n
                FROM user_search_usage
                WHERE owner_user_id = ? AND usage_date = ?
                """,
                (user_id, usage_date),
            ).fetchone()
            used = int(count_row["n"]) if count_row is not None else 0

            if existing is not None:
                return TrialReservation(allowed=True, used=used, limit=limit)
            if used >= limit:
                return TrialReservation(allowed=False, used=used, limit=limit)

            conn.execute(
                """
                INSERT OR IGNORE INTO user_search_usage
                    (owner_user_id, usage_date, query_key)
                VALUES (?, ?, ?)
                """,
                (user_id, usage_date, query_key),
            )
            return TrialReservation(allowed=True, used=used + 1, limit=limit)

    def reserve_guest(
        self,
        *,
        browser_id_hash: str,
        usage_date: str,
        query_key: str,
        limit: int,
    ) -> TrialReservation:
        with get_connection(self._db_path) as conn:
            existing = conn.execute(
                """
                SELECT 1 FROM guest_search_usage
                WHERE browser_id_hash = ? AND usage_date = ? AND query_key = ?
                """,
                (browser_id_hash, usage_date, query_key),
            ).fetchone()
            count_row = conn.execute(
                """
                SELECT COUNT(*) AS n
                FROM guest_search_usage
                WHERE browser_id_hash = ? AND usage_date = ?
                """,
                (browser_id_hash, usage_date),
            ).fetchone()
            used = int(count_row["n"]) if count_row is not None else 0

            if existing is not None:
                return TrialReservation(allowed=True, used=used, limit=limit)
            if used >= limit:
                return TrialReservation(allowed=False, used=used, limit=limit)

            conn.execute(
                """
                INSERT OR IGNORE INTO guest_search_usage
                    (browser_id_hash, usage_date, query_key)
                VALUES (?, ?, ?)
                """,
                (browser_id_hash, usage_date, query_key),
            )
            return TrialReservation(allowed=True, used=used + 1, limit=limit)
