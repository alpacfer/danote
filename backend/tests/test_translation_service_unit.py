from __future__ import annotations

import httpx
import pytest

from app.services.translation import AzureTranslationService, TranslationError


class _FakeResponse:
    def __init__(self, payload: object | None = None, *, raises: Exception | None = None):
        self._payload = payload if payload is not None else [{"translations": [{"text": "book"}]}]
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
    request = httpx.Request("POST", "https://api.cognitive.microsofttranslator.com/translate")
    headers = {"Retry-After": retry_after} if retry_after is not None else {}
    response = httpx.Response(status_code, request=request, headers=headers)
    return httpx.HTTPStatusError("status failure", request=request, response=response)


def test_translation_service_returns_translated_text(monkeypatch) -> None:
    service = AzureTranslationService(api_key="test-key", region="westeurope")
    monkeypatch.setattr(service, "_ensure_client", lambda: _FakeClient(_FakeResponse()))
    assert service.translate_da_to_en("bog") == "book"


def test_translation_service_can_translate_en_to_da(monkeypatch) -> None:
    service = AzureTranslationService(api_key="test-key", region="westeurope")
    fake_client = _FakeClient(_FakeResponse(payload=[{"translations": [{"text": "hus"}]}]))
    monkeypatch.setattr(service, "_ensure_client", lambda: fake_client)
    assert service.translate_en_to_da("house") == "hus"
    request_params = fake_client.requests[0]["params"]
    assert request_params["from"] == "en"
    assert request_params["to"] == "da"


def test_translation_service_normalizes_response_to_lowercase(monkeypatch) -> None:
    service = AzureTranslationService(api_key="test-key", region="westeurope")
    monkeypatch.setattr(
        service,
        "_ensure_client",
        lambda: _FakeClient(_FakeResponse(payload=[{"translations": [{"text": "The Book"}]}])),
    )
    assert service.translate_da_to_en("bog") == "the book"


def test_translation_service_detects_source_language(monkeypatch) -> None:
    service = AzureTranslationService(api_key="test-key", region="westeurope")
    fake_client = _FakeClient(_FakeResponse(payload=[{"language": "en", "score": 1.0}]))
    monkeypatch.setattr(service, "_ensure_client", lambda: fake_client)
    assert service.detect_source_language("book") == "EN"
    assert fake_client.requests[0]["params"]["api-version"] == "3.0"


def test_translation_service_raises_on_transport_errors(monkeypatch) -> None:
    service = AzureTranslationService(api_key="test-key", region="westeurope", max_retries=0)
    monkeypatch.setattr(
        service,
        "_ensure_client",
        lambda: _FakeClient(raises=httpx.ConnectError("transport failed")),
    )
    with pytest.raises(TranslationError):
        service.translate_da_to_en("bog")


def test_translation_service_retries_on_rate_limit_then_succeeds(monkeypatch) -> None:
    service = AzureTranslationService(api_key="test-key", region="westeurope", max_retries=3)
    fake_client = _FakeClient(
        sequence=[
            _FakeResponse(raises=_http_status_error(429, retry_after="0")),
            _FakeResponse(payload=[{"translations": [{"text": "book"}]}]),
        ]
    )
    monkeypatch.setattr(service, "_ensure_client", lambda: fake_client)
    monkeypatch.setattr("app.services.translation.time.sleep", lambda _seconds: None)

    assert service.translate_da_to_en("bog") == "book"
    assert fake_client.calls == 2


def test_translation_service_does_not_retry_non_retryable_status(monkeypatch) -> None:
    service = AzureTranslationService(api_key="test-key", region="westeurope", max_retries=3)
    fake_client = _FakeClient(sequence=[_FakeResponse(raises=_http_status_error(400))])
    monkeypatch.setattr(service, "_ensure_client", lambda: fake_client)
    monkeypatch.setattr("app.services.translation.time.sleep", lambda _seconds: None)

    with pytest.raises(TranslationError):
        service.translate_da_to_en("bog")
    assert fake_client.calls == 1


def test_translation_service_uses_configured_endpoint_override() -> None:
    service = AzureTranslationService(
        api_key="test-key",
        region="westeurope",
        endpoint="https://custom-translator.cognitiveservices.azure.com/",
    )
    assert service.endpoint == "https://custom-translator.cognitiveservices.azure.com"
