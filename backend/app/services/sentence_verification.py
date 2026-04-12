from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.services.gemini_translation_helpers import is_retryable_exception


class SentenceVerificationError(RuntimeError):
    """Raised when Gemini sentence verification cannot complete."""


@dataclass(frozen=True, slots=True)
class SentenceVerificationErrorSpan:
    start: int    # char offset, inclusive
    end: int      # char offset, exclusive
    message: str


@dataclass(frozen=True, slots=True)
class SentenceVerificationResult:
    is_valid: bool
    errors: list[SentenceVerificationErrorSpan]
    corrected_text: str | None
    language: Literal["da", "en", "unknown"]


class SentenceVerificationService(Protocol):
    def verify_sentence(self, source_text: str) -> SentenceVerificationResult: ...


def _build_prompt(source_text: str) -> str:
    return (
        "You are a Danish language expert.\n"
        f'Check this text for typos and grammatical errors: "{source_text}"\n\n'
        "Return JSON only:\n"
        '- "is_valid": true if no errors, false otherwise\n'
        '- "errors": array of {start, end, message} with 0-indexed char offsets for each error; empty if valid\n'
        '- "corrected_text": fully corrected sentence string if is_valid is false, null if is_valid is true\n'
        '- "language": "da" if Danish, "en" if English, "unknown" otherwise\n'
        "Keep the same capitalization style at the start of the sentence as the source text.\n"
        "Do not flag sentence-initial capitalization by itself as an error.\n"
        "Never add a trailing period to corrected_text unless the source text already ends with a period."
    )


def _preserve_leading_letter_case(source_text: str, corrected_text: str | None) -> str | None:
    if not corrected_text:
        return None

    source_index = next((idx for idx, char in enumerate(source_text) if char.isalpha()), None)
    corrected_index = next((idx for idx, char in enumerate(corrected_text) if char.isalpha()), None)
    if source_index is None or corrected_index is None:
        return corrected_text

    source_char = source_text[source_index]
    corrected_char = corrected_text[corrected_index]
    if source_char.islower() and corrected_char.isupper():
        return (
            corrected_text[:corrected_index]
            + corrected_char.lower()
            + corrected_text[corrected_index + 1:]
        )
    if source_char.isupper() and corrected_char.islower():
        return (
            corrected_text[:corrected_index]
            + corrected_char.upper()
            + corrected_text[corrected_index + 1:]
        )
    return corrected_text


def _preserve_terminal_period_style(source_text: str, corrected_text: str | None) -> str | None:
    if not corrected_text:
        return None

    trimmed_source = source_text.rstrip()
    trimmed_corrected = corrected_text.rstrip()
    if not trimmed_corrected.endswith(".") or trimmed_source.endswith("."):
        return corrected_text

    without_period = trimmed_corrected[:-1].rstrip()
    trailing_whitespace = corrected_text[len(trimmed_corrected):]
    return without_period + trailing_whitespace


def _is_ignorable_case_only_error(
    error: SentenceVerificationErrorSpan,
    source_text: str,
    corrected_text: str | None,
) -> bool:
    if not corrected_text:
        return False

    start = max(error.start, 0)
    end = min(error.end, len(source_text), len(corrected_text))
    if start >= end:
        return False

    source_slice = source_text[start:end]
    corrected_slice = corrected_text[start:end]
    if len(source_slice) != len(corrected_slice):
        return False

    return source_slice != corrected_slice and source_slice.casefold() == corrected_slice.casefold()


def _parse_result(raw: str | None, source_text: str) -> SentenceVerificationResult:
    if not raw:
        return SentenceVerificationResult(is_valid=True, errors=[], corrected_text=None, language="unknown")
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return SentenceVerificationResult(is_valid=True, errors=[], corrected_text=None, language="unknown")

    is_valid = bool(data.get("is_valid", True))
    raw_language = data.get("language", "unknown")
    language: Literal["da", "en", "unknown"] = raw_language if raw_language in ("da", "en") else "unknown"
    raw_corrected_text = data.get("corrected_text") or None
    corrected_text = _preserve_terminal_period_style(
        source_text,
        _preserve_leading_letter_case(source_text, raw_corrected_text),
    )
    raw_errors = data.get("errors") or []
    errors: list[SentenceVerificationErrorSpan] = []
    for e in raw_errors:
        if not isinstance(e, dict):
            continue
        start = e.get("start")
        end = e.get("end")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        errors.append(SentenceVerificationErrorSpan(
            start=start,
            end=end,
            message=str(e.get("message", "")),
        ))
    filtered_errors = [
        error for error in errors
        if not _is_ignorable_case_only_error(error, source_text, raw_corrected_text)
    ]
    normalized_is_valid = is_valid if filtered_errors else True
    normalized_corrected_text = (
        None
        if (
            corrected_text is None
            or (
                not filtered_errors
                and corrected_text.casefold() == source_text.casefold()
            )
        )
        else corrected_text
    )
    return SentenceVerificationResult(
        is_valid=normalized_is_valid,
        errors=filtered_errors,
        corrected_text=normalized_corrected_text,
        language=language,
    )


@dataclass
class GeminiSentenceVerificationService:
    """Danish sentence grammar/typo checker backed by Gemini."""

    api_key: str
    model: str = "gemini-3.1-flash-lite-preview"
    timeout_seconds: float = 20.0
    max_retries: int = 2
    backoff_seconds: float = 0.5
    _client: object | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        normalized_key = self.api_key.strip()
        normalized_model = self.model.strip()
        if not normalized_key:
            raise SentenceVerificationError("Gemini API key is required.")
        if not normalized_model:
            raise SentenceVerificationError("Gemini model is required.")
        self.api_key = normalized_key
        self.model = normalized_model

    def verify_sentence(self, source_text: str) -> SentenceVerificationResult:
        prompt = _build_prompt(source_text)
        raw = self._generate_text(prompt)
        return _parse_result(raw, source_text)

    def close(self) -> None:
        self._client = None

    def _ensure_client(self) -> object:
        if self._client is None:
            try:
                from google import genai  # type: ignore import-not-found
            except ImportError as exc:
                raise SentenceVerificationError("google-genai package required.") from exc
            genai_types = self._genai_types()
            timeout_ms = max(1, math.ceil(self.timeout_seconds * 1000))
            self._client = genai.Client(
                api_key=self.api_key,
                http_options=genai_types.HttpOptions(timeout=timeout_ms),
            )
        return self._client

    def _genai_types(self) -> object:
        try:
            from google.genai import types as genai_types  # type: ignore import-not-found
        except ImportError as exc:
            raise SentenceVerificationError("google-genai package required.") from exc
        return genai_types

    def _response_config(self) -> object:
        genai_types = self._genai_types()
        return genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "is_valid": {"type": "BOOLEAN"},
                    "errors": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "start": {"type": "INTEGER"},
                                "end": {"type": "INTEGER"},
                                "message": {"type": "STRING"},
                            },
                            "required": ["start", "end", "message"],
                        },
                    },
                    "corrected_text": {"type": "STRING", "nullable": True},
                    "language": {
                        "type": "STRING",
                        "enum": ["da", "en", "unknown"],
                    },
                },
                "required": ["is_valid", "errors", "corrected_text", "language"],
            },
            temperature=0,
            max_output_tokens=256,
            thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
        )

    def _generate_text(self, prompt: str) -> str | None:
        response = self._generate_content(prompt, config=self._response_config())
        text = getattr(response, "text", None)
        cleaned = text.strip() if isinstance(text, str) else ""
        return cleaned or None

    def _generate_content(self, prompt: str, *, config: object | None = None) -> object:
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            try:
                client = self._ensure_client()
                return client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
            except Exception as exc:
                if attempt < self.max_retries and self._is_retryable_exception(exc):
                    delay = self.backoff_seconds * (2 ** attempt)
                    if delay > 0:
                        time.sleep(delay)
                    continue
                raise SentenceVerificationError(
                    f"Gemini sentence verification failed: {exc}"
                ) from exc
        raise SentenceVerificationError("Gemini sentence verification failed after retries.")

    @staticmethod
    def _is_retryable_exception(exc: Exception) -> bool:
        return is_retryable_exception(
            exc,
            exception_status_code=GeminiSentenceVerificationService._exception_status_code,
        )

    @staticmethod
    def _exception_status_code(exc: Exception) -> int | None:
        for candidate in (exc, getattr(exc, "response", None), getattr(exc, "cause", None)):
            if candidate is None:
                continue
            status_code = getattr(candidate, "status_code", None)
            if isinstance(status_code, int):
                return status_code
            code = getattr(candidate, "code", None)
            if isinstance(code, int):
                return code
        return None
