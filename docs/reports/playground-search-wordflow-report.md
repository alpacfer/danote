# Playground & Search Word Analysis Flow Report

## Scope

This report analyzes the current end-to-end flow for **analyzing and categorizing words** in:

- Playground (`/api/analyze` + token actions)
- Sidebar Search (`/api/wordbank/resolve-query` + add actions)

It focuses on architecture, UX behavior, consistency between paths, and opportunities to improve efficiency.

## Executive Summary

The implementation is already quite strong in core architecture:

- Route handlers are thin and delegate orchestration into use-cases.
- Both Playground and Search depend on the same classification engine (`LemmaAwareClassifier`).
- There is an explicit unit test guarding consistency of action payloads across `resolve_query` and `analyze`.

However, there are some opportunities:

1. **Search makes resolve-query calls too aggressively** (every query change, no debounce).
2. **Fallback action-building in frontend duplicates backend logic**, creating drift risk.
3. **Playground and Search do not expose equivalent enrichment signals** (translations/language detection available in Search but not in Playground analysis payload).
4. **Per-token classification still performs multiple DB lookups per token** and can be optimized via batch prefetching/caching for long notes.
5. **Minor flow inconsistency**: Playground strips inline `#` comments before analysis, Search query does not have equivalent preprocessing semantics.

## Current Flow: Playground

### Trigger & request behavior

- Playground analysis is debounced and abortable in the frontend effect (`ANALYZE_DEBOUNCE_MS`, abort controller, latest-request-wins guard).
- Request: `POST /api/analyze` with `{ text }`.

### Backend pipeline

1. Route verifies DB and NLP readiness.
2. Creates `AnalyzeNoteUseCase`.
3. Use-case strips inline comments (`# ...`) from note lines.
4. Tokenization filters punctuation/non-wordlike tokens.
5. `LemmaAwareClassifier.classify_many(...)` performs classification.
6. Response token includes class, match info, typo suggestions/confidence/reason tags, POS/morphology, and `word_actions` suggestions.

### Classification behavior

Classifier logic for each token:

- Exact surface-form DB match => `known`
- Exact lemma DB match => `known`
- Otherwise use NLP lemma candidates and lexicon matching => `variation` if candidate lemma exists
- Otherwise typo-engine fallback => `typo_likely` / `uncertain` / `new`

## Current Flow: Search

### Trigger & request behavior

- Search dialog normalizes input and performs local matching against loaded lemma and note lists.
- For single-token queries without whitespace and no direct exact lemma match, frontend calls:
  - `POST /api/wordbank/resolve-query` with `{ query_text }`.
- No debounce is currently applied to this network call.

### Backend resolve behavior

`resolve_query(...)` performs:

1. Query normalization.
2. Classification with `LemmaAwareClassifier.classify(...)`.
3. POS/morphology extraction via NLP adapter.
4. Optional DA->EN and EN->DA translation lookups.
5. Optional language detection heuristic/service.
6. "resolved" surface/lemma override for likely-English unknown words translated to Danish.
7. Server-side `word_actions` construction via `build_word_action_suggestions(...)`.

### Search action rendering

- Frontend stores resolved candidate data and shows:
  - matched wordbank lemma
  - add-as-new options (including direction labels)
  - add-variation when relevant
- Frontend still contains a fallback action generator (`fallbackWordActionsFromResolve`) if backend returns no actions.

## Inconsistencies & Drift Risks

### 1) Duplicate action decision logic (backend + frontend fallback)

Even though backend now returns `word_actions`, frontend maintains `fallbackWordActionsFromResolve(...)` with overlapping decision logic.

**Risk**: if backend rules evolve, fallback may diverge from server truth and produce inconsistent Search options.

**Recommendation**:

- Make backend `word_actions` canonical.
- Narrow frontend fallback to only a minimal emergency default (or remove it).
- Add one integration test in frontend that asserts action rendering for representative backend payloads.

### 2) Uneven enrichment between Playground and Search

Search uses resolve-query and can surface translations/language context to construct richer add flows (e.g., English query -> Danish candidate).
Playground analysis returns action suggestions but currently with translation/language fields effectively omitted.

**Impact**: users may see richer decision options in Search than in Playground for semantically similar words.

**Recommendation**:

- Option A (preferred): keep Playground lightweight but add an on-demand "enrich token" endpoint when opening token popover.
- Option B: include optional enrichment flags on `/api/analyze` for parity, off by default.

### 3) Preprocessing semantics mismatch

Playground strips inline `#` comments before analysis; Search resolves raw query text directly.

**Impact**: token interpretation differs subtly by entry point.

**Recommendation**:

- Either document this clearly as intentional,
- or centralize normalization/preprocessing policy for all word-entry points.

## Efficiency Findings

### 1) Search resolve-query call frequency

Search resolve is triggered on query changes (single-token path) without debounce.

**Observed downside**:

- extra backend calls while typing rapidly
- repeated classification/translation/language work for intermediate query states

**Recommendation**:

- Add a 150–300ms debounce to resolve-query.
- Keep abort-controller cancellation behavior.
- Optional: cache recent query results (`Map<query, payload>`) for session lifetime.

### 2) Repeated DB lookups per token classification

`LemmaAwareClassifier._classify_with_connection(...)` performs multiple SQL queries per token (exact surface form, exact lemma, candidate IN lookup).

**Observed downside** (for long notes):

- many round-trips to SQLite within one analysis request

**Recommendation**:

- In `classify_many`, batch prefetch known surfaces and known lemmas for the token set.
- Reuse an in-request cache mapping normalized token -> classification decision.

### 3) Resolve-query can invoke expensive optional operations by default

Translations + language detection are enabled by default. This is valuable, but for fast interactive search it can add latency.

**Recommendation**:

- Keep default behavior for UX quality, but add lightweight fast-path:
  - first call with `include_translations=false` and `include_language_detection=false`
  - enrich asynchronously only if needed for action disambiguation.

## Positive Design Choices Already Present

- Thin route handlers and use-case orchestration are clean and maintainable.
- Search and Playground share the same classifier core, reducing conceptual drift.
- There is already a test asserting action payload consistency between resolve-query and analyze.
- Frontend analysis pipeline uses debounce + abort + stale-response guards (good resilience).

## Prioritized Improvement Plan

### P1 (High impact / low-to-medium risk)

1. Add debounce + short-lived cache to Search resolve-query.
2. Reduce/remove frontend fallback action logic and trust backend `word_actions`.
3. Add frontend regression tests for search action rendering from backend payload fixtures.

### P2 (Medium impact / medium risk)

4. Add batch lookup optimization in `classify_many` for large note analysis.
5. Introduce optional "enrichment" API for Playground token actions to close UX parity gap.

### P3 (Clarity)

6. Document preprocessing policy differences (or unify behavior).

## Suggested KPIs to validate improvements

- Median and p95 latency for `POST /api/wordbank/resolve-query` while typing.
- Number of resolve-query calls per 10 seconds of active typing.
- Median and p95 latency for `POST /api/analyze` for short/medium/long notes.
- Action consistency incidents between Search and Playground (should trend to zero).

