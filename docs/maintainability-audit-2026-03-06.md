# Maintainability audit (non-test code)

Date: 2026-03-06
Scope: application and script code only (test files excluded; vendored UI primitives excluded where already carved out by policy)

## Assessment

Overall maintainability is **improving**, but the repository is still carrying **two backend use-case hotspots above the enforced hard limits**.

The previous top risk, `backend/app/services/use_cases/wordbank/core.py`, has been reduced substantially from the prior audit. That is real progress. The remaining problem is that complexity has shifted into collaborator modules rather than fully disappearing.

## What changed since the 2026-03-05 audit

- `backend/app/services/use_cases/wordbank/core.py` dropped from 2184 lines to 713 lines.
- The wordbank package now has clearer domain grouping under `collaborators/`.
- `frontend/src/components/ui/sidebar.tsx` is no longer the large file from the previous audit; the large implementation now lives in vendored `frontend/src/components/ui/vendor/sidebar.tsx`, which should stay excluded from maintainability enforcement unless the team decides to fork it.
- The maintainability budget script had a false positive: `frontend/src/test/app-test-helpers.tsx` was being scanned as production code. That undermined the audit signal and has now been corrected in `scripts/check-maintainability-budgets.sh`.

## Current highest-impact maintainability risks

### 1) `backend/app/services/use_cases/wordbank/collaborators/cor.py` (785 lines)

Why it is the main risk now:
- It exceeds the backend hard limit enforced by `make maintainability-check`.
- It mixes query resolution, COR lookup orchestration, translation fallback behavior, saved-lemma reconciliation, and action suggestion shaping.
- It is likely to become the default landing place for future "just one more COR rule" changes.

Recommended action:
- Split into focused modules behind the same collaborator API:
  - `cor_query_resolution.py`
  - `cor_local_search.py`
  - `cor_action_suggestions.py`
  - `cor_saved_lemma_lookup.py`

Expected result:
- Smaller blast radius for dictionary/search changes and easier targeted unit coverage.

### 2) `backend/app/services/use_cases/wordbank/core.py` (713 lines)

Why it is still a risk:
- It still exceeds the backend hard limit.
- `WordbankUseCase` remains the composition root plus command/query surface for many workflows.
- The file is much healthier than before, but it is still too large to comfortably evolve.

Recommended action:
- Keep `core.py` as the public facade only.
- Move command/query method bodies into workflow modules and let `WordbankUseCase` delegate.
- Preserve `wordbank/__init__.py` as the stable package surface.

Expected result:
- Cleaner ownership per workflow and lower regression risk when backend endpoints change.

### 3) `backend/app/services/use_cases/wordbank/collaborators/verification.py` (401 lines)

Why it matters:
- It is above the backend soft limit and already combines three concerns: request normalization, DB mutation/application, and Gemini audit logging.
- Verification behavior is policy-heavy and likely to keep growing.

Recommended action:
- Split apply-changes persistence from audit-log emission and payload normalization.
- Keep the collaborator focused on orchestration, not storage details.

Expected result:
- Easier policy changes, clearer failure modes, and tighter unit tests.

## Lower-priority follow-up items

- `backend/app/services/token_classifier.py` (405): still a reasonable extraction target if rule branching grows again.
- `backend/app/api/routes/wordbank.py` (343): currently acceptable, but keep it transport-only.
- `frontend/src/app/chrome/sidebar/app-sidebar.tsx` (290): no immediate refactor required; keep it composition-only.
- `frontend/src/components/notes-editor.tsx` (255): acceptable for now, but new editor behavior should continue going into helpers/hooks.
- `frontend/src/app/sections/developer-section.tsx` (215): slightly above the component target; only refactor if another workflow is added.

## Recommended implementation order

1. Split `backend/app/services/use_cases/wordbank/collaborators/cor.py` below the hard limit.
2. Reduce `backend/app/services/use_cases/wordbank/core.py` into a thin facade/delegator.
3. Extract persistence/logging helpers from `backend/app/services/use_cases/wordbank/collaborators/verification.py`.
4. Keep the maintainability budget script aligned with repository conventions whenever test layout changes.

## Conclusion

The project is in **better shape than the prior audit suggested**, because the largest backend god file has already been cut down significantly. The maintainability posture is not yet "clean" though: the wordbank backend still concentrates too much orchestration in a few files, and the automation signal needed a small correction to stay trustworthy.
