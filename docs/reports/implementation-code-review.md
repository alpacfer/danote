# Implementation code review

## Overall assessment

The current implementation is a solid improvement over the previous per-token database lookup pattern. In particular, `classify_many()` now batches exact surface lookups and lemma-candidate lookups once per request, which should reduce repeated SQL traffic for medium/large notes. The use-case layer also remains thin and delegates classification logic to `LemmaAwareClassifier`, which matches the repository architecture policy.

## What is working well

1. **Batch prefetch for exact and lemma matching**
   - `classify_many()` precomputes normalized inputs, exact matches, and lemma-candidate lexeme availability before iterating token-by-token.
   - This is a meaningful performance-oriented design for the analyze pipeline.

2. **Deterministic token filtering before classification**
   - `AnalyzeNoteUseCase.execute()` filters empty/whitespace, punctuation, and non-wordlike tokens before classifier dispatch, keeping downstream logic focused and predictable.

3. **Backwards-compatible classifier alias retained**
   - Keeping `ExactLookupClassifier = LemmaAwareClassifier` avoids breaking external imports from previous checkpoints.

## Improvement opportunities

1. **Guard against SQLite placeholder limits for large inputs**
   - `_prefetch_exact_matches()` and `_prefetch_lemma_candidates()` build `IN (?, ?, ...)` clauses from full token/candidate sets.
   - SQLite has parameter limits (commonly 999). Very long notes or large lemma-candidate expansions can exceed this and raise `OperationalError`.
   - Suggested fix: chunk identifiers into bounded batches (for example 300-500 items), query each batch, and merge results.

2. **Resolve ambiguous surface-form collisions explicitly**
   - `_prefetch_exact_matches()` materializes one dictionary entry per `sf.form` (`row["form"] -> lemma`).
   - If multiple lexemes share the same surface form, the last fetched row wins implicitly.
   - Suggested fix: either add deterministic ordering + explicit tie-breaking, or store all matches per form and choose via ranking logic.

3. **Remove redundant exception pass-through in use case**
   - `AnalyzeNoteUseCase.execute()` wraps token assembly in `try/except sqlite3.OperationalError: raise`.
   - This does not add context or transformation and can be safely removed for readability.
   - Alternatively, if exception handling is intended, add structured context (request size, token count) before re-raising.

4. **Minor micro-optimization/readability for candidate normalization**
   - In `_classify_with_connection()`, candidate normalization is performed twice per candidate in the set comprehension used with prefetched candidates.
   - Suggested fix: normalize once in a small loop to reduce duplicate work and improve readability.

## Suggested next step

Implement improvement (1) first (chunked prefetch), then add a regression test covering a token batch that exceeds the SQLite parameter threshold to prevent future regressions.
