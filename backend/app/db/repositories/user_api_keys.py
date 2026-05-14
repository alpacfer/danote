from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.db.sqlite import get_connection
from app.services.key_encryption import EncryptedSecret, KeyEncryptionService, last_four

SUPPORTED_PROVIDERS: tuple[str, ...] = (
    "gemini",
    "deepl",
    "azure_translation",
    "azure_tts",
)


@dataclass(frozen=True)
class StoredKeyMeta:
    provider: str
    last_four: str | None
    is_set: bool


class UnknownProviderError(ValueError):
    pass


def _validate_provider(provider: str) -> None:
    if provider not in SUPPORTED_PROVIDERS:
        raise UnknownProviderError(provider)


class UserApiKeysRepository:
    def __init__(self, db_path: Path, encryption: KeyEncryptionService) -> None:
        self._db_path = db_path
        self._encryption = encryption

    def upsert(self, *, user_id: int, provider: str, plaintext: str) -> StoredKeyMeta:
        _validate_provider(provider)
        cleaned = plaintext.strip()
        if not cleaned:
            raise ValueError("API key must not be empty")
        secret = self._encryption.encrypt(cleaned)
        preview = last_four(cleaned)
        with get_connection(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO user_api_keys
                    (owner_user_id, provider, ciphertext, nonce, last_four, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(owner_user_id, provider) DO UPDATE SET
                    ciphertext = excluded.ciphertext,
                    nonce = excluded.nonce,
                    last_four = excluded.last_four,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, provider, secret.ciphertext, secret.nonce, preview),
            )
        return StoredKeyMeta(provider=provider, last_four=preview, is_set=True)

    def delete(self, *, user_id: int, provider: str) -> None:
        _validate_provider(provider)
        with get_connection(self._db_path) as conn:
            conn.execute(
                "DELETE FROM user_api_keys WHERE owner_user_id = ? AND provider = ?",
                (user_id, provider),
            )

    def get_plaintext(self, *, user_id: int, provider: str) -> str | None:
        _validate_provider(provider)
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT ciphertext, nonce FROM user_api_keys WHERE owner_user_id = ? AND provider = ?",
                (user_id, provider),
            ).fetchone()
        if row is None:
            return None
        return self._encryption.decrypt(
            EncryptedSecret(ciphertext=bytes(row["ciphertext"]), nonce=bytes(row["nonce"]))
        )

    def get_all_plaintext(self, *, user_id: int) -> dict[str, str]:
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                "SELECT provider, ciphertext, nonce FROM user_api_keys WHERE owner_user_id = ?",
                (user_id,),
            ).fetchall()
        result: dict[str, str] = {}
        for row in rows:
            try:
                result[str(row["provider"])] = self._encryption.decrypt(
                    EncryptedSecret(
                        ciphertext=bytes(row["ciphertext"]),
                        nonce=bytes(row["nonce"]),
                    )
                )
            except Exception:
                # Skip records that fail to decrypt (e.g. master key rotated).
                # The user will see them as "not set" in the UI and can re-enter.
                continue
        return result

    def status(self, *, user_id: int) -> dict[str, StoredKeyMeta]:
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                "SELECT provider, last_four FROM user_api_keys WHERE owner_user_id = ?",
                (user_id,),
            ).fetchall()
        stored = {
            str(row["provider"]): str(row["last_four"]) if row["last_four"] is not None else None
            for row in rows
        }
        return {
            provider: StoredKeyMeta(
                provider=provider,
                last_four=stored.get(provider),
                is_set=provider in stored,
            )
            for provider in SUPPORTED_PROVIDERS
        }
