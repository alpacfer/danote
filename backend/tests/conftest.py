from __future__ import annotations

import pytest

from app.core.config import DATA_DIR
from app.nlp.adapter import NLPToken
from tests.helpers.artifact_restore import FileSnapshot, capture_file_snapshot, restore_file_snapshot


_GEMINI_CHANGES_LOG_PATH = DATA_DIR / "gemini-applied-changes.jsonl"
_gemini_changes_log_snapshot: FileSnapshot | None = None


class StubNLPAdapter:
    def tokenize(self, text: str) -> list[NLPToken]:
        return []

    def lemma_candidates_for_token(self, token: str) -> list[str]:
        return []

    def lemma_for_token(self, token: str) -> str | None:
        return None

    def metadata(self) -> dict[str, str]:
        return {"adapter": "StubNLPAdapter"}


@pytest.fixture
def stub_nlp_adapter_factory():
    return lambda _settings: StubNLPAdapter()


def pytest_sessionstart(session) -> None:
    del session
    global _gemini_changes_log_snapshot
    _gemini_changes_log_snapshot = capture_file_snapshot(_GEMINI_CHANGES_LOG_PATH)


def pytest_sessionfinish(session, exitstatus: int) -> None:
    del session, exitstatus
    if _gemini_changes_log_snapshot is None:
        return
    restore_file_snapshot(_gemini_changes_log_snapshot)
