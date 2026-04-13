# Sentence Search Speed + EN Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix EN `english_translation` to use Gemini-corrected text (not DA→EN retranslation), skip 2nd Gemini call for EN, add two-phase sentence search (fast preview + full verification), adaptive debounce (200ms DA / 350ms EN).

**Architecture:** Backend adds `fast: bool` param → fast path skips Gemini, uses heuristic lang detect + Azure translate only, returns `status="preview"`. Frontend fires both fast+slow in parallel after one adaptive debounce; fast result shows first, slow overwrites with corrections.

**Tech Stack:** FastAPI + Pydantic (backend), React + TypeScript + Vitest (frontend).

---

## File Map

| File | Change |
|------|--------|
| `backend/app/api/schemas/v1/sentencebank.py` | Add `fast: bool = False` to request; add `"preview"` to status union |
| `backend/app/services/use_cases/sentencebank.py` | Fix EN path (use corrected EN, skip 2nd Gemini+DA→EN); add `_heuristic_detect_language`; add fast path in `preview_sentence_search` |
| `backend/tests/use_cases/test_sentencebank_use_case.py` | Update EN tests (remove unused 2nd-Gemini setup); add fast-path tests |
| `backend/tests/api/test_sentencebank_verify_route.py` | Update EN route test (same assertions, cleaner setup) |
| `frontend/src/app/core/types-api.ts` | Add `"preview"` to `SentenceSearchPreviewResponse.status` |
| `frontend/src/app/core/constants.ts` | Replace `SENTENCE_VERIFY_DEBOUNCE_MS` with `SENTENCE_DEBOUNCE_DA_MS=200`, `SENTENCE_DEBOUNCE_EN_MS=350` |
| `frontend/src/app/chrome/sidebar/use-sidebar-search.ts` | Add `detectQueryLanguage`; adaptive debounce; parallel fast+slow fetch |
| `frontend/src/test/app/mock-fetch.ts` | Add `sentenceSearchPreviewFastHandler` option; parse `fast` from body in default handler |
| `frontend/src/test/app/app-shell-search-sentence-verification.test.tsx` | Update loading test (two requests); add two-phase display test |

---

## Task 1: Backend schema — add `fast` field + `"preview"` status

**Files:**
- Modify: `backend/app/api/schemas/v1/sentencebank.py`

- [ ] **Step 1: Add fields**

Replace in `backend/app/api/schemas/v1/sentencebank.py`:

```python
class SentenceSearchPreviewRequest(BaseModel):
    source_text: str = Field(..., min_length=1, max_length=100)
    fast: bool = False


class SentenceSearchPreviewResponse(BaseModel):
    status: Literal["ready", "blocked", "preview"]
    query_language: Literal["da", "en", "unknown"] = "unknown"
    source_text: str | None = None
    english_translation: str | None = None
    is_valid: bool
    errors: list[SentenceVerificationErrorItem] = Field(default_factory=list)
    message: str | None = None
```

- [ ] **Step 2: Run lint**

```bash
cd backend && PYTHONPATH=. .venv/bin/python -m ruff check app/api/schemas/v1/sentencebank.py
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/schemas/v1/sentencebank.py
git commit -m "feat(schema): add fast param and preview status to sentence search preview"
```

---

## Task 2: Backend use-case — fix EN path + add fast path

**Files:**
- Modify: `backend/app/services/use_cases/sentencebank.py:213-303`

Current EN path (lines 223–247) calls `_verify_sentence_result` twice and `_lookup_phrase_translation` to retranslate DA→EN. Fix: use `initial_verification.corrected_text or normalized_query` as `english_translation`, translate that to DA, skip 2nd Gemini call and DA→EN retranslation.

Fast path: heuristic lang detect (æøå→DA, ASCII→EN, else unknown), Azure translate only, return `status="preview"`.

- [ ] **Step 1: Write failing tests** (see Task 3 — write tests first, then implement)

Skip to Task 3, then return here.

- [ ] **Step 2: Add `_heuristic_detect_language` method**

Add after `_detect_query_language` method (~line 303):

```python
def _heuristic_detect_language(self, source_text: str) -> Literal["da", "en", "unknown"]:
    lower = source_text.lower()
    if any(c in lower for c in ("æ", "ø", "å")):
        return "da"
    if source_text.isascii():
        return "en"
    return "unknown"
```

- [ ] **Step 3: Fix EN path in `preview_sentence_search` and add fast path**

Replace entire `preview_sentence_search` method (lines 213–261):

```python
def preview_sentence_search(self, source_text: str, *, fast: bool = False) -> SentenceSearchPreviewResponse:
    normalized_query = _normalize_sentence_text(source_text)
    if not normalized_query:
        raise ValueError("source_text is required")

    if fast:
        return self._preview_sentence_search_fast(normalized_query)

    initial_verification = self._verify_sentence_result(normalized_query)
    query_language = initial_verification.language
    if query_language == "unknown":
        query_language = self._detect_query_language(normalized_query)

    if query_language == "en":
        english_for_translation = initial_verification.corrected_text or normalized_query
        translated_danish = self._lookup_reverse_translation(english_for_translation)
        if not translated_danish:
            return SentenceSearchPreviewResponse(
                status="blocked",
                query_language="en",
                source_text=None,
                english_translation=None,
                is_valid=False,
                errors=[],
                message="Could not translate this English sentence to Danish.",
            )
        return SentenceSearchPreviewResponse(
            status="ready",
            query_language="en",
            source_text=translated_danish,
            english_translation=english_for_translation,
            is_valid=True,
            errors=[],
            message=None,
        )

    final_source_text = initial_verification.corrected_text or normalized_query
    return SentenceSearchPreviewResponse(
        status="ready",
        query_language=query_language,
        source_text=final_source_text,
        english_translation=self._lookup_phrase_translation(final_source_text),
        is_valid=initial_verification.is_valid,
        errors=[
            SentenceVerificationErrorItem(start=e.start, end=e.end, message=e.message)
            for e in initial_verification.errors
        ],
        message=None,
    )
```

Add new `_preview_sentence_search_fast` method after `preview_sentence_search`:

```python
def _preview_sentence_search_fast(self, normalized_query: str) -> SentenceSearchPreviewResponse:
    query_language = self._heuristic_detect_language(normalized_query)
    if query_language == "en":
        translated_danish = self._lookup_reverse_translation(normalized_query)
        if not translated_danish:
            return SentenceSearchPreviewResponse(
                status="blocked",
                query_language="en",
                source_text=None,
                english_translation=None,
                is_valid=True,
                errors=[],
                message=None,
            )
        return SentenceSearchPreviewResponse(
            status="preview",
            query_language="en",
            source_text=translated_danish,
            english_translation=normalized_query,
            is_valid=True,
            errors=[],
            message=None,
        )
    effective_language: Literal["da", "en", "unknown"] = "da" if query_language == "da" else "unknown"
    en_translation = self._lookup_phrase_translation(normalized_query)
    return SentenceSearchPreviewResponse(
        status="preview",
        query_language=effective_language,
        source_text=normalized_query,
        english_translation=en_translation,
        is_valid=True,
        errors=[],
        message=None,
    )
```

- [ ] **Step 4: Update route handler to pass `fast`**

In `backend/app/api/routes/sentencebank.py`, update `sentence_search_preview`:

```python
@router.post("/sentencebank/search-preview", response_model=SentenceSearchPreviewResponse)
def sentence_search_preview(
    payload: SentenceSearchPreviewRequest,
    request: Request,
) -> SentenceSearchPreviewResponse:
    return run_db_operation(
        request,
        lambda: _sentencebank_use_case(request).preview_sentence_search(
            payload.source_text, fast=payload.fast
        ),
        error_log_name="sentencebank_search_preview_db_operational_error",
    )
```

- [ ] **Step 5: Run lint**

```bash
cd backend && PYTHONPATH=. .venv/bin/python -m ruff check app/services/use_cases/sentencebank.py app/api/routes/sentencebank.py
```

Expected: no errors.

---

## Task 3: Backend tests — update EN tests + new fast-path tests

**Files:**
- Modify: `backend/tests/use_cases/test_sentencebank_use_case.py`
- Modify: `backend/tests/api/test_sentencebank_verify_route.py`

- [ ] **Step 1: Update `test_sentencebank_preview_sentence_search_translates_english_input`**

Replace the test at line 572 (remove unused 2nd-Gemini/DA→EN setup, add corrected_text assertion):

```python
def test_sentencebank_preview_sentence_search_translates_english_input(tmp_path: Path) -> None:
    verification_service = FakeSentenceVerificationService(
        results={
            "I am happy": SentenceVerificationResult(
                is_valid=True,
                errors=[],
                corrected_text=None,
                language="en",
            ),
        }
    )
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService(
            {"I am happy": "jeg er glad"},
            detected_languages={"I am happy": "EN"},
        ),
        sentence_verification_service=verification_service,
    )

    preview = use_case.preview_sentence_search("I am happy")

    assert preview.status == "ready"
    assert preview.query_language == "en"
    assert preview.source_text == "jeg er glad"
    assert preview.english_translation == "I am happy"
    assert preview.is_valid is True
    assert preview.errors == []
```

- [ ] **Step 2: Add test for Gemini-corrected EN used as `english_translation`**

Add after the test above:

```python
def test_sentencebank_preview_sentence_search_en_uses_gemini_corrected_text(tmp_path: Path) -> None:
    verification_service = FakeSentenceVerificationService(
        results={
            "i am hapy": SentenceVerificationResult(
                is_valid=False,
                errors=[SentenceVerificationErrorSpan(start=5, end=9, message="typo")],
                corrected_text="I am happy",
                language="en",
            ),
        }
    )
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService(
            {"I am happy": "jeg er glad"},
        ),
        sentence_verification_service=verification_service,
    )

    preview = use_case.preview_sentence_search("i am hapy")

    assert preview.status == "ready"
    assert preview.query_language == "en"
    assert preview.source_text == "jeg er glad"
    assert preview.english_translation == "I am happy"
    assert preview.is_valid is True
    assert preview.errors == []
```

- [ ] **Step 3: Update `test_sentencebank_preview_sentence_search_degrades_when_verification_unavailable`**

Remove unused `"jeg er glad": "i am happy"` from FakeTranslationService (no longer called):

```python
def test_sentencebank_preview_sentence_search_degrades_when_verification_unavailable(tmp_path: Path) -> None:
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService(
            {"I am happy": "jeg er glad"},
            detected_languages={"I am happy": "EN"},
        ),
        sentence_verification_service=FakeSentenceVerificationService(should_raise=True),
    )

    preview = use_case.preview_sentence_search("I am happy")

    assert preview.status == "ready"
    assert preview.query_language == "en"
    assert preview.source_text == "jeg er glad"
    assert preview.english_translation == "I am happy"
    assert preview.is_valid is True
    assert preview.errors == []
```

- [ ] **Step 4: Add fast-path tests**

Add at end of file:

```python
def test_sentencebank_preview_sentence_fast_path_danish(tmp_path: Path) -> None:
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"jeg er glad": "i am happy"}),
    )

    preview = use_case.preview_sentence_search("jeg er glad", fast=True)

    assert preview.status == "preview"
    assert preview.query_language == "da"
    assert preview.source_text == "jeg er glad"
    assert preview.english_translation == "I am happy"
    assert preview.is_valid is True
    assert preview.errors == []


def test_sentencebank_preview_sentence_fast_path_english(tmp_path: Path) -> None:
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"I am happy": "jeg er glad"}),
    )

    preview = use_case.preview_sentence_search("I am happy", fast=True)

    assert preview.status == "preview"
    assert preview.query_language == "en"
    assert preview.source_text == "jeg er glad"
    assert preview.english_translation == "I am happy"
    assert preview.is_valid is True
    assert preview.errors == []


def test_sentencebank_preview_sentence_fast_path_unknown_language(tmp_path: Path) -> None:
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({}),
    )

    preview = use_case.preview_sentence_search("café au lait", fast=True)

    assert preview.status == "preview"
    assert preview.query_language == "unknown"
    assert preview.source_text == "café au lait"
    assert preview.english_translation is None
    assert preview.is_valid is True
    assert preview.errors == []


def test_sentencebank_preview_sentence_fast_path_no_gemini_called(tmp_path: Path) -> None:
    verification_service = FakeSentenceVerificationService(
        results={
            "jeg er glad": SentenceVerificationResult(
                is_valid=False,
                errors=[SentenceVerificationErrorSpan(start=0, end=3, message="error")],
                corrected_text="jeg er glad",
                language="da",
            ),
        }
    )
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"jeg er glad": "i am happy"}),
        sentence_verification_service=verification_service,
    )

    preview = use_case.preview_sentence_search("jeg er glad", fast=True)

    assert preview.status == "preview"
    assert preview.is_valid is True
    assert preview.errors == []
    assert verification_service.calls == []
```

- [ ] **Step 5: Update API route test for EN path**

In `backend/tests/api/test_sentencebank_verify_route.py`, update `test_sentence_search_preview_translates_english_to_danish` — remove unused `translate_da_to_en` setup:

```python
def test_sentence_search_preview_translates_english_to_danish(tmp_path, stub_nlp_adapter_factory) -> None:
    app = build_api_test_app(tmp_path / "db.sqlite3", nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        provider = "stub"

        def translate_da_to_en(self, text: str) -> str | None:
            return None  # no longer called for EN path

        def translate_en_to_da(self, text: str) -> str | None:
            return "jeg er glad" if text == "I am happy" else None

        def detect_source_language(self, text: str) -> str | None:
            return "EN" if text == "I am happy" else "DA"

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        set_service_field(client.app, "sentence_verification_service", StubSentencePreviewVerificationService())
        response = client.post("/api/sentencebank/search-preview", json={"source_text": "I am happy"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "query_language": "en",
        "source_text": "jeg er glad",
        "english_translation": "I am happy",
        "is_valid": True,
        "errors": [],
        "message": None,
    }
```

Note: `StubSentencePreviewVerificationService` returns `corrected_text=None, language="en"` for "I am happy" — verify this in the test file's existing stub. `english_translation` should be `None or "I am happy"` = `"I am happy"`.

- [ ] **Step 6: Run backend tests**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/use_cases/test_sentencebank_use_case.py tests/api/test_sentencebank_verify_route.py
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/use_cases/sentencebank.py backend/app/api/routes/sentencebank.py backend/tests/use_cases/test_sentencebank_use_case.py backend/tests/api/test_sentencebank_verify_route.py
git commit -m "feat(sentencebank): fix EN english_translation, skip 2nd Gemini call, add fast preview path"
```

---

## Task 4: Frontend types + constants

**Files:**
- Modify: `frontend/src/app/core/types-api.ts:386-394`
- Modify: `frontend/src/app/core/constants.ts`

- [ ] **Step 1: Update `SentenceSearchPreviewResponse` type**

In `frontend/src/app/core/types-api.ts` at line 387, change:

```typescript
export type SentenceSearchPreviewResponse = {
  status: "ready" | "blocked" | "preview"
  query_language: "da" | "en" | "unknown"
  source_text: string | null
  english_translation: string | null
  is_valid: boolean
  errors: SentenceVerificationErrorItem[]
  message: string | null
}
```

- [ ] **Step 2: Update constants**

In `frontend/src/app/core/constants.ts`, replace `SENTENCE_VERIFY_DEBOUNCE_MS = 600` with:

```typescript
export const SENTENCE_DEBOUNCE_DA_MS = 200
export const SENTENCE_DEBOUNCE_EN_MS = 350
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/core/types-api.ts frontend/src/app/core/constants.ts
git commit -m "feat(types): add preview status to sentence search response, adaptive debounce constants"
```

---

## Task 5: Frontend hook — two-phase fetch + adaptive debounce

**Files:**
- Modify: `frontend/src/app/chrome/sidebar/use-sidebar-search.ts`

The hook currently imports `SENTENCE_VERIFY_DEBOUNCE_MS`. Replace with new constants and add `detectQueryLanguage`. Replace single-fetch sentence effect with parallel fast+slow fetch.

- [ ] **Step 1: Update imports**

Replace in `use-sidebar-search.ts` line 7:

```typescript
  BACKEND_URL,
  SEARCH_RESOLVE_DEBOUNCE_MS,
  SENTENCE_DEBOUNCE_DA_MS,
  SENTENCE_DEBOUNCE_EN_MS,
  SENTENCE_VERIFY_MAX_CHARS,
```

(Remove `SENTENCE_VERIFY_DEBOUNCE_MS`, add two new constants.)

- [ ] **Step 2: Add `detectQueryLanguage` helper**

Add before the `useSidebarSearch` function definition:

```typescript
function detectQueryLanguage(text: string): "da" | "en" | "unknown" {
  if (/[æøåÆØÅ]/u.test(text)) return "da"
  if (/^[\x00-\x7F\s]*$/u.test(text)) return "en"
  return "unknown"
}
```

- [ ] **Step 3: Replace sentence search effect with two-phase parallel fetch**

Replace the entire `useEffect` block starting at line 223 (`useEffect(() => {`) through line 284 (`}, [apiClient, isSentenceMode, sentenceQuery, wordbankCacheVersion, searchTranslationConfigVersion])`):

```typescript
  useEffect(() => {
    if (!isSentenceMode || !sentenceQuery) {
      setSentenceSearchPreview(null)
      setSentenceSearchPreviewError(null)
      setIsSentenceSearchPreviewLoading(false)
      return
    }

    const cached = sentenceSearchPreviewCacheRef.current.get(sentenceQuery)
    if (cached) {
      setSentenceSearchPreview({ query: sentenceQuery, result: cached })
      setIsSentenceSearchPreviewLoading(false)
      setSentenceSearchPreviewError(null)
      return
    }

    let cancelled = false
    let gotFullResult = false
    setSentenceSearchPreview(null)
    setIsSentenceSearchPreviewLoading(true)
    setSentenceSearchPreviewError(null)

    const detectedLang = detectQueryLanguage(sentenceQuery)
    const debounceMs = detectedLang === "da" ? SENTENCE_DEBOUNCE_DA_MS : SENTENCE_DEBOUNCE_EN_MS

    const timeoutId = window.setTimeout(() => {
      const fastPromise = apiClient.postJson<SentenceSearchPreviewResponse>(
        "/api/sentencebank/search-preview",
        { source_text: sentenceQuery, fast: true },
        "Could not prepare sentence preview.",
      )
      const fullPromise = apiClient.postJson<SentenceSearchPreviewResponse>(
        "/api/sentencebank/search-preview",
        { source_text: sentenceQuery, fast: false },
        "Could not prepare sentence preview.",
      )

      void fastPromise.then((fastResult) => {
        if (!cancelled && !gotFullResult) {
          setSentenceSearchPreview({ query: sentenceQuery, result: fastResult })
        }
      })

      void fullPromise
        .then((fullResult) => {
          if (cancelled) return
          gotFullResult = true
          sentenceSearchPreviewCacheRef.current.set(sentenceQuery, fullResult)
          setSentenceSearchPreview({ query: sentenceQuery, result: fullResult })
          setSentenceSearchPreviewError(null)
        })
        .catch((error) => {
          if (cancelled) return
          gotFullResult = true
          const fallback: SentenceSearchPreviewResponse = {
            status: "ready",
            query_language: "unknown",
            source_text: sentenceQuery,
            english_translation: null,
            message: null,
            is_valid: true,
            errors: [],
          }
          setSentenceSearchPreviewError(
            error instanceof Error ? error.message : "Could not prepare sentence preview.",
          )
          setSentenceSearchPreview({ query: sentenceQuery, result: fallback })
        })
        .finally(() => {
          if (!cancelled) {
            setIsSentenceSearchPreviewLoading(false)
          }
        })
    }, debounceMs)

    return () => {
      cancelled = true
      window.clearTimeout(timeoutId)
      setIsSentenceSearchPreviewLoading(false)
    }
  }, [apiClient, isSentenceMode, sentenceQuery, wordbankCacheVersion, searchTranslationConfigVersion])
```

- [ ] **Step 4: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/chrome/sidebar/use-sidebar-search.ts
git commit -m "feat(search): two-phase sentence search, adaptive debounce (200ms DA / 350ms EN)"
```

---

## Task 6: Frontend tests — update mock + tests

**Files:**
- Modify: `frontend/src/test/app/mock-fetch.ts`
- Modify: `frontend/src/test/app/app-shell-search-sentence-verification.test.tsx`

- [ ] **Step 1: Update mock-fetch type to include `fast` in preview response type**

In `frontend/src/test/app/mock-fetch.ts` at line 613, update `sentenceSearchPreviewResponse` type to include `status: "ready" | "blocked" | "preview"`:

```typescript
  sentenceSearchPreviewResponse?: {
    status: "ready" | "blocked" | "preview"
    query_language: "da" | "en" | "unknown"
    source_text: string | null
    english_translation: string | null
    is_valid: boolean
    errors: Array<{ start: number; end: number; message: string }>
    message: string | null
  }
  sentenceSearchPreviewFastResponse?: {
    status: "ready" | "blocked" | "preview"
    query_language: "da" | "en" | "unknown"
    source_text: string | null
    english_translation: string | null
    is_valid: boolean
    errors: Array<{ start: number; end: number; message: string }>
    message: string | null
  }
  sentenceSearchPreviewOk?: boolean
  sentenceSearchPreviewHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
```

- [ ] **Step 2: Update default fast response and URL handler in mock-fetch**

Near line 885, add default fast response:

```typescript
  const sentenceSearchPreviewResponse = options?.sentenceSearchPreviewResponse ?? {
    status: "ready" as const,
    query_language: "da" as const,
    source_text: "Jeg elsker dansk",
    english_translation: "I love Danish",
    is_valid: true,
    errors: [],
    message: null,
  }
  const sentenceSearchPreviewFastResponse = options?.sentenceSearchPreviewFastResponse ?? {
    ...sentenceSearchPreviewResponse,
    status: sentenceSearchPreviewResponse.status === "blocked" ? "blocked" as const : "preview" as const,
  }
```

Near line 1289, update the URL handler to check `fast` from body:

```typescript
    if (url.endsWith("/api/sentencebank/search-preview")) {
      if (options?.sentenceSearchPreviewHandler) {
        return options.sentenceSearchPreviewHandler(input, init)
      }
      if (options?.sentenceSearchPreviewOk === false) {
        return new Response(null, { status: 500 })
      }
      const body = JSON.parse(String(init?.body ?? "{}")) as { fast?: boolean }
      return responseOf(body.fast ? sentenceSearchPreviewFastResponse : sentenceSearchPreviewResponse)
    }
```

- [ ] **Step 3: Update loading UI test — handle two concurrent requests**

In `app-shell-search-sentence-verification.test.tsx`, update the first test `"shows verification loading UI while verifying a sentence"`:

```typescript
  it("shows verification loading UI while verifying a sentence", async () => {
    const resolvers: Array<() => void> = []
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      sentenceSearchPreviewHandler: async () => {
        await new Promise<void>((resolve) => {
          resolvers.push(resolve)
        })
        return responseOf({
          status: "ready",
          query_language: "da",
          source_text: "jeg er glad",
          english_translation: "I am happy",
          is_valid: true,
          errors: [],
          message: null,
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "jeg er glad")

    expect(await within(dialog).findByRole("option")).toHaveAttribute("aria-disabled", "true")
    expect(within(dialog).getByTestId("sentence-search-translation-skeleton")).toBeInTheDocument()
    resolvers.forEach((r) => r())
  })
```

- [ ] **Step 4: Add test for fast preview shown before full result**

Add new test in the `describe` block:

```typescript
  it("shows fast preview result immediately then replaces with full result", async () => {
    let resolveFullPreview: (() => void) | null = null
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      sentenceSearchPreviewHandler: async (_input, init) => {
        const body = JSON.parse(String(init?.body ?? "{}")) as { fast?: boolean }
        if (body.fast) {
          return responseOf({
            status: "preview",
            query_language: "da",
            source_text: "jeg er glad",
            english_translation: "I am happy",
            is_valid: true,
            errors: [],
            message: null,
          })
        }
        await new Promise<void>((resolve) => {
          resolveFullPreview = resolve
        })
        return responseOf({
          status: "ready",
          query_language: "da",
          source_text: "jeg er glad",
          english_translation: "I am happy",
          is_valid: true,
          errors: [],
          message: null,
        })
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const dialog = await openSearch()
    typeInSearch(dialog, "jeg er glad")

    // Fast preview shows the sentence card (option not disabled)
    await waitFor(() => {
      const option = getSentenceOption(dialog)
      expect(within(option).getByText(/^jeg er glad$/i)).toBeInTheDocument()
    })

    // Loading indicator still visible (full request pending)
    expect(within(dialog).getByTestId("sentence-search-translation-skeleton")).toBeInTheDocument()

    resolveFullPreview?.()

    // After full resolves, loading gone
    await waitFor(() => {
      expect(within(dialog).queryByTestId("sentence-search-translation-skeleton")).not.toBeInTheDocument()
    })
  })
```

- [ ] **Step 5: Run frontend tests**

```bash
cd frontend && npx vitest run src/test/app/app-shell-search-sentence-verification.test.tsx
```

Expected: all pass.

- [ ] **Step 6: Run all frontend tests**

```bash
cd frontend && npx vitest run
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/test/app/mock-fetch.ts frontend/src/test/app/app-shell-search-sentence-verification.test.tsx
git commit -m "test: update sentence search tests for two-phase fetch and adaptive debounce"
```

---

## Task 7: Full verification + docs

- [ ] **Step 1: Run full backend test suite**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/
```

Expected: all pass.

- [ ] **Step 2: Run make lint + make test**

```bash
make lint && make test
```

Expected: all pass.

- [ ] **Step 3: Update API contract doc**

In `docs/contracts/api-contract.md`, find `POST /api/sentencebank/search-preview` section and update:

```markdown
### POST `/api/sentencebank/search-preview`
- **Request model:** `SentenceSearchPreviewRequest` (`source_text: str`, `fast: bool = False`).
- **Response model:** `SentenceSearchPreviewResponse` (`status: "ready" | "blocked" | "preview"`, `query_language`, `source_text`, `english_translation`, `is_valid`, `errors`, `message`).
- **Notable behavior:** `fast=true` skips Gemini verification, uses heuristic language detection and Azure translate only. Returns `status="preview"`. `fast=false` (default) runs full Gemini verification and returns `status="ready"` or `"blocked"`. EN queries: `english_translation` is the Gemini-corrected original English (not a retranslation from Danish).
```

- [ ] **Step 4: Commit docs**

```bash
git add docs/contracts/api-contract.md
git commit -m "docs: update api-contract for fast preview param and EN translation fix"
```

---

## Self-Review

**Spec coverage:**
- [x] EN `english_translation` uses Gemini `corrected_text` (Task 2, 3)
- [x] 2nd Gemini call removed for EN path (Task 2 — `_verify_sentence_result(translated_danish)` removed)
- [x] Fast path added (Task 2 `_preview_sentence_search_fast`)
- [x] Adaptive debounce 200ms DA / 350ms EN (Task 4, 5)
- [x] Parallel fast+slow requests (Task 5)
- [x] Fast shows first, slow replaces (Task 5 `gotFullResult` guard)
- [x] Schema `"preview"` status (Task 1)
- [x] Tests cover all paths (Task 3, 6)
- [x] Docs updated (Task 7)

**Placeholder scan:** No TBD/TODO/placeholder found.

**Type consistency:**
- `SentenceSearchPreviewResponse.status` → `"ready" | "blocked" | "preview"` in Pydantic schema, Python Literal, TypeScript type, and mock-fetch type — all consistent.
- `preview_sentence_search(source_text, *, fast=False)` → route passes `payload.fast` — consistent.
- `SENTENCE_DEBOUNCE_DA_MS`, `SENTENCE_DEBOUNCE_EN_MS` defined in constants.ts, imported in use-sidebar-search.ts — consistent.
- `detectQueryLanguage` defined and used within same file — consistent.
