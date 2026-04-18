from __future__ import annotations

import math
import time

from app.services.verification_models import VerificationError


def ensure_client(service) -> object:
    if service._client is None:
        try:
            from google import genai  # type: ignore import-not-found
            from google.genai import types as genai_types  # type: ignore import-not-found
        except ImportError as exc:
            raise VerificationError("google-genai package is required for Gemini verification.") from exc
        timeout_ms = max(1, math.ceil(service.timeout_seconds * 1000))
        service._client = genai.Client(
            api_key=service.api_key,
            http_options=genai_types.HttpOptions(timeout=timeout_ms),
        )
    return service._client


def generate_content(service, prompt: str, *, config: object | None = None) -> object:
    attempts = service.max_retries + 1
    for attempt in range(attempts):
        try:
            client = ensure_client(service)
            return client.models.generate_content(
                model=service.model,
                contents=prompt,
                config=config,
            )
        except Exception as exc:
            if attempt < service.max_retries:
                delay = service.backoff_seconds * (2**attempt)
                if delay > 0:
                    time.sleep(delay)
                continue
            raise VerificationError(f"Gemini verification request failed: {exc}") from exc
    return type("R", (), {"text": None})()


def generate_text(service, prompt: str) -> str | None:
    attempts = service.max_retries + 1
    for attempt in range(attempts):
        try:
            client = ensure_client(service)
            response = client.models.generate_content(model=service.model, contents=prompt)
            text = getattr(response, "text", None)
            cleaned = text.strip() if isinstance(text, str) else ""
            return cleaned or None
        except Exception as exc:
            if attempt < service.max_retries:
                delay = service.backoff_seconds * (2**attempt)
                if delay > 0:
                    time.sleep(delay)
                continue
            raise VerificationError(f"Gemini verification request failed: {exc}") from exc
    return None
