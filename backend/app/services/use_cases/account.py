from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.api.schemas.v1 import (
    AccountFreshStartResponse,
    AccountStatusResponse,
    ApiKeyStatus,
    TestApiKeyResponse,
    TrialOptInResponse,
    UpdateApiKeyResponse,
)
from app.db.repositories.user_api_keys import (
    SUPPORTED_PROVIDERS,
    UnknownProviderError,
    UserApiKeysRepository,
)
from app.services.use_cases.trial import TrialUseCase
from app.services.use_cases.user_data_reset import clear_user_learning_data


class GuestApiKeysForbiddenError(Exception):
    pass


class KeyStorageUnavailableError(Exception):
    pass


class UnsupportedApiKeyProviderError(Exception):
    pass


@dataclass(frozen=True)
class AccountUseCase:
    db_path: Path
    api_keys_repository: UserApiKeysRepository | None
    trial_use_case: TrialUseCase

    def _keys_repo(self) -> UserApiKeysRepository:
        if self.api_keys_repository is None:
            raise KeyStorageUnavailableError
        return self.api_keys_repository

    @staticmethod
    def _is_guest(auth_provider: str) -> bool:
        return auth_provider == "guest"

    @staticmethod
    def ensure_supported(provider: str) -> None:
        if provider not in SUPPORTED_PROVIDERS:
            raise UnsupportedApiKeyProviderError(provider)

    def status(
        self,
        *,
        user_id: int,
        auth_provider: str,
        guest_browser_id_hash: str | None,
    ) -> AccountStatusResponse:
        if self._is_guest(auth_provider):
            providers = {
                name: ApiKeyStatus(provider=name, is_set=False, last_four=None)
                for name in SUPPORTED_PROVIDERS
            }
            return AccountStatusResponse(
                keys_configured=False,
                providers=providers,
                missing=list(SUPPORTED_PROVIDERS),
                trial=self.trial_use_case.guest_status(guest_browser_id_hash or ""),
            )

        repo = self._keys_repo()
        snapshot = repo.status(user_id=user_id)
        providers = {
            name: ApiKeyStatus(provider=name, is_set=meta.is_set, last_four=meta.last_four)
            for name, meta in snapshot.items()
        }
        missing = [name for name, meta in snapshot.items() if not meta.is_set]
        return AccountStatusResponse(
            keys_configured=not missing,
            providers=providers,
            missing=missing,
            trial=self.trial_use_case.status(user_id),
        )

    def opt_in_trial(
        self,
        *,
        user_id: int,
        auth_provider: str,
        guest_browser_id_hash: str | None,
    ) -> TrialOptInResponse:
        if self._is_guest(auth_provider):
            return TrialOptInResponse(
                trial=self.trial_use_case.guest_status(guest_browser_id_hash or "")
            )
        return TrialOptInResponse(trial=self.trial_use_case.opt_in(user_id))

    def fresh_start(self, *, user_id: int) -> AccountFreshStartResponse:
        clear_user_learning_data(self.db_path, user_id, include_search_usage=False)
        return AccountFreshStartResponse(
            status="reset",
            message="Your saved words and sentences have been deleted.",
        )

    def upsert_api_key(self, *, user_id: int, auth_provider: str, provider: str, value: str) -> UpdateApiKeyResponse:
        if self._is_guest(auth_provider):
            raise GuestApiKeysForbiddenError
        self.ensure_supported(provider)
        try:
            meta = self._keys_repo().upsert(user_id=user_id, provider=provider, plaintext=value)
        except UnknownProviderError as exc:
            raise UnsupportedApiKeyProviderError(str(exc)) from None
        return UpdateApiKeyResponse(provider=meta.provider, is_set=meta.is_set, last_four=meta.last_four)

    def delete_api_key(self, *, user_id: int, auth_provider: str, provider: str) -> UpdateApiKeyResponse:
        if self._is_guest(auth_provider):
            raise GuestApiKeysForbiddenError
        self.ensure_supported(provider)
        self._keys_repo().delete(user_id=user_id, provider=provider)
        return UpdateApiKeyResponse(provider=provider, is_set=False, last_four=None)

    def test_api_key(self, *, user_id: int, auth_provider: str, provider: str) -> TestApiKeyResponse:
        if self._is_guest(auth_provider):
            raise GuestApiKeysForbiddenError
        self.ensure_supported(provider)
        plaintext = self._keys_repo().get_plaintext(user_id=user_id, provider=provider)
        if plaintext is None:
            return TestApiKeyResponse(provider=provider, ok=False, error="key_not_set")
        ok = len(plaintext.strip()) >= 8
        return TestApiKeyResponse(provider=provider, ok=ok, error=None if ok else "key_too_short")
