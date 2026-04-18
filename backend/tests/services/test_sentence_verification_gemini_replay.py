from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.services.sentence_verification import (
    GeminiSentenceVerificationService,
    SentenceVerificationErrorSpan,
    SentenceVerificationResult,
)
from tests.helpers.paths import FIXTURES_DIR


_FIXTURE_DIR = FIXTURES_DIR / "gemini" / "sentence_verification"


@dataclass(frozen=True, slots=True)
class _RecordedSentenceVerificationFixture:
    path: Path
    source_text: str
    raw_response: str | None
    expected: SentenceVerificationResult


def _load_fixture(path: Path) -> _RecordedSentenceVerificationFixture:
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected_payload = payload["expected"]
    return _RecordedSentenceVerificationFixture(
        path=path,
        source_text=str(payload["source_text"]),
        raw_response=payload.get("raw_response"),
        expected=SentenceVerificationResult(
            is_valid=bool(expected_payload["is_valid"]),
            errors=[
                SentenceVerificationErrorSpan(
                    start=int(error["start"]),
                    end=int(error["end"]),
                    message=str(error["message"]),
                )
                for error in expected_payload.get("errors", [])
            ],
            corrected_text=expected_payload.get("corrected_text"),
            language=str(expected_payload.get("language", "unknown")),
        ),
    )


_FIXTURE_PATHS = sorted(_FIXTURE_DIR.glob("*.json"))


@pytest.mark.skipif(not _FIXTURE_PATHS, reason="No recorded Gemini sentence verification fixtures are present.")
@pytest.mark.parametrize("fixture_path", _FIXTURE_PATHS, ids=lambda path: path.stem)
def test_verify_sentence_replays_recorded_gemini_response(
    fixture_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _load_fixture(fixture_path)
    service = GeminiSentenceVerificationService(api_key="test-key")
    prompts: list[str] = []

    def _fake_generate_text(prompt: str) -> str | None:
        prompts.append(prompt)
        return fixture.raw_response

    monkeypatch.setattr(service, "_generate_text", _fake_generate_text)

    result = service.verify_sentence(fixture.source_text)

    assert prompts, f"expected verify_sentence to generate a prompt for {fixture.path.name}"
    assert fixture.source_text in prompts[0]
    assert result == fixture.expected
