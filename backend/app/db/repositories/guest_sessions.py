from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from pathlib import Path

from app.db.repositories.users import AppUserRecord, AppUserRepository
from app.db.sqlite import get_connection

GUEST_TOKEN_PREFIX = "guest_"


@dataclass(frozen=True)
class GuestSessionRecord:
    token: str
    browser_id_hash: str
    user: AppUserRecord


def hash_guest_browser_id(browser_id: str) -> str:
    normalized = browser_id.strip()
    if not normalized:
        raise ValueError("browser_id_required")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def hash_guest_token(token: str) -> str:
    normalized = token.strip()
    if not normalized.startswith(GUEST_TOKEN_PREFIX):
        raise ValueError("invalid_guest_token")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class GuestSessionRepository:
    def __init__(self, db_path: Path, users_repository: AppUserRepository) -> None:
        self._db_path = db_path
        self._users = users_repository

    def create(self, *, browser_id: str) -> GuestSessionRecord:
        browser_id_hash = hash_guest_browser_id(browser_id)
        token = f"{GUEST_TOKEN_PREFIX}{secrets.token_urlsafe(32)}"
        token_hash = hash_guest_token(token)
        auth_subject = f"guest-{secrets.token_urlsafe(18)}"
        user = self._users.create_guest_user(auth_subject=auth_subject)
        with get_connection(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO guest_sessions (owner_user_id, token_hash, browser_id_hash)
                VALUES (?, ?, ?)
                """,
                (user.id, token_hash, browser_id_hash),
            )
        return GuestSessionRecord(token=token, browser_id_hash=browser_id_hash, user=user)

    def get_by_token(self, token: str) -> tuple[AppUserRecord, str] | None:
        try:
            token_hash = hash_guest_token(token)
        except ValueError:
            return None
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                """
                SELECT
                  u.id, u.auth_provider, u.auth_subject, u.email, u.display_name,
                  u.created_at, u.last_seen_at, gs.browser_id_hash
                FROM guest_sessions gs
                JOIN app_users u ON u.id = gs.owner_user_id
                WHERE gs.token_hash = ?
                """,
                (token_hash,),
            ).fetchone()
            if row is not None:
                conn.execute(
                    "UPDATE guest_sessions SET last_seen_at = CURRENT_TIMESTAMP WHERE token_hash = ?",
                    (token_hash,),
                )
        if row is None:
            return None
        user = AppUserRecord(
            id=int(row["id"]),
            auth_provider=str(row["auth_provider"]),
            auth_subject=str(row["auth_subject"]),
            email=row["email"],
            display_name=row["display_name"],
            created_at=str(row["created_at"]),
            last_seen_at=str(row["last_seen_at"]),
        )
        return user, str(row["browser_id_hash"])
