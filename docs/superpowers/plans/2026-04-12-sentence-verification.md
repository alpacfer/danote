# Sentence Verification in Search — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gemini verifies Danish sentence in sidebar search before save; errors shown underlined + corrected text; save button gated on verification.

**Architecture:** New `GeminiSentenceVerificationService` (own file, Protocol pattern). New `POST /api/sentencebank/verify-sentence` route via schema-first. Frontend debounces verification at 600ms in `use-sidebar-search.ts`, caches per query; `SidebarSentenceResult` renders error spans + corrected text, gates save.

**Tech Stack:** Python `google-genai`, FastAPI, Pydantic, React 19, TypeScript, shadcn/ui CommandItem.

---

## File map

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/app/services/sentence_verification.py` | Create | Service Protocol + dataclasses + Gemini impl |
| `backend/app/api/schemas/v1/sentencebank.py` | Modify | Add `VerifySentenceRequest`, `VerifySentenceResponse`, `SentenceVerificationErrorItem` |
| `backend/app/services/use_cases/sentencebank.py` | Modify | Add `verify_sentence` method |
| `backend/app/api/routes/sentencebank.py` | Modify | Add `POST /api/sentencebank/verify-sentence` |
| `backend/app/core/app_state.py` | Modify | Add `sentence_verification_service` slot |
| `backend/app/bootstrap/runtime_sentence_verification.py` | Create | Bootstrap init for service |
| `backend/app/bootstrap/runtime.py` | Modify | Add startup step |
| `docs/contracts/api-contract.md` | Modify | Add new endpoint |
| `backend/tests/services/test_sentence_verification_unit.py` | Create | Parse logic unit tests |
| `backend/tests/api/test_sentencebank_verify_route.py` | Create | Route HTTP tests |
| `frontend/src/app/core/types-api.ts` | Modify | Add `VerifySentenceResponse` type |
| `frontend/src/app/core/constants.ts` | Modify | Add `SENTENCE_VERIFY_DEBOUNCE_MS` |
| `frontend/src/app/core/index.ts` | Modify | Export new type + constant |
| `frontend/src/app/chrome/sidebar/use-sidebar-search.ts` | Modify | 50-char limit, verification state, debounce, cache |
| `frontend/src/app/chrome/sidebar/sidebar-sentence-result.tsx` | Modify | Error spans, corrected text, save gate |
| `frontend/src/app/chrome/sidebar/sidebar-search-results.tsx` | Modify | Thread verification props |
| `frontend/src/app/chrome/sidebar/app-sidebar.tsx` | Modify | Thread verification props |
| `frontend/src/test/app/mock-fetch.ts` | Modify | Add verify-sentence mock option |
| `frontend/src/test/app/app-shell-search-sentence-verification.test.tsx` | Create | UI integration tests |

---

## Task 1: Backend sentence verification service

**Files:**
- Create: `backend/app/services/sentence_verification.py`
- Create: `backend/tests/services/test_sentence_verification_unit.py`

- [ ] **Step 1.1: Write failing unit tests**

```python
# backend/tests/services/test_sentence_verification_unit.py
from __future__ import annotations

from app.services.sentence_verification import (
    SentenceVerificationErrorSpan,
    SentenceVerificationResult,
    _parse_result,
)


def test_parse_result_valid_sentence() -> None:
    raw = '{"is_valid": true, "errors": [], "corrected_text": null, "language": "da"}'
    result = _parse_result(raw, "Jeg er glad")
    assert result.is_valid is True
    assert result.errors == []
    assert result.corrected_text is None
    assert result.language == "da"


def test_parse_result_with_errors() -> None:
    raw = '{"is_valid": false, "errors": [{"start": 7, "end": 11, "message": "typo"}], "corrected_text": "jeg er glad", "language": "da"}'
    result = _parse_result(raw, "jeg er glat")
    assert result.is_valid is False
    assert len(result.errors) == 1
    assert result.errors[0] == SentenceVerificationErrorSpan(start=7, end=11, message="typo")
    assert result.corrected_text == "jeg er glad"
    assert result.language == "da"


def test_parse_result_none_returns_valid_fallback() -> None:
    result = _parse_result(None, "any text")
    assert result.is_valid is True
    assert result.errors == []
    assert result.corrected_text is None
    assert result.language == "unknown"


def test_parse_result_invalid_json_returns_valid_fallback() -> None:
    result = _parse_result("not json", "any text")
    assert result.is_valid is True
    assert result.errors == []


def test_parse_result_unknown_language_normalized() -> None:
    raw = '{"is_valid": true, "errors": [], "corrected_text": null, "language": "fr"}'
    result = _parse_result(raw, "bonjour")
    assert result.language == "unknown"


def test_parse_result_english_detected() -> None:
    raw = '{"is_valid": true, "errors": [], "corrected_text": null, "language": "en"}'
    result = _parse_result(raw, "hello world")
    assert result.language == "en"


def test_parse_result_skips_malformed_error_spans() -> None:
    raw = '{"is_valid": false, "errors": [{"start": "bad", "end": 5, "message": "x"}, {"start": 0, "end": 3, "message": "ok"}], "corrected_text": "fix", "language": "da"}'
    result = _parse_result(raw, "fix me")
    assert len(result.errors) == 1
    assert result.errors[0].start == 0
```

- [ ] **Step 1.2: Run — confirm fail**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_sentence_verification_unit.py
```
Expected: `ImportError` or `ModuleNotFoundError` (file doesn't exist yet).

- [ ] **Step 1.3: Create service file**

```python
# backend/app/services/sentence_verification.py
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from typing import Literal, Protocol


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
        '- "language": "da" if Danish, "en" if English, "unknown" otherwise'
    )


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
    corrected_text = data.get("corrected_text") or None
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
    return SentenceVerificationResult(
        is_valid=is_valid,
        errors=errors,
        corrected_text=corrected_text,
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
        from app.services.gemini_translation_helpers import is_retryable_exception
        return is_retryable_exception(
            exc,
            exception_status_code=GeminiSentenceVerificationService._exception_status_code,
        )

    @staticmethod
    def _exception_status_code(exc: Exception) -> int | None:
        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int):
            return status_code
        code = getattr(exc, "code", None)
        if isinstance(code, int):
            return code
        return None
```

- [ ] **Step 1.4: Run — confirm pass**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_sentence_verification_unit.py
```
Expected: 7 passed.

- [ ] **Step 1.5: Lint**

```bash
cd backend && PYTHONPATH=. .venv/bin/ruff check app/services/sentence_verification.py
```

- [ ] **Step 1.6: Commit**

```bash
git add backend/app/services/sentence_verification.py backend/tests/services/test_sentence_verification_unit.py
git commit -m "feat: add GeminiSentenceVerificationService with parse logic"
```

---

## Task 2: Backend API layer (schema + use case + route + docs)

**Files:**
- Modify: `backend/app/api/schemas/v1/sentencebank.py`
- Modify: `backend/app/services/use_cases/sentencebank.py`
- Modify: `backend/app/api/routes/sentencebank.py`
- Modify: `docs/contracts/api-contract.md`
- Create: `backend/tests/api/test_sentencebank_verify_route.py`

- [ ] **Step 2.1: Write failing route test**

```python
# backend/tests/api/test_sentencebank_verify_route.py
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.app_state import set_service_field
from app.services.sentence_verification import SentenceVerificationErrorSpan, SentenceVerificationResult
from tests.api.support import build_api_test_app


class StubSentenceVerificationService:
    def verify_sentence(self, source_text: str) -> SentenceVerificationResult:
        if source_text == "jeg er glat":
            return SentenceVerificationResult(
                is_valid=False,
                errors=[SentenceVerificationErrorSpan(start=7, end=11, message="typo")],
                corrected_text="jeg er glad",
                language="da",
            )
        return SentenceVerificationResult(
            is_valid=True,
            errors=[],
            corrected_text=None,
            language="da",
        )


def test_verify_sentence_valid(tmp_path, stub_nlp_adapter_factory) -> None:
    app = build_api_test_app(tmp_path / "db.sqlite3", nlp_adapter_factory=stub_nlp_adapter_factory)
    with TestClient(app) as client:
        set_service_field(client.app, "sentence_verification_service", StubSentenceVerificationService())
        response = client.post("/api/sentencebank/verify-sentence", json={"source_text": "jeg er glad"})
    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is True
    assert body["errors"] == []
    assert body["corrected_text"] is None
    assert body["language"] == "da"


def test_verify_sentence_with_errors(tmp_path, stub_nlp_adapter_factory) -> None:
    app = build_api_test_app(tmp_path / "db.sqlite3", nlp_adapter_factory=stub_nlp_adapter_factory)
    with TestClient(app) as client:
        set_service_field(client.app, "sentence_verification_service", StubSentenceVerificationService())
        response = client.post("/api/sentencebank/verify-sentence", json={"source_text": "jeg er glat"})
    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is False
    assert body["errors"] == [{"start": 7, "end": 11, "message": "typo"}]
    assert body["corrected_text"] == "jeg er glad"
    assert body["language"] == "da"


def test_verify_sentence_no_service_returns_valid(tmp_path, stub_nlp_adapter_factory) -> None:
    app = build_api_test_app(tmp_path / "db.sqlite3", nlp_adapter_factory=stub_nlp_adapter_factory)
    with TestClient(app) as client:
        set_service_field(client.app, "sentence_verification_service", None)
        response = client.post("/api/sentencebank/verify-sentence", json={"source_text": "jeg er glad"})
    assert response.status_code == 200
    assert response.json()["is_valid"] is True


def test_verify_sentence_too_long_returns_400(tmp_path, stub_nlp_adapter_factory) -> None:
    app = build_api_test_app(tmp_path / "db.sqlite3", nlp_adapter_factory=stub_nlp_adapter_factory)
    with TestClient(app) as client:
        response = client.post(
            "/api/sentencebank/verify-sentence",
            json={"source_text": "a" * 51},
        )
    assert response.status_code == 422


def test_verify_sentence_empty_returns_422(tmp_path, stub_nlp_adapter_factory) -> None:
    app = build_api_test_app(tmp_path / "db.sqlite3", nlp_adapter_factory=stub_nlp_adapter_factory)
    with TestClient(app) as client:
        response = client.post("/api/sentencebank/verify-sentence", json={"source_text": ""})
    assert response.status_code == 422
```

- [ ] **Step 2.2: Run — confirm fail**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/api/test_sentencebank_verify_route.py
```
Expected: 404 or import errors (endpoint doesn't exist yet).

- [ ] **Step 2.3: Add schemas**

In `backend/app/api/schemas/v1/sentencebank.py`, add after `AddSentenceResponse`:

```python
class SentenceVerificationErrorItem(BaseModel):
    start: int
    end: int
    message: str


class VerifySentenceRequest(BaseModel):
    source_text: str = Field(..., min_length=1, max_length=50)


class VerifySentenceResponse(BaseModel):
    is_valid: bool
    errors: list[SentenceVerificationErrorItem] = Field(default_factory=list)
    corrected_text: str | None = None
    language: Literal["da", "en", "unknown"] = "unknown"
```

Also add `Literal` to the imports at the top of `sentencebank.py` schemas file (it already has `from typing import Literal` from `AddSentenceResponse` — verify first, add if missing).

- [ ] **Step 2.4: Add `verify_sentence` to `SentencebankUseCase`**

In `backend/app/services/use_cases/sentencebank.py`:

Add import at top (after existing imports):
```python
from app.services.sentence_verification import SentenceVerificationService
from app.api.schemas.v1.sentencebank import (
    AddSentenceResponse,
    SentenceListResponse,
    SentenceSummary,
    SentenceTokenCard,
    SentenceVerificationErrorItem,
    VerifySentenceResponse,
)
```

Note: the existing import block already pulls `AddSentenceResponse`, `SentenceListResponse`, `SentenceSummary`, `SentenceTokenCard` from `app.api.schemas.v1.sentencebank` — extend that import to include `SentenceVerificationErrorItem` and `VerifySentenceResponse`.

Update `__init__`:
```python
class SentencebankUseCase:
    def __init__(
        self,
        db_path,
        translation_service: TranslationService | None = None,
        nlp_adapter: NLPAdapter | None = None,
        wordbank_use_case: WordbankUseCase | None = None,
        sentence_verification_service: SentenceVerificationService | None = None,
    ):
        self._repository = SentencebankRepository(db_path)
        self._translation_service = translation_service
        self._nlp_adapter = nlp_adapter
        self._wordbank_use_case = wordbank_use_case
        self._sentence_verification_service = sentence_verification_service
```

Add method (after `list_linked_sentences`):
```python
def verify_sentence(self, source_text: str) -> VerifySentenceResponse:
    normalized = _normalize_sentence_text(source_text)
    if not normalized:
        raise ValueError("source_text is required")
    if self._sentence_verification_service is None:
        return VerifySentenceResponse(is_valid=True, errors=[], corrected_text=None, language="unknown")
    result = self._sentence_verification_service.verify_sentence(normalized)
    return VerifySentenceResponse(
        is_valid=result.is_valid,
        errors=[
            SentenceVerificationErrorItem(start=e.start, end=e.end, message=e.message)
            for e in result.errors
        ],
        corrected_text=result.corrected_text,
        language=result.language,
    )
```

- [ ] **Step 2.5: Add route**

In `backend/app/api/routes/sentencebank.py`:

Add imports:
```python
from app.api.schemas.v1.sentencebank import (
    AddSentenceRequest,
    AddSentenceResponse,
    SentenceListResponse,
    VerifySentenceRequest,
    VerifySentenceResponse,
)
```

Update `_sentencebank_use_case` factory to pass the service:
```python
def _sentencebank_use_case(request: Request) -> SentencebankUseCase:
    settings = get_settings(request)
    services = get_services(request)
    return SentencebankUseCase(
        db_path=settings.db_path,
        translation_service=services.translation_service,
        nlp_adapter=services.nlp_adapter,
        wordbank_use_case=build_wordbank_use_case(request),
        sentence_verification_service=services.sentence_verification_service,
    )
```

Add route after `list_sentences`:
```python
@router.post("/sentencebank/verify-sentence", response_model=VerifySentenceResponse)
def verify_sentence(payload: VerifySentenceRequest, request: Request) -> VerifySentenceResponse:
    return run_db_operation(
        request,
        lambda: _sentencebank_use_case(request).verify_sentence(payload.source_text),
        error_log_name="sentencebank_verify_db_operational_error",
    )
```

- [ ] **Step 2.6: Update API contract**

In `docs/contracts/api-contract.md`, find the sentencebank section and add after `GET /api/sentencebank/sentences`:

```markdown
### POST `/api/sentencebank/verify-sentence`
- **Request model:** `VerifySentenceRequest` (`source_text: str`, max 50 chars).
- **Response model:** `VerifySentenceResponse` (`is_valid`, `errors: [{start, end, message}]`, `corrected_text`, `language`).
- **Notable status/error behavior:** `400` empty text. `422` text >50 chars or empty. `503` DB unavailable. No Gemini service → returns `is_valid=true`.
```

- [ ] **Step 2.7: Run tests — confirm pass**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/api/test_sentencebank_verify_route.py tests/services/test_sentence_verification_unit.py
```
Expected: all pass.

- [ ] **Step 2.8: Lint**

```bash
cd backend && PYTHONPATH=. .venv/bin/ruff check app/api/schemas/v1/sentencebank.py app/services/use_cases/sentencebank.py app/api/routes/sentencebank.py
```

- [ ] **Step 2.9: Commit**

```bash
git add backend/app/api/schemas/v1/sentencebank.py backend/app/services/use_cases/sentencebank.py backend/app/api/routes/sentencebank.py backend/tests/api/test_sentencebank_verify_route.py docs/contracts/api-contract.md
git commit -m "feat: add verify-sentence route and use case method"
```

---

## Task 3: Backend bootstrap wiring

**Files:**
- Modify: `backend/app/core/app_state.py`
- Create: `backend/app/bootstrap/runtime_sentence_verification.py`
- Modify: `backend/app/bootstrap/runtime.py`

- [ ] **Step 3.1: Add `sentence_verification_service` slot to `BackendServices`**

In `backend/app/core/app_state.py`, in the `BackendServices` dataclass, add:
```python
sentence_verification_service: Any = None
```

And in `close_runtime_services`, extend the `for field_name in (...)` tuple to include `"sentence_verification_service"`.

Current tuple ends with `"tts_service"`. Change to:
```python
    for field_name in (
        "cor_lexicon_service",
        "translation_service",
        "gemini_word_translation_service",
        "gemini_related_words_service",
        "word_verification_service",
        "tts_service",
        "sentence_verification_service",
    ):
```

- [ ] **Step 3.2: Create bootstrap file**

```python
# backend/app/bootstrap/runtime_sentence_verification.py
from __future__ import annotations

import logging

from fastapi import FastAPI

from app.core.app_state import get_runtime_state, set_service_field
from app.core.config import Settings

logger = logging.getLogger(__name__)


def initialize_sentence_verification(app: FastAPI, settings: Settings) -> None:
    _close_service(get_runtime_state(app).services.sentence_verification_service)
    set_service_field(app, "sentence_verification_service", None)

    api_key = settings.word_verification_gemini_api_key or settings.gemini_api_key
    if not api_key:
        logger.warning("backend_sentence_verification_startup_skipped_missing_api_key")
        return

    model = settings.word_verification_gemini_model or settings.gemini_model
    try:
        from app.services.sentence_verification import GeminiSentenceVerificationService
        set_service_field(
            app,
            "sentence_verification_service",
            GeminiSentenceVerificationService(api_key=api_key, model=model),
        )
    except Exception:
        logger.exception("backend_sentence_verification_startup_failed")


def _close_service(service: object | None) -> None:
    close = getattr(service, "close", None)
    if callable(close):
        close()
```

- [ ] **Step 3.3: Add startup step**

In `backend/app/bootstrap/runtime.py`:

Add import:
```python
from app.bootstrap.runtime_sentence_verification import initialize_sentence_verification
```

In `build_startup_steps`, add entry after `"word_verification"`:
```python
StartupStep("sentence_verification", initialize_sentence_verification),
```

- [ ] **Step 3.4: Run existing tests to confirm nothing broken**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/api/test_sentencebank_verify_route.py tests/api/test_sentencebank_endpoint.py
```
Expected: all pass.

- [ ] **Step 3.5: Commit**

```bash
git add backend/app/core/app_state.py backend/app/bootstrap/runtime_sentence_verification.py backend/app/bootstrap/runtime.py
git commit -m "feat: bootstrap sentence verification service on startup"
```

---

## Task 4: Frontend — core type + constant

**Files:**
- Modify: `frontend/src/app/core/types-api.ts`
- Modify: `frontend/src/app/core/constants.ts`
- Modify: `frontend/src/app/core/index.ts`

- [ ] **Step 4.1: Add `VerifySentenceResponse` to types**

In `frontend/src/app/core/types-api.ts`, after `AddSentenceResponse`:

```typescript
export type SentenceVerificationErrorItem = {
  start: number
  end: number
  message: string
}

export type VerifySentenceResponse = {
  is_valid: boolean
  errors: SentenceVerificationErrorItem[]
  corrected_text: string | null
  language: "da" | "en" | "unknown"
}
```

- [ ] **Step 4.2: Add constant**

In `frontend/src/app/core/constants.ts`, add:

```typescript
export const SENTENCE_VERIFY_DEBOUNCE_MS = 600
```

- [ ] **Step 4.3: Export from index**

In `frontend/src/app/core/index.ts`, verify `types-api.ts` and `constants.ts` are re-exported (they should already be with a wildcard or named export). If `VerifySentenceResponse` and `SENTENCE_VERIFY_DEBOUNCE_MS` aren't reachable from `@/app/core`, add them explicitly to `index.ts`.

Check the index pattern:
```bash
grep -n "types-api\|constants" frontend/src/app/core/index.ts
```

If they export via `export * from "./types-api"` and `export * from "./constants"`, no change needed. If individual named exports are used, add the new names.

- [ ] **Step 4.4: Commit**

```bash
git add frontend/src/app/core/types-api.ts frontend/src/app/core/constants.ts frontend/src/app/core/index.ts
git commit -m "feat: add VerifySentenceResponse type and SENTENCE_VERIFY_DEBOUNCE_MS constant"
```

---

## Task 5: Frontend hook — `use-sidebar-search.ts`

**Files:**
- Modify: `frontend/src/app/chrome/sidebar/use-sidebar-search.ts`

- [ ] **Step 5.1: Update imports and add state**

In `use-sidebar-search.ts`, update the import from `@/app/core`:

```typescript
import {
  BACKEND_URL,
  SEARCH_RESOLVE_DEBOUNCE_MS,
  SENTENCE_VERIFY_DEBOUNCE_MS,
  createApiClient,
  hasMultipleWords,
  isShortLetterWord,
  type GeneratePhraseTranslationResponse,
  type VerifySentenceResponse,
  normalizeSearchWord,
  type CORSearchFormResponse,
  type SavedNote,
  type WordbankSearchItem,
  type WordbankSearchResponse,
} from "@/app/core"
```

Add new state inside `useSidebarSearch` (after `isSentenceTranslationLoading` state):

```typescript
const [sentenceVerification, setSentenceVerification] = useState<{
  query: string
  result: VerifySentenceResponse
} | null>(null)
const [isSentenceVerificationLoading, setIsSentenceVerificationLoading] = useState(false)
const sentenceVerificationCacheRef = useRef<Map<string, VerifySentenceResponse>>(new Map())
```

- [ ] **Step 5.2: Apply 50-char limit**

Change:
```typescript
const isSentenceMode = hasMultipleWords(trimmedQuery)
```

To:
```typescript
const isSentenceMode = hasMultipleWords(trimmedQuery) && trimmedQuery.length <= 50
```

- [ ] **Step 5.3: Clear verification cache with other caches**

In the existing `useEffect` that calls `wordbankSearchCacheRef.current.clear()` and `corFormSearchCacheRef.current.clear()`, add:
```typescript
sentenceVerificationCacheRef.current.clear()
```

- [ ] **Step 5.4: Add verification debounce effect**

Add a new `useEffect` after the phrase translation effect (around line 263):

```typescript
useEffect(() => {
  if (!isSentenceMode || !trimmedQuery) {
    setSentenceVerification(null)
    setIsSentenceVerificationLoading(false)
    return
  }

  const cached = sentenceVerificationCacheRef.current.get(trimmedQuery)
  if (cached) {
    setSentenceVerification({ query: trimmedQuery, result: cached })
    setIsSentenceVerificationLoading(false)
    return
  }

  let cancelled = false
  setSentenceVerification(null)
  setIsSentenceVerificationLoading(true)

  const timeoutId = window.setTimeout(() => {
    void (async () => {
      try {
        const result = await apiClient.postJson<VerifySentenceResponse>(
          "/api/sentencebank/verify-sentence",
          { source_text: trimmedQuery },
          "Could not verify sentence.",
        )
        if (cancelled) {
          return
        }
        sentenceVerificationCacheRef.current.set(trimmedQuery, result)
        setSentenceVerification({ query: trimmedQuery, result })
      } catch {
        if (!cancelled) {
          // Verification failure → allow save (treat as valid)
          const fallback: VerifySentenceResponse = {
            is_valid: true,
            errors: [],
            corrected_text: null,
            language: "unknown",
          }
          sentenceVerificationCacheRef.current.set(trimmedQuery, fallback)
          setSentenceVerification({ query: trimmedQuery, result: fallback })
        }
      } finally {
        if (!cancelled) {
          setIsSentenceVerificationLoading(false)
        }
      }
    })()
  }, SENTENCE_VERIFY_DEBOUNCE_MS)

  return () => {
    cancelled = true
    window.clearTimeout(timeoutId)
    setIsSentenceVerificationLoading(false)
  }
}, [apiClient, isSentenceMode, trimmedQuery])
```

- [ ] **Step 5.5: Return new values from hook**

In the `return` object at end of `useSidebarSearch`, add:

```typescript
sentenceVerification: sentenceVerification?.query === trimmedQuery ? sentenceVerification.result : null,
isSentenceVerificationLoading,
```

- [ ] **Step 5.6: Lint check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```
Fix any type errors before continuing.

- [ ] **Step 5.7: Commit**

```bash
git add frontend/src/app/chrome/sidebar/use-sidebar-search.ts
git commit -m "feat: add sentence verification debounce and 50-char limit in sidebar search"
```

---

## Task 6: Frontend UI — SidebarSentenceResult + prop threading

**Files:**
- Modify: `frontend/src/app/chrome/sidebar/sidebar-sentence-result.tsx`
- Modify: `frontend/src/app/chrome/sidebar/sidebar-search-results.tsx`
- Modify: `frontend/src/app/chrome/sidebar/app-sidebar.tsx`

- [ ] **Step 6.1: Update `SidebarSentenceResult`**

Replace entire `frontend/src/app/chrome/sidebar/sidebar-sentence-result.tsx`:

```typescript
import { Plus } from "lucide-react"

import type { SentenceVerificationErrorItem, VerifySentenceResponse } from "@/app/core"
import { CommandGroup, CommandItem } from "@/components/ui/command"
import { Skeleton } from "@/components/ui/skeleton"

type SidebarSentenceResultProps = {
  sourceText: string
  englishTranslation: string | null
  isTranslationLoading: boolean
  sentenceVerification: VerifySentenceResponse | null
  isSentenceVerificationLoading: boolean
  onSaveSentence: (sourceText: string) => Promise<void>
  onCloseSearch: () => void
}

function renderWithErrors(text: string, errors: SentenceVerificationErrorItem[]) {
  if (!errors.length) {
    return <span>{text}</span>
  }
  const sorted = [...errors].sort((a, b) => a.start - b.start)
  const parts: React.ReactNode[] = []
  let cursor = 0
  for (const err of sorted) {
    if (cursor < err.start) {
      parts.push(<span key={`clean-${cursor}`}>{text.slice(cursor, err.start)}</span>)
    }
    if (err.start < err.end) {
      parts.push(
        <span
          key={`err-${err.start}`}
          className="underline decoration-destructive decoration-wavy decoration-2"
          title={err.message}
        >
          {text.slice(err.start, err.end)}
        </span>,
      )
    }
    cursor = err.end
  }
  if (cursor < text.length) {
    parts.push(<span key={`tail-${cursor}`}>{text.slice(cursor)}</span>)
  }
  return <>{parts}</>
}

export function SidebarSentenceResult({
  sourceText,
  englishTranslation,
  isTranslationLoading,
  sentenceVerification,
  isSentenceVerificationLoading,
  onSaveSentence,
  onCloseSearch,
}: SidebarSentenceResultProps) {
  const isSaveDisabled = isSentenceVerificationLoading || sentenceVerification === null
  const textToSave = sentenceVerification?.corrected_text ?? sourceText
  const hasErrors = sentenceVerification !== null && !sentenceVerification.is_valid

  return (
    <CommandGroup heading="Sentence">
      <CommandItem
        value="sentence-translation-result"
        disabled={isSaveDisabled}
        onSelect={() => {
          if (isSaveDisabled) {
            return
          }
          void (async () => {
            await onSaveSentence(textToSave)
            onCloseSearch()
          })()
        }}
        className="flex items-center justify-between gap-3"
      >
        <div className="flex min-w-0 flex-col items-start gap-1">
          <span className="text-sm font-semibold break-words">
            {renderWithErrors(sourceText, sentenceVerification?.errors ?? [])}
          </span>
          {isTranslationLoading ? (
            <Skeleton className="h-4 w-28" data-testid="sentence-search-translation-skeleton" />
          ) : (
            <span className="text-muted-foreground text-xs leading-4 break-words">
              {englishTranslation?.trim() || "No translation available."}
            </span>
          )}
          {hasErrors && sentenceVerification.corrected_text ? (
            <div className="mt-0.5 space-y-0.5">
              <span className="text-muted-foreground text-xs">Corrected:</span>
              <p className="text-sm font-medium">{sentenceVerification.corrected_text}</p>
            </div>
          ) : null}
          {isSentenceVerificationLoading ? (
            <Skeleton className="h-3 w-24" data-testid="sentence-verification-skeleton" />
          ) : null}
        </div>
        <Plus className="text-muted-foreground size-4 shrink-0" />
      </CommandItem>
    </CommandGroup>
  )
}
```

- [ ] **Step 6.2: Thread props in `sidebar-search-results.tsx`**

In `frontend/src/app/chrome/sidebar/sidebar-search-results.tsx`:

Add to `SidebarSearchResultsData` type:
```typescript
sentenceVerification: VerifySentenceResponse | null
isSentenceVerificationLoading: boolean
```

Add import at top:
```typescript
import type { VerifySentenceResponse } from "@/app/core"
// ... existing imports
```

Update the `SidebarSentenceResult` usage inside `SidebarSearchResults`:
```tsx
<SidebarSentenceResult
  sourceText={data.sentenceSearchResult.source_text}
  englishTranslation={data.sentenceSearchResult.english_translation}
  isTranslationLoading={data.isSentenceTranslationLoading}
  sentenceVerification={data.sentenceVerification}
  isSentenceVerificationLoading={data.isSentenceVerificationLoading}
  onSaveSentence={actions.onAddSentenceFromSearch}
  onCloseSearch={actions.onCloseSearch}
/>
```

- [ ] **Step 6.3: Thread props in `app-sidebar.tsx`**

In `frontend/src/app/chrome/sidebar/app-sidebar.tsx`:

The `searchResultData` object is built using values from `useSidebarSearch`. Add the two new fields:

```typescript
const searchResultData: SidebarSearchResultsData = {
  sentenceSearchResult,
  isSentenceTranslationLoading,
  sentenceVerification,           // add
  isSentenceVerificationLoading,  // add
  // ... rest of existing fields
}
```

These come from the `useSidebarSearch` return — destructure them at the top of the component alongside `sentenceSearchResult` and `isSentenceTranslationLoading`.

- [ ] **Step 6.4: Type check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```
Expected: no errors.

- [ ] **Step 6.5: Commit**

```bash
git add frontend/src/app/chrome/sidebar/sidebar-sentence-result.tsx frontend/src/app/chrome/sidebar/sidebar-search-results.tsx frontend/src/app/chrome/sidebar/app-sidebar.tsx
git commit -m "feat: sentence verification UI — error underlines, corrected text, save gate"
```

---

## Task 7: Frontend tests

**Files:**
- Modify: `frontend/src/test/app/mock-fetch.ts`
- Create: `frontend/src/test/app/app-shell-search-sentence-verification.test.tsx`

- [ ] **Step 7.1: Add verify-sentence mock to `mock-fetch.ts`**

In `mockFetchImplementation` options type (around the `addSentenceOk` block), add:

```typescript
verifySentenceResponse?: {
  is_valid: boolean
  errors: Array<{ start: number; end: number; message: string }>
  corrected_text: string | null
  language: "da" | "en" | "unknown"
}
verifySentenceOk?: boolean
```

Inside the mock `fetch` handler (before the final 404 return), add:

```typescript
if (url.endsWith("/api/sentencebank/verify-sentence")) {
  if (options?.verifySentenceOk === false) {
    throw new Error("verify sentence request failed")
  }
  return responseOf(
    options?.verifySentenceResponse ?? {
      is_valid: true,
      errors: [],
      corrected_text: null,
      language: "unknown",
    },
  )
}
```

Place this block before the `url.endsWith("/api/sentencebank/sentences")` POST check.

- [ ] **Step 7.2: Write integration tests**

```typescript
// frontend/src/test/app/app-shell-search-sentence-verification.test.tsx
import { fireEvent, mockFetchImplementation, renderApp, screen, waitFor } from "@/test/app-test-helpers"

const SEARCH_LABEL = "command search"

function openSearch() {
  fireEvent.click(screen.getByRole("button", { name: /search\.\.\./i }))
}

function typeInSearch(text: string) {
  const input = screen.getByRole("combobox", { name: SEARCH_LABEL })
  fireEvent.change(input, { target: { value: text } })
}

describe("Sentence verification in search", () => {
  it("shows verification loading skeleton while verifying", async () => {
    mockFetchImplementation()
    renderApp()
    await screen.findByLabelText("backend-connection-status")

    openSearch()
    typeInSearch("jeg er glad")

    expect(await screen.findByTestId("sentence-verification-skeleton")).toBeInTheDocument()
  })

  it("save button disabled while verification loading", async () => {
    mockFetchImplementation()
    renderApp()
    await screen.findByLabelText("backend-connection-status")

    openSearch()
    typeInSearch("jeg er glad")

    // CommandItem with sentence result should be disabled during verification
    const item = await screen.findByRole("option", { name: /sentence-translation-result/i })
    expect(item).toHaveAttribute("aria-disabled", "true")
  })

  it("no sentence result for query over 50 chars", async () => {
    mockFetchImplementation()
    renderApp()
    await screen.findByLabelText("backend-connection-status")

    openSearch()
    typeInSearch("a".repeat(51))

    // Should not show sentence mode UI
    expect(screen.queryByTestId("sentence-verification-skeleton")).not.toBeInTheDocument()
    expect(screen.queryByTestId("sentence-search-translation-skeleton")).not.toBeInTheDocument()
  })

  it("shows corrected sentence when verification finds errors", async () => {
    mockFetchImplementation({
      verifySentenceResponse: {
        is_valid: false,
        errors: [{ start: 7, end: 11, message: "typo" }],
        corrected_text: "jeg er glad",
        language: "da",
      },
    })
    renderApp()
    await screen.findByLabelText("backend-connection-status")

    openSearch()
    typeInSearch("jeg er glat")

    expect(await screen.findByText("Corrected:")).toBeInTheDocument()
    expect(screen.getByText("jeg er glad")).toBeInTheDocument()
  })

  it("save button enabled after successful verification", async () => {
    mockFetchImplementation({
      verifySentenceResponse: {
        is_valid: true,
        errors: [],
        corrected_text: null,
        language: "da",
      },
    })
    renderApp()
    await screen.findByLabelText("backend-connection-status")

    openSearch()
    typeInSearch("jeg er glad")

    await waitFor(() => {
      const item = screen.getByRole("option", { name: /sentence-translation-result/i })
      expect(item).not.toHaveAttribute("aria-disabled", "true")
    })
  })

  it("saves corrected text when errors found", async () => {
    const addSentenceResponse = {
      status: "inserted" as const,
      source_text: "jeg er glad",
      english_translation: null,
      created_at: "2026-04-12T10:00:00.000Z",
    }
    mockFetchImplementation({
      verifySentenceResponse: {
        is_valid: false,
        errors: [{ start: 7, end: 11, message: "typo" }],
        corrected_text: "jeg er glad",
        language: "da",
      },
      addSentenceResponse,
    })
    renderApp()
    await screen.findByLabelText("backend-connection-status")

    openSearch()
    typeInSearch("jeg er glat")

    // Wait for verification to complete and corrected text to appear
    await screen.findByText("Corrected:")

    // Select the item (saves)
    const item = screen.getByRole("option", { name: /sentence-translation-result/i })
    fireEvent.click(item)

    // Verify save called with corrected text (search should close)
    await waitFor(() => {
      expect(screen.queryByRole("combobox", { name: SEARCH_LABEL })).not.toBeInTheDocument()
    })
  })
})
```

- [ ] **Step 7.3: Run tests**

```bash
cd frontend && npx vitest run src/test/app/app-shell-search-sentence-verification.test.tsx
```
Expected: all pass (some may need adjustment based on exact DOM structure).

- [ ] **Step 7.4: Run full frontend test suite**

```bash
cd frontend && npx vitest run
```
Expected: no regressions.

- [ ] **Step 7.5: Run backend tests**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_sentence_verification_unit.py tests/api/test_sentencebank_verify_route.py tests/api/test_sentencebank_endpoint.py tests/use_cases/test_sentencebank_use_case.py
```
Expected: all pass.

- [ ] **Step 7.6: Full lint**

```bash
make lint
```
Expected: no errors.

- [ ] **Step 7.7: Commit**

```bash
git add frontend/src/test/app/mock-fetch.ts frontend/src/test/app/app-shell-search-sentence-verification.test.tsx
git commit -m "test: add sentence verification integration tests"
```

---

## Self-review

**Spec coverage check:**

| Requirement | Task |
|-------------|------|
| Gemini verification of Danish sentence | Task 1 (service), Task 2 (use case) |
| 50-char limit on search input | Task 5 (hook) |
| Auto-trigger when user stops typing | Task 5 (600ms debounce effect) |
| Cache — only run Gemini once per unique sentence | Task 5 (sentenceVerificationCacheRef) |
| Underline errors with char offsets | Task 6 (renderWithErrors) |
| Show corrected sentence below | Task 6 (SidebarSentenceResult) |
| Save button gated on verification | Task 6 (isSaveDisabled) |
| Save corrected text | Task 6 (textToSave = corrected_text ?? sourceText) |
| Language detection in Gemini prompt | Task 1 (prompt + SentenceVerificationResult.language) |
| No changes to Playground | Nothing in plan touches playground files |
| API contract updated | Task 2 |
| Bootstrap service on startup | Task 3 |

**Placeholder scan:** None found — all steps have complete code.

**Type consistency check:**
- `VerifySentenceResponse` defined in Task 4, used in Tasks 5, 6
- `SentenceVerificationErrorItem` defined in Task 4, used in Task 6 (`renderWithErrors`)
- `SentenceVerificationErrorSpan` (backend) defined in Task 1, used in Task 2
- `verify_sentence` method name consistent across use case (Task 2) and route (Task 2)
- `sentence_verification_service` slot name consistent across `BackendServices` (Task 3), route factory (Task 2), bootstrap (Task 3)
- `isSentenceVerificationLoading` consistent across hook return (Task 5), search-results type (Task 6), sidebar (Task 6), component prop (Task 6)
- `sentenceVerification` consistent across hook return (Task 5), search-results type (Task 6), component prop (Task 6)
