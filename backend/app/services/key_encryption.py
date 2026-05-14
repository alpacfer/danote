from __future__ import annotations

import base64
import os
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# 32 bytes -> AES-256-GCM. 12-byte nonce is the recommended AESGCM size.
_KEY_BYTES = 32
_NONCE_BYTES = 12


class KeyEncryptionConfigError(RuntimeError):
    """Master encryption key is missing or malformed."""


class KeyDecryptionError(RuntimeError):
    """Stored ciphertext could not be decrypted (wrong master key or corruption)."""


@dataclass(frozen=True)
class EncryptedSecret:
    ciphertext: bytes
    nonce: bytes


class KeyEncryptionService:
    """Encrypts and decrypts user-provided API keys at rest with AES-GCM."""

    def __init__(self, master_key: bytes) -> None:
        if len(master_key) != _KEY_BYTES:
            raise KeyEncryptionConfigError(
                f"master key must be {_KEY_BYTES} bytes, got {len(master_key)}"
            )
        self._aead = AESGCM(master_key)

    @classmethod
    def from_base64_secret(cls, secret_b64: str) -> KeyEncryptionService:
        try:
            raw = base64.b64decode(secret_b64, validate=True)
        except (ValueError, base64.binascii.Error) as exc:  # type: ignore[attr-defined]
            raise KeyEncryptionConfigError(
                "DANOTE_KEY_ENCRYPTION_SECRET must be valid base64"
            ) from exc
        return cls(raw)

    def encrypt(self, plaintext: str) -> EncryptedSecret:
        nonce = os.urandom(_NONCE_BYTES)
        ciphertext = self._aead.encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)
        return EncryptedSecret(ciphertext=ciphertext, nonce=nonce)

    def decrypt(self, secret: EncryptedSecret) -> str:
        try:
            plaintext = self._aead.decrypt(secret.nonce, secret.ciphertext, associated_data=None)
        except InvalidTag as exc:
            raise KeyDecryptionError(
                "stored API key could not be decrypted; master key may have changed"
            ) from exc
        return plaintext.decode("utf-8")


def last_four(plaintext: str) -> str:
    """A masked preview for the UI: last 4 chars or fewer if the secret is short."""
    cleaned = plaintext.strip()
    return cleaned[-4:] if len(cleaned) >= 4 else cleaned
