from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class VerificationActionExecutionResult:
    status: Literal["applied", "skipped"]
    applied_action_type: str | None
    target_lemma: str | None
    target_meaning_id: int | None
    log_payload: dict[str, object] | None
    invalidate_targets: tuple[tuple[str, str | None], ...]
