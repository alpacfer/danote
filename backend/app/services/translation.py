from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Protocol

import httpx


class TranslationError(RuntimeError):
    """Raised when a translation provider cannot return a translation."""


class TranslationService(Protocol):
    def translate_da_to_en(self, text: str) -> str | None: ...


@dataclass
class DeepLTranslationService:
    """Danish->English translator backed by the DeepL API."""

    api_key: str
    source_code: str = "DA"
    target_code: str = "EN-US"
    context_template: str = (
        "Dette er et dansk ord fra en elevnote. "
        "Giv en fuld engelsk oversaettelse som frase. "
        "For bestemt form brug artikel, fx \"the ...\"."
    )
    homograph_disambiguation_template: str = (
        "Kildeteksten er dansk. "
        "Ordet \"{word}\" er et dansk substantiv, ikke et engelsk verbum. "
        "Giv den bedste naturlige engelske oversaettelse."
    )
    homograph_disambiguation_tokens: tuple[str, ...] = ("is",)
    homograph_fallback_translations: dict[str, str] = field(
        default_factory=lambda: {"is": "ice cream"}
    )
    base_url: str | None = None
    timeout_seconds: float = 10.0
    max_retries: int = 5
    backoff_seconds: float = 0.5
    max_backoff_seconds: float = 8.0
    min_request_interval_seconds: float = 0.35
    _client: httpx.Client | None = field(default=None, init=False, repr=False, compare=False)
    _next_allowed_request_at: float = field(default=0.0, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        normalized_key = self.api_key.strip()
        if not normalized_key:
            raise TranslationError("DeepL API key is required for translation.")
        self.api_key = normalized_key

        if self.base_url is None:
            self.base_url = "https://api-free.deepl.com" if normalized_key.endswith(":fx") else "https://api.deepl.com"

        self.homograph_disambiguation_tokens = tuple(
            token.strip().lower() for token in self.homograph_disambiguation_tokens if token.strip()
        )
        self.homograph_fallback_translations = {
            self._normalize_for_compare(source): target.strip()
            for source, target in self.homograph_fallback_translations.items()
            if source.strip() and target.strip()
        }

    def _ensure_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds)
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def translate_da_to_en(self, text: str) -> str | None:
        normalized = text.strip()
        if not normalized:
            return None

        cleaned = self._translate_with_context(text=normalized, context=self.context_template)
        if cleaned is None:
            return None

        if self._should_disambiguate(source_text=normalized, translated_text=cleaned):
            source_normalized = self._normalize_for_compare(normalized)
            try:
                disambiguated = self._translate_with_context(
                    text=normalized,
                    context=self.homograph_disambiguation_template.format(word=normalized),
                )
            except TranslationError:
                disambiguated = None
            if disambiguated and self._normalize_for_compare(disambiguated) != source_normalized:
                return disambiguated
            fallback = self.homograph_fallback_translations.get(source_normalized)
            if fallback:
                return fallback

        return cleaned

    def _translate_with_context(self, *, text: str, context: str) -> str | None:
        payload = {
            "text": [text],
            "source_lang": self.source_code,
            "target_lang": self.target_code,
            "context": context,
        }

        headers = {"Authorization": f"DeepL-Auth-Key {self.api_key}"}

        response = self._post_with_retry(payload=payload, headers=headers)

        try:
            body = response.json()
        except ValueError as exc:
            raise TranslationError("DeepL translation response was not valid JSON.") from exc

        entries = body.get("translations")
        if not isinstance(entries, list) or not entries:
            return None

        first = entries[0]
        translated = first.get("text") if isinstance(first, dict) else None

        cleaned = translated.strip() if isinstance(translated, str) else ""
        return cleaned or None

    def _should_disambiguate(self, *, source_text: str, translated_text: str) -> bool:
        source_normalized = self._normalize_for_compare(source_text)
        translated_normalized = self._normalize_for_compare(translated_text)
        return (
            source_normalized == translated_normalized
            and source_normalized in self.homograph_disambiguation_tokens
        )

    @staticmethod
    def _normalize_for_compare(text: str) -> str:
        return " ".join(text.strip().lower().split())

    def _post_with_retry(self, *, payload: dict[str, object], headers: dict[str, str]) -> httpx.Response:
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            try:
                self._enforce_request_interval()
                response = self._ensure_client().post("/v2/translate", json=payload, headers=headers)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code if exc.response is not None else 0
                should_retry = status_code in {429, 500, 502, 503, 504}
                if should_retry and attempt < self.max_retries:
                    self._sleep_before_retry(attempt=attempt, response=exc.response)
                    continue
                raise TranslationError(f"DeepL translation request failed with status {status_code}.") from exc
            except httpx.HTTPError as exc:
                if attempt < self.max_retries:
                    self._sleep_before_retry(attempt=attempt, response=None)
                    continue
                raise TranslationError(f"DeepL translation request failed: {exc}") from exc

        raise TranslationError("DeepL translation request failed after retries.")

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
