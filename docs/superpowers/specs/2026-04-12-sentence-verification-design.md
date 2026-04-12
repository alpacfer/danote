# Sentence Verification in Search — Design

**Date:** 2026-04-12  
**Status:** Approved

## Summary

When the sidebar search enters sentence mode (user types 2+ words), automatically verify the Danish sentence for typos and grammatical errors using Gemini before allowing it to be saved to the sentencebank. Show errors inline with underlines and the corrected sentence. Save the corrected version.

## Scope

Only the sidebar search sentence mode (`use-sidebar-search.ts` + `SidebarSentenceResult`). No changes to the Playground phrase popover or any other save path.

---

## Backend

### New service: `backend/app/services/sentence_verification.py`

```python
@dataclass
class SentenceVerificationError:
    start: int       # char offset in source_text (inclusive)
    end: int         # char offset in source_text (exclusive)
    message: str     # human-readable description

@dataclass
class SentenceVerificationResult:
    is_valid: bool
    errors: list[SentenceVerificationError]
    corrected_text: str | None   # None when is_valid=True
    language: Literal["da", "en", "unknown"]
```

Single Gemini call with a focused JSON prompt:

> Given this text: `"<source_text>"`, respond with JSON only:
> `{ "is_valid": bool, "errors": [{"start": int, "end": int, "message": str}], "corrected_text": str|null, "language": "da"|"en"|"unknown" }`
> Check for typos and grammatical errors in Danish. `corrected_text` is null when `is_valid` is true.

### New schemas: `backend/app/api/schemas/v1/sentencebank.py`

```python
class SentenceVerificationErrorItem(BaseModel):
    start: int
    end: int
    message: str

class VerifySentenceRequest(BaseModel):
    source_text: str = Field(..., min_length=1, max_length=50)

class VerifySentenceResponse(BaseModel):
    is_valid: bool
    errors: list[SentenceVerificationErrorItem]
    corrected_text: str | None
    language: Literal["da", "en", "unknown"]
```

### New route: `POST /api/sentencebank/verify-sentence`

Added to `backend/app/api/routes/sentencebank.py`. Thin handler: validates input via schema, calls use-case, maps `ValueError` → 400. No business logic in route.

---

## Frontend

### `use-sidebar-search.ts`

**50-char limit:** `isSentenceMode` only activates when `trimmedQuery.length <= 50`. Above 50 chars, stays in single-word mode (no sentence result shown).

**New state:**
```ts
sentenceVerification: { query: string; result: VerifySentenceResponse } | null
isSentenceVerificationLoading: boolean
sentenceVerificationError: string | null
```

**Cache:** `sentenceVerificationCacheRef: Map<string, VerifySentenceResponse>` keyed by normalized query. Same text → skip Gemini, return cached result immediately.

**Debounced effect:** fires ~600ms after user stops typing (longer than `SEARCH_RESOLVE_DEBOUNCE_MS` = 220ms). Only runs when `isSentenceMode && sentenceQuery.length <= 50`. Resets on query change. Clears when exiting sentence mode. Verification requests use whitespace-normalized text with the user's capitalization preserved.

### `SidebarSentenceResult`

**New props:**
```ts
sentenceVerification: VerifySentenceResponse | null
isSentenceVerificationLoading: boolean
```

**Error display:** source text rendered as inline spans — clean text between errors, error spans wrapped in `<span>` with `underline decoration-red-500 decoration-wavy`. Corrected sentence shown below in muted style with a small label when `!is_valid`.

**Save gate:** `+` button disabled while `isSentenceVerificationLoading || !sentenceVerification`.

**Save action:** passes `sentenceVerification.corrected_text ?? sourceText` to `onSaveSentence`.

---

## Data flow

```
User types "jeg er glat" (≤50 chars, 2+ words)
  → isSentenceMode = true
  → translation debounce (220ms) → POST /api/wordbank/phrase-translation  [existing]
  → verification debounce (600ms) → POST /api/sentencebank/verify-sentence [new]
      Gemini returns: { is_valid: false, errors: [{start:7,end:11,message:"typo"}],
                        corrected_text: "Jeg er glad", language: "da" }
  → SidebarSentenceResult shows:
      "jeg er [glat]"  ← red wavy underline on "glat"
      Corrected: "Jeg er glad"
      [+] button enabled
  → User clicks [+] → saves "Jeg er glad"
```

For valid sentences (`is_valid: true`), no underlines, corrected_text is null, saves original text.

---

## Caching / "smart" triggering

- Same normalized query within a session → instant result from cache, no Gemini call
- Query changes → previous verification cleared, new debounce starts
- Exit sentence mode → cache retained, state cleared
- 50-char cap ensures Gemini only sees short sentences, not paragraphs

---

## Files touched

| File | Change |
|------|--------|
| `backend/app/services/sentence_verification.py` | New — Gemini sentence check service |
| `backend/app/api/schemas/v1/sentencebank.py` | Add `VerifySentenceRequest`, `VerifySentenceResponse`, `SentenceVerificationErrorItem` |
| `backend/app/api/routes/sentencebank.py` | Add `POST /api/sentencebank/verify-sentence` route |
| `backend/app/services/use_cases/sentencebank.py` | Add `verify_sentence` method wiring service |
| `docs/contracts/api-contract.md` | Add new endpoint |
| `frontend/src/app/chrome/sidebar/use-sidebar-search.ts` | 50-char limit, verification state + debounce, cache |
| `frontend/src/app/chrome/sidebar/sidebar-sentence-result.tsx` | Error underlines, corrected text, save gate |
| `frontend/src/app/chrome/sidebar/sidebar-search-results.tsx` | Pass verification props |
| `frontend/src/app/chrome/sidebar/app-sidebar.tsx` | Pass verification props if needed |

---

## Out of scope

- Playground phrase popover (no changes)
- Verification of sentences already saved (retroactive)
- Showing language detection in the UI (stored in response, available for future use)
