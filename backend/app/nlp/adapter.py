from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class NLPToken:
    text: str
    lemma: str | None
    pos: str | None
    morphology: str | None
    is_punctuation: bool


class NLPAdapter(Protocol):
    def tokenize(self, text: str) -> list[NLPToken]:
        ...

    def lemma_for_token(self, token: str) -> str | None:
        ...

    def metadata(self) -> dict[str, str]:
        ...
