from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from urllib.error import URLError
from urllib.parse import quote_plus
from urllib.request import urlopen


class TranslationError(RuntimeError):
    """Raised when a translation provider cannot return a translation."""


class TranslationService(Protocol):
    def translate_da_to_en(self, text: str) -> str | None: ...


@dataclass(frozen=True)
class MyMemoryTranslationService:
    """Minimal Danish->English translator backed by MyMemory's public API."""

    timeout_seconds: float = 4.0

    def translate_da_to_en(self, text: str) -> str | None:
        normalized = text.strip()
        if not normalized:
            return None

        endpoint = (
            "https://api.mymemory.translated.net/get"
            f"?q={quote_plus(normalized)}&langpair=da|en"
        )

        try:
            with urlopen(endpoint, timeout=self.timeout_seconds) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
        except (TimeoutError, URLError, json.JSONDecodeError) as exc:
            raise TranslationError(f"Translation provider request failed: {exc}") from exc

        response_data = payload.get("responseData")
        if not isinstance(response_data, dict):
            return None

        translated = response_data.get("translatedText")
        if not isinstance(translated, str):
            return None

        cleaned = translated.strip()
        if not cleaned:
            return None

        if cleaned.lower() == normalized.lower():
            matches = payload.get("matches")
            if isinstance(matches, list):
                for candidate in matches:
                    if not isinstance(candidate, dict):
                        continue
                    candidate_text = candidate.get("translation")
                    if isinstance(candidate_text, str) and candidate_text.strip():
                        cleaned = candidate_text.strip()
                        break

        return cleaned or None
