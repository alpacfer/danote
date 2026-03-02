from __future__ import annotations

from dataclasses import dataclass, field
import json
import time
from typing import Protocol

import httpx


class TranslationError(RuntimeError):
    """Raised when a translation provider cannot return a translation."""


class TranslationService(Protocol):
    provider: str

    def translate_da_to_en(self, text: str) -> str | None: ...
    def translate_en_to_da(self, text: str) -> str | None: ...
    def detect_source_language(self, text: str) -> str | None: ...


@dataclass
class AzureTranslationService:
    """Danish/English translation service backed by Azure Translator."""

    api_key: str
    region: str
    endpoint: str | None = None
    api_version: str = "3.0"
    timeout_seconds: float = 10.0
    max_retries: int = 5
    backoff_seconds: float = 0.5
    max_backoff_seconds: float = 8.0
    min_request_interval_seconds: float = 0.35
    provider: str = field(default="azure_translator", init=False)
    _client: httpx.Client | None = field(default=None, init=False, repr=False, compare=False)
    _next_allowed_request_at: float = field(default=0.0, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        normalized_key = self.api_key.strip()
        normalized_region = self.region.strip()
        normalized_version = self.api_version.strip()
        if not normalized_key:
            raise TranslationError("Azure Translator API key is required for translation.")
        if not normalized_region:
            raise TranslationError("Azure Translator region is required for translation.")
        if not normalized_version:
            raise TranslationError("Azure Translator API version is required for translation.")
        self.api_key = normalized_key
        self.region = normalized_region
        self.api_version = normalized_version
        self.endpoint = self._normalize_endpoint(self.endpoint)

    def _ensure_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(base_url=self.endpoint, timeout=self.timeout_seconds)
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def translate_da_to_en(self, text: str) -> str | None:
        normalized = text.strip()
        if not normalized:
            return None
        return self._translate_text(text=normalized, source_code="da", target_code="en")

    def translate_en_to_da(self, text: str) -> str | None:
        normalized = text.strip()
        if not normalized:
            return None
        return self._translate_text(text=normalized, source_code="en", target_code="da")

    def detect_source_language(self, text: str) -> str | None:
        normalized = text.strip()
        if not normalized:
            return None

        response = self._post_with_retry(
            path="/detect",
            params={"api-version": self.api_version},
            payload=[{"Text": normalized}],
        )
        try:
            body = response.json()
        except ValueError as exc:
            raise TranslationError("Azure language detection response was not valid JSON.") from exc
        if not isinstance(body, list) or not body:
            return None
        first = body[0]
        language = first.get("language") if isinstance(first, dict) else None
        cleaned = language.strip().upper() if isinstance(language, str) else ""
        return cleaned or None

    def _translate_text(self, *, text: str, source_code: str, target_code: str) -> str | None:
        response = self._post_with_retry(
            path="/translate",
            params={
                "api-version": self.api_version,
                "from": source_code,
                "to": target_code,
            },
            payload=[{"Text": text}],
        )

        try:
            body = response.json()
        except ValueError as exc:
            raise TranslationError("Azure translation response was not valid JSON.") from exc
        if not isinstance(body, list) or not body:
            return None
        first = body[0]
        translations = first.get("translations") if isinstance(first, dict) else None
        if not isinstance(translations, list) or not translations:
            return None
        candidate = translations[0]
        translated = candidate.get("text") if isinstance(candidate, dict) else None
        cleaned = translated.strip() if isinstance(translated, str) else ""
        if not cleaned:
            return None
        return cleaned.lower()

    def _post_with_retry(
        self,
        *,
        path: str,
        params: dict[str, object],
        payload: list[dict[str, str]],
    ) -> httpx.Response:
        attempts = self.max_retries + 1
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Ocp-Apim-Subscription-Region": self.region,
            "Content-Type": "application/json",
        }
        for attempt in range(attempts):
            try:
                self._enforce_request_interval()
                response = self._ensure_client().post(path, params=params, content=json.dumps(payload), headers=headers)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code if exc.response is not None else 0
                should_retry = status_code in {408, 429, 500, 502, 503, 504}
                if should_retry and attempt < self.max_retries:
                    self._sleep_before_retry(attempt=attempt, response=exc.response)
                    continue
                raise TranslationError(
                    f"Azure translation request failed with status {status_code}."
                ) from exc
            except httpx.HTTPError as exc:
                if attempt < self.max_retries:
                    self._sleep_before_retry(attempt=attempt, response=None)
                    continue
                raise TranslationError(f"Azure translation request failed: {exc}") from exc

        raise TranslationError("Azure translation request failed after retries.")

    def _sleep_before_retry(self, *, attempt: int, response: httpx.Response | None) -> None:
        retry_after = response.headers.get("Retry-After") if response is not None else None
        if retry_after:
            try:
                delay = float(retry_after)
            except ValueError:
                delay = self.backoff_seconds * (2**attempt)
        else:
            delay = self.backoff_seconds * (2**attempt)

        delay = max(0.0, min(delay, self.max_backoff_seconds))
        if delay > 0:
            time.sleep(delay)

    def _enforce_request_interval(self) -> None:
        if self.min_request_interval_seconds <= 0:
            return
        now = time.monotonic()
        if now < self._next_allowed_request_at:
            time.sleep(self._next_allowed_request_at - now)
        self._next_allowed_request_at = time.monotonic() + self.min_request_interval_seconds

    @staticmethod
    def _normalize_endpoint(endpoint: str | None) -> str:
        if not isinstance(endpoint, str) or not endpoint.strip():
            return "https://api.cognitive.microsofttranslator.com"
        return endpoint.strip().rstrip("/")
