# Batch Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Batch N individual Gemini verification calls into 1 call when adding sentences.

**Architecture:** Add `verify_word_entries_batch()` to verification service protocol + implementation. Batch prompt includes all word contexts + shared sentence context. Single Gemini call returns per-word verdicts. Sentencebank triggers batch after token resolution. Falls back to individual queuing on failure.

**Tech Stack:** Python, Gemini Flash, existing verification prompt patterns, pytest, monkeypatch

---

### Task 1: Batch verification prompt builder

**Files:**
- Modify: `backend/app/services/verification_prompt_templates.py`
- Test: `backend/tests/services/test_verification_prompt_templates_batch.py`

- [ ] **Step 1: Write failing test — batch prompt includes sentence context**

```python
# test_verification_prompt_templates_batch.py
from __future__ import annotations

from app.services.verification_prompt_templates import build_batch_verification_prompt


def test_batch_prompt_includes_sentence_context():
    entries = [{"word_id": 0, "lemma": "hus"}]
    prompt = build_batch_verification_prompt(entries=entries, sentence_context="Jeg har et hus")

    assert "sentence_context" in prompt
    assert "Jeg har et hus" in prompt
```

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_verification_prompt_templates_batch.py -v`
Expected: FAIL — `ImportError` or `AttributeError`

- [ ] **Step 2: Write failing test — batch prompt includes all entries**

```python
def test_batch_prompt_includes_multiple_entries():
    entries = [
        {"word_id": 0, "current_entry": {"lemma": "hus"}},
        {"word_id": 1, "current_entry": {"lemma": "kat"}},
    ]
    prompt = build_batch_verification_prompt(entries=entries, sentence_context="Hus og kat")

    assert '"word_id": 0' in prompt
    assert '"word_id": 1' in prompt
    assert '"lemma": "hus"' in prompt
    assert '"lemma": "kat"' in prompt
```

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_verification_prompt_templates_batch.py -v`
Expected: FAIL

- [ ] **Step 3: Write failing test — batch prompt response format**

```python
def test_batch_prompt_requests_results_array():
    entries = [{"word_id": 0, "current_entry": {"lemma": "hus"}}]
    prompt = build_batch_verification_prompt(entries=entries, sentence_context="hus")

    assert '"results"' in prompt
    assert '"word_id"' in prompt
    assert "JSON only" in prompt
```

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_verification_prompt_templates_batch.py -v`
Expected: FAIL

- [ ] **Step 4: Write failing test — batch prompt includes core verification rules**

```python
def test_batch_prompt_includes_verification_rules():
    entries = [{"word_id": 0, "current_entry": {"lemma": "hus"}}]
    prompt = build_batch_verification_prompt(entries=entries, sentence_context="hus")

    assert "Translations belong to the lemma or meaning section only" in prompt
    assert "Surface forms do not have independent translations" in prompt
    assert "gloss" in prompt.lower()
    assert "Never suggest editing a gloss" in prompt
    assert "idiomatic English" in prompt
```

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_verification_prompt_templates_batch.py -v`
Expected: FAIL

- [ ] **Step 5: Implement `build_batch_verification_prompt`**

Add to `backend/app/services/verification_prompt_templates.py`:

```python
def build_batch_verification_prompt(
    *,
    entries: list[dict[str, object]],
    sentence_context: str | None = None,
) -> str:
    entry_json = json.dumps(entries, ensure_ascii=False)
    context_line = f'\n"sentence_context": {json.dumps(sentence_context)}\n' if sentence_context else ""
    return (
        "You are a Professional Danish Language Expert.\n"
        "Review each saved wordbank target.\n"
        "Translations belong to the lemma or meaning section only.\n"
        "Surface forms do not have independent translations.\n"
        "Glosses are sense labels. Never suggest editing a gloss.\n"
        "Treat glosses and gloss translations as fixed COR reference labels, not editable user content.\n"
        "Only review whether the saved English translation fits the saved lemma or meaning.\n"
        "Use the reviewed target, relevant surface forms, and sibling meanings only as needed.\n"
        "Count if the reviewed entry is composed of multiple words.\n"
        "Return JSON only.\n"
        '{"results":[{"word_id":0,"verdict":"correct|incorrect","word_count":0,'
        '"problem":"...","change_to_implement":"...","suggested_actions":'
        '[{"action_type":"fix_translation","english_translation":"...","reason":"..."},'
        '{"action_type":"move_to_meaning_section","target_meaning_id":0,"reason":"..."},'
        '{"action_type":"move_to_lemma","target_lemma":"...","target_meaning_key":"...","target_gloss":"...","'
        'target_english_translation":"...","target_pos_tag":"...","target_morphology":"...","reason":"..."}]}]}\n'
        "Rules:\n"
        "- Use only these action types: fix_translation, move_to_meaning_section, move_to_lemma.\n"
        "- If verdict=correct, return suggested_actions as [].\n"
        "- If action_type=move_to_meaning_section, target_meaning_id must be one of the available meaning ids.\n"
        "- If action_type=move_to_lemma, include target_lemma and target_meaning_key.\n"
        "- Never propose gloss edits; use gloss only to identify the intended meaning section.\n"
        "- Never criticize, rewrite, or score the gloss text or gloss translation itself.\n"
        "- If action_type=fix_translation, english_translation must be idiomatic English. Never repeat the Danish lemma or surface form unless the translated gloss explicitly matches it.\n"
        "- Keep problem to one short sentence.\n"
        "- Keep change_to_implement to one short imperative sentence.\n"
        "- When meaning_gloss_translation or section gloss_translation is present, use it as the main sense clue for homographs.\n"
        "- If canonical_lemma is present and differs from lemma, treat the saved lemma as incorrect and suggest move_to_lemma to canonical_lemma unless the entry already belongs under another provided lemma.\n"
        "- When gram_raw or paradigm_slot_surface_forms identify a valid paradigm slot for the saved surface form, do not move that form to a different lemma just because the spelling is also a noun or another homograph elsewhere.\n"
        '- Keep message short: use "OK" or "Review needed".\n'
        "- Suggested actions must be self-contained. Do not rely on prose fields for apply details.\n"
        f"Sentence context:{context_line}"
        f"Entries:\n{entry_json}"
    )
```

- [ ] **Step 6: Run tests, verify all pass**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_verification_prompt_templates_batch.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/verification_prompt_templates.py backend/tests/services/test_verification_prompt_templates_batch.py
git commit -m "feat: add batch verification prompt builder"
```

---

### Task 2: Batch verification protocol + service

**Files:**
- Modify: `backend/app/services/verification.py`
- Modify: `backend/tests/services/test_verification_service_unit.py`

- [ ] **Step 1: Write failing test — protocol has batch method**

```python
# Add to test_verification_service_unit.py

def test_word_verification_service_protocol_has_batch_method():
    from app.services.verification import WordVerificationService

    assert hasattr(WordVerificationService, "verify_word_entries_batch")
```

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_verification_service_unit.py::test_word_verification_service_protocol_has_batch_method -v`
Expected: FAIL — `AttributeError`

- [ ] **Step 2: Add `verify_word_entries_batch` to protocol**

In `backend/app/services/verification.py`, add to `WordVerificationService`:

```python
class WordVerificationService(Protocol):
    provider: str
    reviewer_role: str

    def verify_word_entry(self, payload: WordVerificationInput) -> WordVerificationResult: ...
    def classify_word_categories(self, payload: WordVerificationInput) -> WordCategoryClassificationResult: ...
    def verify_word_entries_batch(
        self, payloads: list[WordVerificationInput], sentence_context: str | None = None,
    ) -> list[WordVerificationResult]: ...
```

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_verification_service_unit.py::test_word_verification_service_protocol_has_batch_method -v`
Expected: PASS

- [ ] **Step 3: Write failing test — batch service returns per-word results**

```python
def test_gemini_batch_verification_returns_per_word_results(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_content",
        lambda prompt, config: type("R", (), {
            "text": (
                '{"results":['
                '{"word_id":0,"verdict":"correct","word_count":1,"suggested_actions":[]},'
                '{"word_id":1,"verdict":"incorrect","word_count":1,"problem":"mismatch","change_to_implement":"fix","suggested_actions":[]}'
                ']}'
            ),
        })(),
    )

    results = service.verify_word_entries_batch([_payload(), _mor_payload()], sentence_context="test sentence")

    assert len(results) == 2
    assert results[0].verdict == "verified"
    assert results[1].verdict == "flagged"
```

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_verification_service_unit.py::test_gemini_batch_verification_returns_per_word_results -v`
Expected: FAIL — `AttributeError`

- [ ] **Step 4: Refactor `verify_word_entry` — extract `_process_single_verdict`**

In `backend/app/services/verification.py`, extract the post-processing logic from `verify_word_entry` into a helper:

```python
def _process_single_verdict(
    self, payload: WordVerificationInput, parsed: dict[str, object]
) -> WordVerificationResult:
    """Post-process a parsed Gemini verdict dict into a WordVerificationResult."""
    fallback_word_count = self._infer_word_count(payload)

    verdict = parsed.get("verdict")
    word_count_raw = parsed.get("word_count")
    word_count = int(word_count_raw) if isinstance(word_count_raw, int) else fallback_word_count
    problem = parsed.get("problem") if isinstance(parsed.get("problem"), str) else None
    change_to_implement = (
        parsed.get("change_to_implement") if isinstance(parsed.get("change_to_implement"), str) else None
    )
    raw_suggested_actions = parsed.get("suggested_actions")
    suggested_actions = tuple(self._parse_suggested_actions(raw_suggested_actions, payload))
    if should_backfill_translation_from_gloss_hint(
        payload=payload,
        raw_suggested_actions=raw_suggested_actions,
        suggested_actions=suggested_actions,
    ):
        suggested_actions = (self._gloss_hint_translation_action(payload),)

    force_translation_fix = should_force_translation_fix_from_gloss_hint(
        payload=payload,
        suggested_actions=suggested_actions,
    )
    if force_translation_fix:
        suggested_actions = (self._gloss_hint_translation_action(payload),)
    problem, change_to_implement = normalize_translation_review_copy(
        problem=problem,
        change_to_implement=change_to_implement,
        suggested_actions=suggested_actions,
    )

    if verdict == "incorrect":
        if should_ignore_variation_only_review(
            payload=payload,
            raw_suggested_actions=raw_suggested_actions,
            suggested_actions=suggested_actions,
        ) or should_ignore_surface_translation_review(
            payload=payload,
            raw_suggested_actions=raw_suggested_actions,
            suggested_actions=suggested_actions,
            problem=problem,
            change_to_implement=change_to_implement,
        ) or should_ignore_morphology_supported_move_review(
            payload=payload,
            raw_suggested_actions=raw_suggested_actions,
            suggested_actions=suggested_actions,
        ) or should_ignore_gloss_hint_translation_review(
            payload=payload,
            raw_suggested_actions=raw_suggested_actions,
            suggested_actions=suggested_actions,
        ) or should_suppress_gloss_only_feedback(
            problem=problem,
            change_to_implement=change_to_implement,
            suggested_actions=suggested_actions,
        ):
            return WordVerificationResult(
                verdict="verified",
                message="OK",
                composed_word_count=word_count,
            )
        return WordVerificationResult(
            verdict="flagged",
            message="Review needed",
            composed_word_count=word_count,
            problem=problem or "Entry placement is inconsistent.",
            change_to_implement=(
                change_to_implement
                or "Apply the matching structured fix."
            ),
            suggested_actions=suggested_actions,
        )
    if force_translation_fix:
        return WordVerificationResult(
            verdict="flagged",
            message="Review needed",
            composed_word_count=word_count,
            problem=problem or TRANSLATION_FIX_PROBLEM,
            change_to_implement=change_to_implement or TRANSLATION_FIX_CHANGE,
            suggested_actions=suggested_actions,
        )
    return WordVerificationResult(
        verdict="verified",
        message="OK",
        composed_word_count=word_count,
    )
```

Then update `verify_word_entry` to call it:

```python
def verify_word_entry(self, payload: WordVerificationInput) -> WordVerificationResult:
    prompt = self._verification_prompt(payload)
    raw = self._generate_text(prompt)
    if not raw:
        return WordVerificationResult(
            verdict="flagged",
            message="Review needed",
            composed_word_count=self._infer_word_count(payload),
            problem="Could not verify the entry.",
            change_to_implement="Retry verification.",
        )
    parsed = self._parse_response(raw)
    return self._process_single_verdict(payload, parsed)
```

- [ ] **Step 5: Run existing tests — verify refactor didn't break anything**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_verification_service_unit.py -v`
Expected: ALL PASS (existing tests still work with refactored method)

- [ ] **Step 6: Implement `verify_word_entries_batch`**

Add to `GeminiWordVerificationService`:

```python
def verify_word_entries_batch(
    self,
    payloads: list[WordVerificationInput],
    sentence_context: str | None = None,
) -> list[WordVerificationResult]:
    if not payloads:
        return []
    entries = [
        {"word_id": index, **self._verification_context(payload)}
        for index, payload in enumerate(payloads)
    ]
    prompt = self._batch_verification_prompt(entries, sentence_context)
    raw = self._generate_content(prompt)
    text = getattr(raw, "text", None)
    cleaned = text.strip() if isinstance(text, str) else ""
    if not cleaned:
        return [self._batch_fallback(payload) for payload in payloads]

    parsed = self._parse_batch_response(cleaned, len(payloads))
    results: list[WordVerificationResult] = []
    for payload, word_parsed in zip(payloads, parsed, strict=False):
        if word_parsed is None:
            results.append(self._batch_fallback(payload))
        else:
            results.append(self._process_single_verdict(payload, word_parsed))
    return results


def _batch_verification_prompt(
    self,
    entries: list[dict[str, object]],
    sentence_context: str | None = None,
) -> str:
    from app.services.verification_prompt_templates import build_batch_verification_prompt
    return build_batch_verification_prompt(entries=entries, sentence_context=sentence_context)


def _parse_batch_response(
    self,
    raw: str,
    expected_count: int,
) -> list[dict[str, object] | None]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    try:
        parsed = json.loads(cleaned)
    except ValueError:
        return [None] * expected_count
    if not isinstance(parsed, dict):
        return [None] * expected_count
    raw_results = parsed.get("results")
    if not isinstance(raw_results, list):
        return [None] * expected_count
    by_id: dict[int, dict[str, object]] = {}
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        word_id = item.get("word_id")
        if isinstance(word_id, int):
            by_id[word_id] = item
    return [by_id.get(i) for i in range(expected_count)]


def _batch_fallback(self, payload: WordVerificationInput) -> WordVerificationResult:
    return WordVerificationResult(
        verdict="flagged",
        message="Review needed",
        composed_word_count=self._infer_word_count(payload),
        problem="Batch verification failed for this entry.",
        change_to_implement="Retry verification.",
    )
```

Also add the import for `build_batch_verification_prompt` at the top of the file (inside the method to avoid circular imports at module level — same pattern as existing `build_word_verification_prompt` import).

- [ ] **Step 7: Run batch test — verify it passes**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_verification_service_unit.py::test_gemini_batch_verification_returns_per_word_results -v`
Expected: PASS

- [ ] **Step 8: Write failing test — batch applies same post-processing per word**

```python
def test_gemini_batch_verification_applies_post_processing_per_word(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_content",
        lambda prompt, config: type("R", (), {
            "text": (
                '{"results":['
                '{"word_id":0,"verdict":"incorrect","word_count":1,"problem":"The gloss is wrong.","change_to_implement":"fix gloss","suggested_actions":[]},'
                '{"word_id":1,"verdict":"incorrect","word_count":1,"problem":"translation mismatch","change_to_implement":"set translation",'
                '"suggested_actions":[{"action_type":"fix_translation","english_translation":"mother","reason":"use the noun translation"}]}'
                ']}'
            ),
        })(),
    )

    results = service.verify_word_entries_batch([_payload(), _mor_payload()], sentence_context="test")

    assert results[0].verdict == "verified"  # gloss-only review suppressed
    assert results[0].suggested_actions == ()
    assert results[1].verdict == "flagged"  # translation fix allowed
    assert [a.action_type for a in results[1].suggested_actions] == ["fix_translation"]
```

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_verification_service_unit.py::test_gemini_batch_verification_applies_post_processing_per_word -v`
Expected: PASS (if post-processing is correctly applied)

- [ ] **Step 9: Write failing test — empty payloads returns empty**

```python
def test_gemini_batch_verification_empty_payloads():
    service = GeminiWordVerificationService(api_key="test-key")
    assert service.verify_word_entries_batch([]) == []
```

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_verification_service_unit.py::test_gemini_batch_verification_empty_payloads -v`
Expected: PASS

- [ ] **Step 10: Run all verification tests**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_verification_service_unit.py -v`
Expected: ALL PASS

- [ ] **Step 11: Commit**

```bash
git add backend/app/services/verification.py backend/tests/services/test_verification_service_unit.py
git commit -m "feat: add verify_word_entries_batch to verification service"
```

---

### Task 3: Batch verification collaborator

**Files:**
- Modify: `backend/app/services/use_cases/wordbank/collaborators/verification.py`

- [ ] **Step 1: Write failing test — collaborator has batch method**

```python
# Add to test_verification_service_unit.py (or new collaborator test file)
def test_verification_collaborator_has_batch_method():
    from app.services.use_cases.wordbank.collaborators.verification import VerificationCollaborator
    assert hasattr(VerificationCollaborator, "verify_word_entries_batch")
```

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_verification_service_unit.py::test_verification_collaborator_has_batch_method -v`
Expected: FAIL — `AttributeError`

- [ ] **Step 2: Add `verify_word_entries_batch` to `VerificationCollaborator`**

Add to `backend/app/services/use_cases/wordbank/collaborators/verification.py`:

```python
def verify_word_entries_batch(
    self,
    verification_inputs: list[WordVerificationInput],
    sentence_context: str | None = None,
) -> list[VerificationResult]:
    """Verify multiple words in a single Gemini call. Returns per-word results."""
    if self._verification_service is None:
        return [self._skipped_verification_result(payload) for payload in verification_inputs]

    provider_name, reviewer_name = self._verification_metadata()
    try:
        verdicts = self._verification_service.verify_word_entries_batch(
            verification_inputs, sentence_context=sentence_context,
        )
    except Exception as exc:
        logger.warning(
            "wordbank_batch_verification_failed",
            extra={"error": str(exc), "word_count": len(verification_inputs)},
        )
        return [self._error_verification_result(payload, exc, provider_name, reviewer_name)
                for payload in verification_inputs]

    completed_at = now_utc_iso()
    results: list[VerificationResult] = []
    for payload, verdict in zip(verification_inputs, verdicts, strict=False):
        result = self._build_batch_verification_result(
            verdict, payload, provider_name, reviewer_name, completed_at,
        )
        self._persist_batch_result(payload, result)
        results.append(result)

    # Auto-apply eligible actions for all results
    for payload, result in zip(verification_inputs, results, strict=False):
        if result.status in ("verified", "flagged"):
            self._auto_apply_eligible_actions(
                stored_lemma=payload.stored_lemma,
                stored_surface_form=payload.stored_surface_form,
                meaning_id=payload.meaning_id,
            )
    return results


def _skipped_verification_result(self, payload: WordVerificationInput) -> VerificationResult:
    return VerificationResult(
        status="skipped",
        provider=None,
        reviewer_role=None,
        review_intent=payload.review_intent,
        message="Verification disabled.",
    )


def _error_verification_result(
    self,
    payload: WordVerificationInput,
    exc: Exception,
    provider_name: str,
    reviewer_name: str | None,
) -> VerificationResult:
    return VerificationResult(
        status="error",
        provider=provider_name,
        reviewer_role=reviewer_name,
        review_intent=payload.review_intent,
        message="Verification failed",
        composed_word_count=None,
        stored_surface_form=payload.stored_surface_form,
        requested_at=now_utc_iso(),
        completed_at=now_utc_iso(),
        problem=str(exc),
        change_to_implement="Retry verification.",
        suggested_actions=[],
    )


def _build_batch_verification_result(
    self,
    verdict: WordVerificationResult,
    payload: WordVerificationInput,
    provider_name: str,
    reviewer_name: str | None,
    completed_at: str,
) -> VerificationResult:
    suggested_actions = [
        verification_action_to_schema(action)
        for action in getattr(verdict, "suggested_actions", ()) or ()
    ]
    return VerificationResult(
        status=verdict.verdict,
        provider=provider_name,
        reviewer_role=reviewer_name,
        review_intent=payload.review_intent,
        message=verdict.message,
        composed_word_count=getattr(verdict, "composed_word_count", None),
        stored_surface_form=payload.stored_surface_form,
        requested_at=completed_at,
        completed_at=completed_at,
        problem=getattr(verdict, "problem", None),
        change_to_implement=getattr(verdict, "change_to_implement", None),
        suggested_actions=suggested_actions,
    )


def _persist_batch_result(
    self,
    payload: WordVerificationInput,
    result: VerificationResult,
) -> None:
    repository = WordbankRepository(self._db_path)
    lexeme = repository.get_lexeme(payload.stored_lemma)
    if lexeme is None:
        return
    record = repository.get_verification_record(
        lexeme_id=lexeme.id,
        meaning_id=payload.meaning_id,
        stored_surface_form=payload.stored_surface_form,
    )
    requested_at = record.requested_at if record is not None else result.requested_at
    persisted = result.model_copy(
        update={
            "requested_at": requested_at or now_utc_iso(),
            "completed_at": result.completed_at,
        }
    )
    persist_verification_result(
        repository,
        lexeme_id=lexeme.id,
        meaning_id=payload.meaning_id,
        stored_surface_form=payload.stored_surface_form,
        verification=persisted,
        requested_at=requested_at,
    )
```

- [ ] **Step 3: Run all verification tests — verify no breakage**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_verification_service_unit.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/use_cases/wordbank/collaborators/verification.py backend/tests/services/test_verification_service_unit.py
git commit -m "feat: add batch verification to VerificationCollaborator"
```

---

### Task 4: Sentencebank batch verification integration

**Files:**
- Modify: `backend/app/services/use_cases/sentencebank.py`
- Modify: `backend/tests/use_cases/test_sentencebank_use_case.py`

- [ ] **Step 1: Write failing test — sentence add calls batch verification**

```python
# Add to test_sentencebank_use_case.py

class FakeVerificationService:
    provider = "fake_verification"
    reviewer_role = "Fake Reviewer"
    batch_calls = []

    def verify_word_entry(self, payload):
        return WordVerificationResult(
            verdict="verified", message="OK", composed_word_count=1,
        )

    def verify_word_entries_batch(self, payloads, sentence_context=None):
        self.batch_calls.append((payloads, sentence_context))
        return [
            WordVerificationResult(verdict="verified", message="OK", composed_word_count=1)
            for _ in payloads
        ]

    def classify_word_categories(self, payload):
        return WordCategoryClassificationResult(categories=())


def test_sentencebank_add_sentence_triggers_batch_verification(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "Huset er stort": [
                NLPToken(text="Huset", lemma="hus", pos="NOUN", morphology="Gender=Neut|Number=Sing|Definite=Def", is_punctuation=False),
                NLPToken(text="er", lemma="være", pos="AUX", morphology="Tense=Pres|VerbForm=Fin", is_punctuation=False),
                NLPToken(text="stort", lemma="stor", pos="ADJ", morphology="Degree=Pos|Gender=Neut|Number=Sing|Definite=Ind", is_punctuation=False),
            ],
        }
    )
    translation_service = FakeTranslationService({"Huset er stort": "the house is big", "hus": "house", "være": "be", "stor": "big"})
    verification_service = FakeVerificationService()
    wordbank_use_case = WordbankUseCase(
        db_path,
        translation_service=translation_service,
        nlp_adapter=nlp_adapter,
        verification_service=verification_service,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        translation_service=translation_service,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence("Huset er stort")

    assert inserted.status == "inserted"
    assert len(verification_service.batch_calls) == 1
    batch_payloads, batch_context = verification_service.batch_calls[0]
    assert batch_context == "Huset er stort"
    assert len(batch_payloads) >= 1  # at least newly added words
```

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/use_cases/test_sentencebank_use_case.py::test_sentencebank_add_sentence_triggers_batch_verification -v`
Expected: FAIL — batch not called

- [ ] **Step 2: Modify `_resolve_sentence_tokens` to track new tokens**

Change the return type to include metadata about which tokens are new. In `backend/app/services/use_cases/sentencebank.py`:

```python
def _resolve_sentence_tokens(self, source_text: str) -> tuple[list[SentenceTokenWriteRecord], list[dict[str, object]]]:
    """Returns (token_records, new_token_metadata).

    new_token_metadata contains dicts with keys: stored_lemma, stored_surface_form, meaning_id
    for tokens that were newly persisted (not already existing in wordbank).
    """
    if self._nlp_adapter is None or self._wordbank_use_case is None:
        return [], []
    runtime = self._wordbank_use_case.runtime
    resolved: list[SentenceTokenWriteRecord] = []
    new_tokens: list[dict[str, object]] = []
    for nlp_token in self._nlp_adapter.tokenize(source_text):
        surface_form = nlp_token.text.strip()
        if not surface_form or nlp_token.is_punctuation:
            continue
        if not is_wordlike_token(surface_form):
            continue
        normalized_surface = normalize_token(surface_form)
        if not normalized_surface:
            continue
        lemma_candidate = normalize_token(nlp_token.lemma or "") or normalized_surface
        token, is_new = self._resolve_sentence_token(
            runtime,
            token_index=len(resolved),
            display_surface=surface_form,
            normalized_surface=normalized_surface,
            lemma_candidate=lemma_candidate,
            pos_tag=nlp_token.pos,
            morphology=nlp_token.morphology,
            sentence_context=source_text,
        )
        resolved.append(token)
        if is_new:
            new_tokens.append({
                "stored_lemma": token.stored_lemma,
                "stored_surface_form": token.normalized_surface,
                "meaning_id": token.meaning_id,
            })
    return resolved, new_tokens
```

- [ ] **Step 3: Update `_resolve_sentence_token` to return is_new flag**

```python
def _resolve_sentence_token(
    self,
    runtime: WordbankRuntime,
    *,
    token_index: int,
    display_surface: str,
    normalized_surface: str,
    lemma_candidate: str,
    pos_tag: str | None,
    morphology: str | None,
    sentence_context: str,
) -> tuple[SentenceTokenWriteRecord, bool]:
    existing = _existing_saved_token(
        runtime,
        display_surface=display_surface,
        normalized_surface=normalized_surface,
        lemma_candidate=lemma_candidate,
        token_index=token_index,
    )
    if existing is not None:
        return existing, False

    selected_candidate = _select_sentence_candidate(
        runtime,
        surface_form=normalized_surface,
        lemma_candidate=lemma_candidate,
        pos_tag=pos_tag,
        morphology=morphology,
        sentence_context=sentence_context,
    )
    if selected_candidate is None:
        return _save_root_level_sentence_token(
            runtime,
            token_index=token_index,
            display_surface=display_surface,
            normalized_surface=normalized_surface,
            lemma=lemma_candidate,
            pos_tag=pos_tag,
            morphology=morphology,
            cor_id=None,
            gloss=None,
            english_translation=None,
            gloss_translation=None,
        ), True

    persisted_response = _persist_candidate_to_wordbank(
        self._wordbank_use_case,
        normalized_surface=normalized_surface,
        candidate=selected_candidate,
    )
    if persisted_response is not None:
        persisted = _sentence_token_from_saved_word(
            runtime,
            token_index=token_index,
            display_surface=display_surface,
            normalized_surface=normalized_surface,
            stored_lemma=selected_candidate.lemma,
            meaning_id=(
                persisted_response.meaning.id
                if persisted_response.meaning is not None
                else None
            ),
        )
        if persisted is not None:
            return persisted, True

    return _save_root_level_sentence_token(
        runtime,
        token_index=token_index,
        display_surface=display_surface,
        normalized_surface=normalized_surface,
        lemma=selected_candidate.lemma,
        pos_tag=selected_candidate.pos_tag or pos_tag,
        morphology=selected_candidate.morphology or morphology,
        cor_id=selected_candidate.cor_id,
        gloss=selected_candidate.gloss,
        english_translation=selected_candidate.english_translation,
        gloss_translation=selected_candidate.gloss_translation,
    ), True
```

- [ ] **Step 4: Update `add_sentence` to use new return type and call batch verification**

```python
def add_sentence(self, source_text: str) -> AddSentenceResponse:
    normalized_source_text = _normalize_sentence_text(source_text)
    normalized_key = normalize_token(source_text)
    if not normalized_source_text or not normalized_key:
        raise ValueError("source_text is required")

    existing = self._repository.find_by_normalized_sentence(normalized_key)
    if existing is not None:
        return _sentence_response(
            existing,
            status="exists",
            message=f'"{existing.source_text}" is already in sentencebank.',
        )

    english_translation = self._lookup_phrase_translation(normalized_source_text)
    provider = self._translation_provider_name()
    sentence_id = self._repository.insert_sentence(
        source_text=normalized_source_text,
        normalized_sentence=normalized_key,
        english_translation=english_translation,
        translation_provider=provider if english_translation else None,
    )
    token_records, new_token_metadata = self._resolve_sentence_tokens(normalized_source_text)
    self._repository.replace_sentence_tokens(sentence_id=sentence_id, tokens=token_records)
    if new_token_metadata and self._wordbank_use_case is not None:
        _batch_verify_new_sentence_tokens(
            self._wordbank_use_case.runtime,
            new_token_metadata=new_token_metadata,
            sentence_context=normalized_source_text,
        )
    saved = self._repository.find_by_normalized_sentence(normalized_key)
    if saved is None:
        raise RuntimeError("Sentence was saved but could not be reloaded.")
    return _sentence_response(
        saved,
        status="inserted",
        message=f'Added "{normalized_source_text}" to sentencebank.',
    )
```

- [ ] **Step 5: Add `_batch_verify_new_sentence_tokens` function**

```python
def _batch_verify_new_sentence_tokens(
    runtime: WordbankRuntime,
    *,
    new_token_metadata: list[dict[str, object]],
    sentence_context: str,
) -> None:
    """Batch-verify newly persisted sentence tokens via single Gemini call."""
    try:
        verification_inputs = [
            _build_verification_input(runtime, meta)
            for meta in new_token_metadata
        ]
        valid_inputs = [inp for inp in verification_inputs if inp is not None]
        if not valid_inputs:
            return
        runtime.verification.verify_word_entries_batch(
            valid_inputs, sentence_context=sentence_context,
        )
    except Exception:
        pass  # fallback: individual queue already happened during token resolution


def _build_verification_input(
    runtime: WordbankRuntime,
    meta: dict[str, object],
) -> WordVerificationInput | None:
    from app.services.use_cases.wordbank.verification_input_builder import build_verification_input

    stored_lemma = str(meta.get("stored_lemma", ""))
    stored_surface_form = meta.get("stored_surface_form")
    meaning_id = meta.get("meaning_id")
    if not stored_lemma:
        return None
    return build_verification_input(
        db_path=runtime.verification._db_path,
        nlp=runtime.nlp,
        cor=runtime.cor,
        stored_lemma=stored_lemma,
        stored_surface_form=str(stored_surface_form) if stored_surface_form else None,
        meaning_id=int(meaning_id) if isinstance(meaning_id, int) and meaning_id else None,
    )
```

Add the import at the top of `sentencebank.py`:

```python
from app.services.verification import WordVerificationInput
```

- [ ] **Step 6: Run all sentencebank tests**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/use_cases/test_sentencebank_use_case.py -v`
Expected: ALL PASS (existing tests pass, new batch test passes)

- [ ] **Step 7: Write failing test — fallback when batch fails**

```python
def test_sentencebank_add_sentence_falls_back_on_batch_failure(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    nlp_adapter = MappingNLPAdapter(
        {
            "Huset er stort": [
                NLPToken(text="Huset", lemma="hus", pos="NOUN", morphology="Gender=Neut|Number=Sing|Definite=Def", is_punctuation=False),
                NLPToken(text="er", lemma="være", pos="AUX", morphology="Tense=Pres|VerbForm=Fin", is_punctuation=False),
                NLPToken(text="stort", lemma="stor", pos="ADJ", morphology="Degree=Pos|Gender=Neut|Number=Sing|Definite=Ind", is_punctuation=False),
            ],
        }
    )
    translation_service = FakeTranslationService({"Huset er stort": "the house is big"})

    class FailingBatchVerificationService:
        provider = "fake"
        reviewer_role = "Fake"
        batch_called = False

        def verify_word_entry(self, payload):
            return WordVerificationResult(verdict="verified", message="OK", composed_word_count=1)

        def verify_word_entries_batch(self, payloads, sentence_context=None):
            self.batch_called = True
            raise RuntimeError("Gemini overloaded")

        def classify_word_categories(self, payload):
            return WordCategoryClassificationResult(categories=())

    verification_service = FailingBatchVerificationService()
    wordbank_use_case = WordbankUseCase(
        db_path,
        translation_service=translation_service,
        nlp_adapter=nlp_adapter,
        verification_service=verification_service,
    )
    sentencebank_use_case = SentencebankUseCase(
        db_path,
        translation_service=translation_service,
        nlp_adapter=nlp_adapter,
        wordbank_use_case=wordbank_use_case,
    )

    inserted = sentencebank_use_case.add_sentence("Huset er stort")

    assert inserted.status == "inserted"
    assert verification_service.batch_called
```

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/use_cases/test_sentencebank_use_case.py::test_sentencebank_add_sentence_falls_back_on_batch_failure -v`
Expected: PASS (exception caught, sentence still inserted)

- [ ] **Step 8: Run full test suite**

Run: `cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/use_cases/test_sentencebank_use_case.py tests/services/test_verification_service_unit.py tests/services/test_verification_prompt_templates_batch.py -v`
Expected: ALL PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/use_cases/sentencebank.py backend/tests/use_cases/test_sentencebank_use_case.py
git commit -m "feat: integrate batch verification into sentencebank add_sentence"
```

---

### Task 5: Docs + verification

- [ ] **Step 1: Run lint**

Run: `make lint`
Expected: PASS

- [ ] **Step 2: Run full test suite**

Run: `make test`
Expected: PASS

- [ ] **Step 3: Commit docs if any updates needed**

If docs pass without changes: no commit needed.
If `docs/contracts/api-contract.md` or `README.md` need updates: commit them.

---

### Self-Review Checklist

- [ ] Spec coverage: batch prompt builder (Task 1), protocol+service (Task 2), collaborator (Task 3), sentencebank integration (Task 4), docs (Task 5)
- [ ] Placeholder scan: no TBDs, no "implement later", no "similar to Task N"
- [ ] Type consistency: `verify_word_entries_batch` signature same across protocol, service, collaborator
- [ ] `_process_single_verdict` extracted correctly — same behavior as original `verify_word_entry`
- [ ] Batch fallback on failure — graceful degradation
- [ ] No circular imports in `sentencebank.py` (import inside function)
