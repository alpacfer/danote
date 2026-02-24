from __future__ import annotations

import pytest

from app.nlp.adapter import NLPToken


class StubNLPAdapter:
    def tokenize(self, text: str) -> list[NLPToken]:
        return []

    def lemma_for_token(self, token: str) -> str | None:
        return None

    def metadata(self) -> dict[str, str]:
        return {"adapter": "StubNLPAdapter"}


@pytest.fixture
def stub_nlp_adapter_factory():
    return lambda _settings: StubNLPAdapter()
