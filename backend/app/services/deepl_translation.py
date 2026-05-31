from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

import httpx

from app.services.translation import TranslationError
from app.services.translation_result_cache import TranslationResultCache


@dataclass
class DeepLTranslationService:
    """Danish/English translation service backed by DeepL API."""

    api_key: str
    endpoint: str | None = None
    timeout_seconds: float = 10.0
    max_retries: int = 5
    backoff_seconds: float = 0.5
    max_backoff_seconds: float = 8.0
    min_request_interval_seconds: float = 0.35
    max_cache_entries: int = 2048
    provider: str = field(default="deepl_translator", init=False)
    _client: httpx.Client | None = field(default=None, init=False, repr=False, compare=False)
    _next_allowed_request_at: float = field(default=0.0, init=False, repr=False, compare=False)
    _cache: TranslationResultCache = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        normalized_key = self.api_key.strip()
        if not normalized_key:
            raise TranslationError("DeepL API key is required for translation.")
        self.api_key = normalized_key
        self.endpoint = self._normalize_endpoint(self.endpoint, api_key=normalized_key)
        self._cache = TranslationResultCache(self.max_cache_entries)

    def _ensure_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(base_url=self.endpoint, timeout=self.timeout_seconds)
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def clear_cache(self) -> None:
        self._cache.clear()

    def translate_da_to_en(self, text: str) -> str | None:
        normalized = text.strip()
        if not normalized:
            return None
        translated = self._translate_many(texts=[normalized], source_lang="DA", target_lang="EN")
        return translated[0] if translated else None

    def translate_da_to_en_batch(self, texts: list[str]) -> list[str | None]:
        normalized = [t.strip() for t in texts]
        if not normalized or all(not t for t in normalized):
            return [None] * len(texts)

        results: list[str | None] = [None] * len(texts)
        indexed_non_empty = [(index, value) for index, value in enumerate(normalized) if value]
        for chunk_start in range(0, len(indexed_non_empty), 50):
            chunk = indexed_non_empty[chunk_start : chunk_start + 50]
            chunk_texts = [value for _, value in chunk]
            translated_chunk = self._translate_many(texts=chunk_texts, source_lang="DA", target_lang="EN")
            for (index, _), translated in zip(chunk, translated_chunk, strict=False):
                results[index] = translated
        return results

    def translate_en_to_da(self, text: str) -> str | None:
        normalized = text.strip()
        if not normalized:
            return None
        translated = self._translate_many(texts=[normalized], source_lang="EN", target_lang="DA")
        return translated[0] if translated else None

    def detect_source_language(self, text: str) -> str | None:
        normalized = text.strip()
        if not normalized:
            return None
        response = self._post_with_retry(
            payload={
                "text": [normalized],
                "target_lang": "EN",
            }
        )
        try:
            body = response.json()
        except ValueError as exc:
            raise TranslationError("DeepL language detection response was not valid JSON.") from exc
        translations = body.get("translations") if isinstance(body, dict) else None
        if not isinstance(translations, list) or not translations:
            return None
        first = translations[0]
        detected = first.get("detected_source_language") if isinstance(first, dict) else None
        cleaned = detected.strip().upper() if isinstance(detected, str) else ""
        return cleaned or None

    def _translate_many(
        self,
        *,
        texts: list[str],
        source_lang: str | None,
        target_lang: str,
    ) -> list[str | None]:
        direction = f"{source_lang or 'auto'}:{target_lang}"
        results = [self._cache.get(direction, text) for text in texts]
        missing = list(dict.fromkeys(
            text for text, result in zip(texts, results, strict=False)
            if text and result is None
        ))
        if not missing:
            return results
        response = self._post_with_retry(
            payload={
                "text": missing,
                "target_lang": target_lang,
                "source_lang": source_lang,
            }
        )
        try:
            body = response.json()
        except ValueError as exc:
            raise TranslationError("DeepL translation response was not valid JSON.") from exc
        translations = body.get("translations") if isinstance(body, dict) else None
        if not isinstance(translations, list):
            return results
        translated_by_text: dict[str, str | None] = {}
        for text, item in zip(missing, translations, strict=False):
            translated = item.get("text") if isinstance(item, dict) else None
            cleaned = translated.strip() if isinstance(translated, str) else ""
            value = cleaned.lower() if cleaned else None
            translated_by_text[text] = value
            self._cache.put(direction, text, value)
        return [
            result if result is not None else translated_by_text.get(text)
            for text, result in zip(texts, results, strict=False)
        ]

    def _post_with_retry(
        self,
        *,
        payload: dict[str, object],
    ) -> httpx.Response:
        attempts = self.max_retries + 1
        headers = {
            "Authorization": f"DeepL-Auth-Key {self.api_key}",
            "Content-Type": "application/json",
        }
        for attempt in range(attempts):
            try:
                self._enforce_request_interval()
                response = self._ensure_client().post("/v2/translate", content=json.dumps(payload), headers=headers)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code if exc.response is not None else 0
                should_retry = status_code in {408, 429, 500, 502, 503, 504}
                if should_retry and attempt < self.max_retries:
                    self._sleep_before_retry(attempt=attempt, response=exc.response)
                    continue
                raise TranslationError(
                    f"DeepL translation request failed with status {status_code}."
                ) from exc
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

    @staticmethod
    def _normalize_endpoint(endpoint: str | None, *, api_key: str) -> str:
        if isinstance(endpoint, str) and endpoint.strip():
            return endpoint.strip().rstrip("/")
        if api_key.endswith(":fx"):
            return "https://api-free.deepl.com"
        return "https://api.deepl.com"
