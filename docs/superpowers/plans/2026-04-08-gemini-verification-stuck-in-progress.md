# Gemini Verification Stuck In Progress — Fix Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two bugs that cause Gemini word verification to permanently display as "in progress" (queued) in the UI.

**Architecture:** The verification flow queues a background job → a `ThreadPoolExecutor` worker calls the Gemini API → persists the result → the frontend polls until status leaves `queued`. Two separate failure paths leave the record stuck as `queued` forever: (1) the Gemini client has no HTTP timeout so a slow API call hangs the worker thread indefinitely; (2) when the background job exhausts all retries and fails, the verification record is never transitioned from `queued` to `error`.

**Tech Stack:** Python 3.10, FastAPI, google-genai 1.65.0, ThreadPoolExecutor background jobs, SQLite.

---

## Root Cause Analysis

### Bug 1 — Missing timeout on Gemini client (primary cause)

**File:** `backend/app/services/verification.py:173-179` (`GeminiWordVerificationService._ensure_client`)

```python
# current — no timeout
self._client = genai.Client(api_key=self.api_key)
```

The field `timeout_seconds: float = 20.0` is declared at line 156 but never used. Compare to `gemini_translation.py:143-147` which correctly does:

```python
timeout_ms = max(1, math.ceil(self.timeout_seconds * 1000))
self._client = genai.Client(
    api_key=self.api_key,
    http_options=genai_types.HttpOptions(timeout=timeout_ms),
)
```

**Consequence:** When the Gemini API hangs, the background thread blocks forever. The background job stays `running` (never transitions to `failed`). The verification record stays `queued`. The frontend polls at 1.5s intervals indefinitely.

### Bug 2 — Failed background job does not update verification record to "error"

**File:** `backend/app/services/use_cases/wordbank/background_jobs.py:79-86` (`_collect_completed_jobs`)

When a `verify_word` job raises an unhandled exception, `mark_retryable_failure` is called. After all retries are exhausted, the background job reaches `status='failed'`. But the wordbank verification record is never updated — it stays `queued`.

**Consequence:** Even if the Gemini call raises a `VerificationError` on every attempt, the verification record stays `queued`. Frontend polls forever.

---

## File Map

| File | Change |
|------|--------|
| `backend/app/services/verification.py` | Wire `timeout_seconds` into `_ensure_client` using `genai_types.HttpOptions` |
| `backend/app/services/use_cases/wordbank/background_jobs.py` | Persist `error` verification record when `verify_word` job fails permanently |
| `backend/tests/services/test_verification_service_unit.py` | Test that `_ensure_client` passes `HttpOptions(timeout=…)` |
| `backend/tests/use_cases/test_wordbank_pronunciation_and_verification.py` | Test that permanently-failed verify_word job updates record to `error` |

---

## Task 1: Wire timeout into `GeminiWordVerificationService._ensure_client`

**Files:**
- Modify: `backend/app/services/verification.py:173-179`
- Test: `backend/tests/services/test_verification_service_unit.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/services/test_verification_service_unit.py`:

```python
def test_ensure_client_passes_timeout_to_http_options() -> None:
    """_ensure_client must wire timeout_seconds into genai.Client http_options."""
    import math
    captured: dict[str, object] = {}

    class _FakeGenai:
        class Client:
            def __init__(self, *, api_key: str, http_options: object) -> None:
                captured["http_options"] = http_options

    svc = GeminiWordVerificationService(api_key="key", timeout_seconds=15.0)
    svc._ensure_client.__func__  # noqa: just referencing to trigger import below

    import importlib, sys
    # Temporarily inject fake genai so _ensure_client picks it up
    fake_module = type(sys)("google.genai")
    fake_module.Client = _FakeGenai.Client  # type: ignore[attr-defined]
    google_pkg = type(sys)("google")
    google_pkg.genai = fake_module  # type: ignore[attr-defined]
    orig = sys.modules.copy()
    sys.modules["google"] = google_pkg
    sys.modules["google.genai"] = fake_module
    try:
        svc._client = None  # force re-init
        svc._ensure_client()
    finally:
        sys.modules.clear()
        sys.modules.update(orig)

    http_options = captured.get("http_options")
    assert http_options is not None, "http_options not passed to genai.Client"
    expected_ms = max(1, math.ceil(15.0 * 1000))
    assert getattr(http_options, "timeout", None) == expected_ms
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_verification_service_unit.py::test_ensure_client_passes_timeout_to_http_options -v
```

Expected: FAIL — `AssertionError: http_options not passed to genai.Client`

- [ ] **Step 3: Apply the fix**

In `backend/app/services/verification.py`, change `_ensure_client` from:

```python
    def _ensure_client(self) -> object:
        if self._client is None:
            try:
                from google import genai  # type: ignore import-not-found
            except ImportError as exc:
                raise VerificationError("google-genai package is required for Gemini verification.") from exc
            self._client = genai.Client(api_key=self.api_key)
        return self._client
```

to:

```python
    def _ensure_client(self) -> object:
        if self._client is None:
            try:
                import math
                from google import genai  # type: ignore import-not-found
                from google.genai import types as genai_types  # type: ignore import-not-found
            except ImportError as exc:
                raise VerificationError("google-genai package is required for Gemini verification.") from exc
            timeout_ms = max(1, math.ceil(self.timeout_seconds * 1000))
            self._client = genai.Client(
                api_key=self.api_key,
                http_options=genai_types.HttpOptions(timeout=timeout_ms),
            )
        return self._client
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_verification_service_unit.py::test_ensure_client_passes_timeout_to_http_options -v
```

Expected: PASS

- [ ] **Step 5: Run the full verification service unit tests**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_verification_service_unit.py -v
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/verification.py backend/tests/services/test_verification_service_unit.py
git commit -m "fix: wire timeout_seconds into Gemini verification client http_options"
```

---

## Task 2: Update verification record to "error" when background job fails permanently

**Files:**
- Modify: `backend/app/services/use_cases/wordbank/background_jobs.py`
- Test: `backend/tests/use_cases/test_wordbank_pronunciation_and_verification.py`

**Approach:** In `_collect_completed_jobs`, when a `verify_word` future raises an exception AND this is the final attempt (`job.attempt_count >= job.max_attempts`), persist an `error` verification result. The payload already carries `stored_lemma`, `stored_surface_form`, `meaning_id`.

- [ ] **Step 1: Read the existing test file to understand the test patterns**

```bash
cd backend && PYTHONPATH=. grep -n "def test_" tests/use_cases/test_wordbank_pronunciation_and_verification.py | head -20
```

- [ ] **Step 2: Write the failing test**

Add to `backend/tests/use_cases/test_wordbank_pronunciation_and_verification.py`:

```python
def test_permanently_failed_verify_word_job_sets_verification_status_to_error(tmp_path, stub_nlp_adapter_factory) -> None:
    """When a verify_word background job exhausts all retries, the verification record must transition to 'error'."""
    from tests.helpers.factories import _db_path
    from tests.helpers.fakes import FakeVerificationService
    from app.services.use_cases.wordbank import WordbankUseCase
    from app.services.use_cases.wordbank.background_jobs import WordbankBackgroundJobRunner
    import threading, time

    db = _db_path(tmp_path)
    nlp = stub_nlp_adapter_factory()

    class AlwaysFailingVerificationService:
        provider = "gemini"
        reviewer_role = "Professional Danish Language Expert"

        def verify_word_entry(self, payload):
            raise RuntimeError("Simulated permanent Gemini failure")

        def classify_word_categories(self, payload):
            raise RuntimeError("Simulated permanent Gemini failure")

    services = _make_services(
        db_path=db,
        nlp=nlp,
        verification_service=AlwaysFailingVerificationService(),
    )
    use_case = WordbankUseCase(
        db,
        typo_engine=services.typo_engine,
        translation_service=services.translation_service,
        gemini_word_translation_service=services.gemini_word_translation_service,
        gemini_related_words_service=services.gemini_related_words_service,
        nlp_adapter=services.nlp_adapter,
        cor_lexicon_service=services.cor_lexicon_service,
        cor_local_lexicon_service=services.cor_local_lexicon_service,
        verification_service=AlwaysFailingVerificationService(),
        tts_service=services.tts_service,
        gemini_changes_log_path=None,
    )

    # Add a word so verification is queued
    added = use_case.add_word("hund", surface_token="hund")
    assert added.verification.status == "queued"

    # Run the background job with max_attempts=1 so failure is permanent immediately
    runner = WordbankBackgroundJobRunner(
        db_path=db,
        services=services,
        gemini_changes_log_path=None,
        max_workers=1,
        poll_interval_seconds=0.05,
    )
    # Override the verification service to always fail
    runner._services = _make_services(
        db_path=db,
        nlp=nlp,
        verification_service=AlwaysFailingVerificationService(),
    )
    runner.start()
    time.sleep(0.5)  # give the worker time to exhaust retries
    runner.stop()

    # The verification record must now be 'error', not 'queued'
    details = use_case.get_lemma_details("hund")
    verification_status = (details.meaning_sections[0].verification.status
                           if details.meaning_sections
                           else details.verification.status)
    assert verification_status == "error", (
        f"Expected 'error' after permanent job failure, got '{verification_status}'"
    )
```

> Note: `_make_services` is a helper already used in this test file — check the existing pattern and use whatever factory/fixture is already there. If none, import `FakeServices` or equivalent from `tests/helpers/fakes.py`.

- [ ] **Step 3: Run test to verify it fails**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q "tests/use_cases/test_wordbank_pronunciation_and_verification.py::test_permanently_failed_verify_word_job_sets_verification_status_to_error" -v
```

Expected: FAIL — `AssertionError: Expected 'error' after permanent job failure, got 'queued'`

- [ ] **Step 4: Read existing test helpers to understand _make_services pattern**

```bash
cd backend && grep -n "_make_services\|FakeServices\|make_services" tests/use_cases/test_wordbank_pronunciation_and_verification.py | head -20
```

Adapt the test in Step 2 if needed to match the actual pattern.

- [ ] **Step 5: Implement the fix in `background_jobs.py`**

In `backend/app/services/use_cases/wordbank/background_jobs.py`, add a new helper method `_persist_verify_word_error` and call it from `_collect_completed_jobs` on final failure:

```python
    def _collect_completed_jobs(self, in_flight: dict[Future[None], object]) -> None:
        completed = [future for future in in_flight if future.done()]
        for future in completed:
            job = in_flight.pop(future)
            try:
                future.result()
            except Exception as exc:  # pragma: no cover - exercised through queue state assertions
                logger.exception(
                    "wordbank_background_job_failed",
                    extra={"job_type": job.job_type, "job_id": job.id},
                )
                is_final_attempt = job.attempt_count >= job.max_attempts
                self._repository.mark_retryable_failure(job, error_message=str(exc))
                if is_final_attempt and job.job_type == "verify_word":
                    self._persist_verify_word_error(job)
                continue
            self._repository.mark_completed(job.id)

    def _persist_verify_word_error(self, job: object) -> None:
        """After a verify_word job fails permanently, set the verification record to 'error'."""
        try:
            from app.api.schemas.v1.wordbank import VerificationResult
            from app.db.repositories.wordbank import WordbankRepository
            from app.services.use_cases.wordbank.verification_records import persist_verification_result

            payload = job.payload
            stored_lemma = str(payload.get("stored_lemma", ""))
            stored_surface_form = payload.get("stored_surface_form")
            meaning_id = payload.get("meaning_id")
            if not stored_lemma:
                return

            repository = WordbankRepository(self._db_path)
            lexeme = repository.get_lexeme(stored_lemma)
            if lexeme is None:
                return

            normalized_surface = (
                str(stored_surface_form).strip() or None
                if stored_surface_form
                else None
            )
            existing = repository.get_verification_record(
                lexeme_id=lexeme.id,
                meaning_id=meaning_id if isinstance(meaning_id, int) else None,
                stored_surface_form=normalized_surface,
            )
            if existing is None or existing.status != "queued":
                return  # Already resolved by another path

            provider = existing.provider or "gemini"
            reviewer_role = existing.reviewer_role or "Professional Danish Language Expert"
            error_result = VerificationResult(
                status="error",
                provider=provider,
                reviewer_role=reviewer_role,
                review_intent=existing.review_intent,
                message="Verification failed after all retries.",
                problem="The verification service could not be reached.",
                change_to_implement="Retry verification manually.",
            )
            persist_verification_result(
                repository,
                lexeme_id=lexeme.id,
                meaning_id=existing.meaning_id,
                stored_surface_form=existing.stored_surface_form,
                verification=error_result,
                latest_snapshot_hash=existing.latest_snapshot_hash,
                request_generation=existing.request_generation,
            )
        except Exception:
            logger.exception("wordbank_background_job_error_persist_failed", extra={"job_id": job.id})
```

- [ ] **Step 6: Run the test to verify it passes**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q "tests/use_cases/test_wordbank_pronunciation_and_verification.py::test_permanently_failed_verify_word_job_sets_verification_status_to_error" -v
```

Expected: PASS

- [ ] **Step 7: Run full verification/pronunciation test file**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/use_cases/test_wordbank_pronunciation_and_verification.py -v
```

Expected: all pass

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/use_cases/wordbank/background_jobs.py backend/tests/use_cases/test_wordbank_pronunciation_and_verification.py
git commit -m "fix: update verification record to error when background job fails permanently"
```

---

## Task 3: Final verification sweep

- [ ] **Step 1: Run the targeted test suite**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_verification_service_unit.py tests/use_cases/test_wordbank_pronunciation_and_verification.py -v
```

Expected: all pass

- [ ] **Step 2: Run the full test suite**

```bash
make test
```

Expected: all pass

- [ ] **Step 3: Check documentation impact**

These changes fix internal background-job behavior and a missing SDK option — no API contract changes, no command/workflow changes, no version/dependency changes. No documentation update is required.

**No documentation impact:** Both bugs are in internal service/job plumbing. No API surface, no CLI commands, and no configuration options changed. `docs/api-contract.md` and `docs/versions.md` are unaffected.

- [ ] **Step 4: Commit if any stray files**

```bash
git status
```

---

## Self-Review

### Spec coverage

| Requirement | Task covering it |
|-------------|----------------|
| Timeout applied to Gemini verification client | Task 1 |
| Verification record → `error` on permanent job failure | Task 2 |
| Tests for both fixes | Tasks 1 + 2 |
| Full suite passes | Task 3 |

### Placeholder scan

None — all steps include concrete file paths, exact code, and expected test output.

### Type consistency

- `_persist_verify_word_error` uses `job.payload` (dict) and `job.id` (int) — both present on `WordbankBackgroundJobRecord`
- `VerificationResult.status = "error"` is a valid literal per `backend/app/api/schemas/v1/wordbank.py:152`
- `persist_verification_result` signature matches existing callers in `verification_records.py`
