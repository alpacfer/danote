from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.api.schemas.v1.account import TrialStatus
from app.core.config import Settings
from app.db.repositories.user_api_keys import UserApiKeysRepository
from app.db.repositories.user_trial import UserTrialRepository

logger = logging.getLogger(__name__)

_FALLBACK_TZ = "UTC"


def normalize_query_key(query_key: str) -> str:
    """Collapse a user query to the key that identifies one distinct word/day."""
    return " ".join(query_key.strip().casefold().split())


@dataclass(frozen=True)
class TrialDecision:
    allowed: bool
    metered: bool
    used: int
    limit: int


class TrialUseCase:
    """Free-trial policy: cap daily distinct word searches for users without
    their own API keys, running on the host fallback services.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        trial_repository: UserTrialRepository,
        api_keys_repository: UserApiKeysRepository | None,
    ) -> None:
        self._settings = settings
        self._trial = trial_repository
        self._api_keys = api_keys_repository

    def _zone(self) -> ZoneInfo:
        name = self._settings.trial_reset_timezone or _FALLBACK_TZ
        try:
            return ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError):
            logger.warning("trial_reset_timezone_invalid", extra={"tz": name})
            return ZoneInfo(_FALLBACK_TZ)

    def _today(self) -> str:
        return datetime.now(self._zone()).date().isoformat()

    @staticmethod
    def _next_day(today: str) -> str:
        return (date.fromisoformat(today) + timedelta(days=1)).isoformat()

    def _keys_configured(self, user_id: int) -> bool:
        if self._api_keys is None:
            return False
        try:
            snapshot = self._api_keys.status(user_id=user_id)
        except Exception:
            logger.exception("trial_keys_status_failed", extra={"user_id": user_id})
            return False
        return bool(snapshot) and all(meta.is_set for meta in snapshot.values())

    @property
    def _limit(self) -> int:
        return max(0, int(self._settings.trial_daily_search_limit))

    def status(self, user_id: int) -> TrialStatus:
        enabled = bool(self._settings.trial_enabled)
        available = bool(self._settings.gemini_api_key)
        keys_configured = self._keys_configured(user_id)
        opted_in = self._trial.is_opted_in(user_id=user_id)
        today = self._today()
        limit = self._limit
        used = 0
        if enabled and not keys_configured:
            used = self._trial.count_for_day(user_id=user_id, usage_date=today)
        return TrialStatus(
            enabled=enabled,
            available=available,
            opted_in=opted_in,
            keys_configured=keys_configured,
            limit=limit,
            used=used,
            remaining=max(0, limit - used),
            resets_on=self._next_day(today),
        )

    def opt_in(self, user_id: int) -> TrialStatus:
        self._trial.opt_in(user_id=user_id)
        return self.status(user_id)

    def check_and_consume(self, user_id: int, query_key: str) -> TrialDecision:
        limit = self._limit
        if not self._settings.trial_enabled or self._keys_configured(user_id):
            return TrialDecision(allowed=True, metered=False, used=0, limit=limit)
        normalized = normalize_query_key(query_key)
        if not normalized:
            return TrialDecision(allowed=True, metered=False, used=0, limit=limit)
        reservation = self._trial.reserve(
            user_id=user_id,
            usage_date=self._today(),
            query_key=normalized,
            limit=limit,
        )
        return TrialDecision(
            allowed=reservation.allowed,
            metered=True,
            used=reservation.used,
            limit=reservation.limit,
        )
