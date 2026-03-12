from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProviderFailureReason(str, Enum):
    NOT_CONFIGURED = "not_configured"
    AUTH = "auth"
    TIMEOUT = "timeout"
    NETWORK = "network"
    PARSE = "parse"
    PROVIDER = "provider"


@dataclass(frozen=True, slots=True)
class ProviderCallFailure:
    provider: str
    operation: str
    reason: ProviderFailureReason
    exception_class: str | None
    retryable: bool


@dataclass(frozen=True, slots=True)
class ProviderCallResult:
    value: str | int | None
    failure: ProviderCallFailure | None = None

    @property
    def ok(self) -> bool:
        return self.failure is None
