from __future__ import annotations

import httpx
import pytest

from app.services.deepl_translation import DeepLTranslationService
from app.services.translation import TranslationError


class _FakeResponse:
    def __init__(self, payload: object | None = None, *, raises: Exception | None = None):
        self._payload = payload if payload is not None else {"translations": [{"text": "book"}]}
        self._raises = raises

    def raise_for_status(self) -> None:
        if self._raises is not None:
            raise self._raises

    def json(self) -> object:
        return self._payload


class _FakeClient:
    def __init__(
        self,
        response: _FakeResponse | None = None,
        *,
        raises: Exception | None = None,
        sequence: list[_FakeResponse | Exception] | None = None,
    ):
        self._response = response
        self._raises = raises
        self._sequence = sequence or []
        self.calls = 0
        self.requests: list[dict] = []

    def post(self, *_args, **_kwargs) -> _FakeResponse:
        self.calls += 1
        self.requests.append(_kwargs)
        if self._sequence:
            event = self._sequence.pop(0)
            if isinstance(event, Exception):
                raise event
            return event
        if self._raises is not None:
            raise self._raises
        if self._response is None:  # pragma: no cover - defensive path for test doubles
            raise RuntimeError("missing fake response")
        return self._response


def _http_status_error(status_code: int, *, retry_after: str | None = None) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://api.deepl.com/v2/translate")
    headers = {"Retry-After": retry_after} if retry_after is not None else {}
    response = httpx.Response(status_code, request=request, headers=headers)
    return httpx.HTTPStatusError("status failure", request=request, response=response)


def test_deepl_translation_service_returns_translated_text(monkeypatch) -> None:
    service = DeepLTranslationService(api_key="test-key")
    monkeypatch.setattr(service, "_ensure_client", lambda: _FakeClient(_FakeResponse()))
    assert service.translate_da_to_en("bog") == "book"


def test_deepl_translation_service_can_translate_en_to_da(monkeypatch) -> None:
    service = DeepLTranslationService(api_key="test-key")
    fake_client = _FakeClient(_FakeResponse(payload={"translations": [{"text": "hus"}]}))
    monkeypatch.setattr(service, "_ensure_client", lambda: fake_client)
    assert service.translate_en_to_da("house") == "hus"
    request_payload = fake_client.requests[0]["content"]
    assert "EN" in request_payload
    assert "DA" in request_payload


def test_deepl_translation_service_normalizes_response_to_lowercase(monkeypatch) -> None:
    service = DeepLTranslationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_ensure_client",
        lambda: _FakeClient(_FakeResponse(payload={"translations": [{"text": "The Book"}]})),
    )
    assert service.translate_da_to_en("bog") == "the book"


def test_deepl_translation_service_detects_source_language(monkeypatch) -> None:
    service = DeepLTranslationService(api_key="test-key")
    fake_client = _FakeClient(
        _FakeResponse(payload={"translations": [{"detected_source_language": "da", "text": "book"}]})
    )
    monkeypatch.setattr(service, "_ensure_client", lambda: fake_client)
    assert service.detect_source_language("bog") == "DA"


def test_deepl_translation_service_raises_on_transport_errors(monkeypatch) -> None:
    service = DeepLTranslationService(api_key="test-key", max_retries=0)
    monkeypatch.setattr(
        service,
        "_ensure_client",
        lambda: _FakeClient(raises=httpx.ConnectError("transport failed")),
    )
    with pytest.raises(TranslationError):
        service.translate_da_to_en("bog")


def test_deepl_translation_service_retries_on_rate_limit_then_succeeds(monkeypatch) -> None:
    service = DeepLTranslationService(api_key="test-key", max_retries=3)
    fake_client = _FakeClient(
        sequence=[
            _FakeResponse(raises=_http_status_error(429, retry_after="0")),
            _FakeResponse(payload={"translations": [{"text": "book"}]}),
        ]
    )
    monkeypatch.setattr(service, "_ensure_client", lambda: fake_client)
    monkeypatch.setattr("app.services.deepl_translation.time.sleep", lambda _seconds: None)

    assert service.translate_da_to_en("bog") == "book"
    assert fake_client.calls == 2


def test_deepl_translation_service_uses_free_endpoint_for_free_keys() -> None:
    service = DeepLTranslationService(api_key="test-key:fx")
    assert service.endpoint == "https://api-free.deepl.com"


def test_deepl_translation_service_requires_api_key() -> None:
    with pytest.raises(TranslationError, match="DeepL API key is required"):
        DeepLTranslationService(api_key=" ")
