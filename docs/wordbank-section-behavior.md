# Wordbank section behavior deep dive

This document describes the current, exact behavior of the **Wordbank section** in the frontend UI, including list mode, the lemma **word page**, meaning sections, pronunciation flows, and Gemini verification interactions.

## Entry points and ownership

- Section switch (list vs word page): `frontend/src/app/sections/wordbank-section.tsx`
- Wordbank data loading and detail fetches: `frontend/src/app/hooks/use-lexicon-data.ts`
- Wordbank workflows (add/pronunciation/verification wiring): `frontend/src/app/hooks/use-wordbank-workflows.ts`
- Word page composition:
  - `frontend/src/app/sections/wordbank/wordbank-word-page.tsx`
  - `frontend/src/app/sections/wordbank/wordbank-lemma-header.tsx`
  - `frontend/src/app/sections/wordbank/wordbank-verification-popover.tsx`
  - `frontend/src/app/sections/wordbank/wordbank-meaning-sections.tsx`
  - `frontend/src/app/sections/wordbank/wordbank-variation-grid.tsx`
- List view rendering:
  - `frontend/src/app/sections/wordbank/wordbank-list-view.tsx`

## High-level mode behavior

The Wordbank section has two UI modes:

1. **List mode** when no lemma is selected.
2. **Word page mode** when a lemma is selected.

`WordbankSection` makes this switch purely from `selectedLemma`: no lemma => `WordbankListView`, otherwise `WordbankWordPage`.

## Data loading lifecycle

## Lemma list loading (`/api/wordbank/lemmas`)

- Wordbank list is **deferred**; it loads only when one of these is true:
  - active section is `wordbank`
  - a lemma is selected
  - wordbank has already been loaded once (`hasLoadedWordbank`)
- The list is not re-fetched if current `wordbankRefreshTick` was already loaded.
- On success:
  - list state (`lemmas`) is updated
  - lazy-load marker is set
  - loaded tick is recorded
- On failure:
  - user-facing `wordbankError` is set
  - list is cleared

## Lemma details loading (`/api/wordbank/lemmas/{lemma}`)

- Details are fetched only when:
  - active section is `wordbank`
  - and `selectedLemma` is present
- If any verification target on the open word page is still `queued`, details are polled every 1.5s until all visible targets reach a final state.
- Leaving wordbank or clearing selection resets details state (`lemmaDetails`, loading/error/skeleton flags).
- A loading skeleton is intentionally delayed by 180ms:
  - avoids flicker for fast responses
  - only shown if request outlives the delay
- Poll refresh failures keep the last rendered details visible and only update the error banner.

## List mode behavior (WordbankListView)

Priority order in list mode:

1. If `wordbankError` exists, show error alert text.
2. If loading and `lemmas.length === 0`, show grouped skeleton placeholders.
3. If no lemmas, show `No saved lemmas yet.`
4. Otherwise render grouped lemma chips with letter headings.

Per-lemma chip behavior:

- Label prefers `display_lemma`, falling back to `lemma`.
- Variation count suffix (`· N`) is shown only when `variation_count > 1`.
- Unread verification markers:
  - unread `1` => small dot indicator
  - unread `>1` => numeric badge pill
- Clicking a chip calls `onSelectLemma(lemma)` and opens that lemma's word page.

## Word page behavior (WordbankWordPage)

Primary flow:

- Shows top-level details error alert when `lemmaDetailsError` exists.
- If loading and delayed skeleton gate is open and details are still absent, shows a full word-page skeleton with header chrome and repeated body cards.
- If loading but skeleton gate has not opened yet, renders `null` (no placeholder yet).
- If not loading and no details found, renders `No details found for this lemma.`
- With details payload:
  - always renders `WordbankLemmaHeader`
  - then renders one of two bodies:
    - sectioned body (`WordbankMeaningSections`) when `lemmaDetails.is_sectioned === true`
    - flat variation body (`WordbankVariationGrid`) otherwise

Meaning auto-scroll behavior:

- When a specific meaning id is selected in sectioned mode, the view scrolls that section card into view via `requestAnimationFrame` + `scrollIntoView({ behavior: "smooth", block: "nearest" })`.

## Header behavior (WordbankLemmaHeader)

## Title/pronunciation source selection

- Header title always uses `lemmaDetails.lemma` (via `WordbankPronunciationWord`).
- Right-clicking the header word opens its contextual audio menu.
- Header chooses a pronunciation playback form with this precedence:
  1. exact normalized match to selected lemma among selected-meaning forms + top-level forms + all section forms, with pronunciation available
  2. first available pronunciation form from that combined search list
  3. no pronunciation icon/action when none exist
- For sectioned lemmas, backend detail payloads may keep the lemma form in top-level `surface_forms`
  even while meaning-section lists continue to show only non-lemma variations. This preserves exact
  lemma pronunciation playback without duplicating the lemma row inside each section card.

## Header metadata and translation

- Header translation is suppressed in sectioned mode.
- In non-sectioned mode, translation prefers selected meaning translation then lemma translation.
- Header badges are shown only when `showSupplementaryMetadata` is true.
- Badge source in header:
  - POS/morphology from selected meaning (fallback lemma-level)
  - `gram_raw` from lemma-level surface form matching selected lemma
- Non-sectioned semantic category badges:
  - render from top-level `lemmaDetails.categories`
  - appear in their own header row below the title/translation block
  - use dedicated outline styling distinct from POS/morphology badges
  - non-sectioned root-scope recategorization moved onto the lemma word's own right-click menu instead of the whole header block

## Header actions

- **Verification trigger button**:
  - remains the only visible header action button
  - icon is dynamic by the aggregated word-page verification state:
    - idle/no record -> info icon
    - queued -> spinner
    - verified -> success/check icon
    - error/flagged -> alert icon
  - trigger priority is:
    - `review` if any target is flagged or errored
    - otherwise `queued` if any target is queued
    - otherwise `verified` if all available targets are verified
    - otherwise neutral
  - review-needed state shows the total suggested-action count inline on the trigger when actions are present
- **Verification popover**:
  - is the single surface for verification status/details; the old standalone status line and success/queued badges are not rendered anymore
  - opening the popover marks only the currently visible verification targets as read in the app notification center
  - uses a fixed-height scrollable content area so long verification histories and action lists stay contained
  - includes provider metadata, an aggregated progress/status summary card, and state counts for all rendered targets
  - renders one target card per visible verification target in word-page order:
    - non-sectioned page: lemma/root target plus each non-lemma variation target that has verification data
    - sectioned page: each meaning-section target plus each verified/queued/reviewable variation target inside that meaning
  - queued target cards show verification-in-progress copy and requested time
  - verified target cards show completion copy and verified time
  - error/flagged target cards show reviewed time, problem, change-to-implement text, and action cards inline on that target
  - error target cards also expose `Retry verification`, which queues that exact target again through the backend queue-only endpoint and keeps the page in polling mode until the refreshed run finishes
  - unchanged `verified` results do not create or keep app-level notification rows; successful Gemini completion is silent outside the word-page popover
  - completion-review meaning cards may expose exactly one `Fix variations` action card that rewrites the whole saved noun variation set for that meaning in one apply
  - completion-review `Fix variations` summaries can describe reviewed noun-slot sets directly, including multiple spellings in one slot such as `Singular indefinite: fader, far`
  - completion-review meaning cards never expose `Move to lemma`, `Move to different meaning`, or translation-fix actions
  - no-record state shows a neutral empty state explaining that verification details will appear here once Gemini runs
  - each action card uses an `Apply change` button that is disabled while apply is in progress

## Word-card context menu

- Wordbank word pages use the shadcn `ContextMenu` primitive for both word-specific audio actions and category-bearing scopes.
- Every pronunciation-enabled word trigger uses the same tooltip copy (`Click to listen`) and the tooltip opens on the left side of the word.
- Sectioned pages:
  - the header lemma word exposes `Regenerate audio`
  - each meaning card is a context-menu trigger
  - noun, adjective, and verb meaning cards expose `Rethink categories` and `Complete variations`
  - other meaning cards expose only `Rethink categories`
  - each surface-form word inside a meaning card also exposes its own `Regenerate audio` action from a nested right-click menu
- Non-sectioned pages:
  - the lemma word is the combined context-menu trigger for root-scope actions
  - that menu exposes `Regenerate audio` plus `Rethink categories`
  - each flat variation word tile also exposes its own `Regenerate audio` action from the word trigger
- `Rethink categories` immediately calls the backend recategorization endpoint for that root / meaning scope and refreshes lemma details after success.
- The action does not open a confirmation flow and does not apply Gemini verification suggestions; it only recalculates semantic category assignments.
- The manual rethink path uses the same Gemini category-classification flow as initial verification; the only difference is that this one is user-triggered.
- `Complete variations` is meaning-only in v1 for noun, adjective, and verb sections.
  - noun sections fill any missing non-lemma noun variations:
    singular-definite, plural-indefinite, and plural-definite.
  - adjective sections fill any missing non-lemma agreement forms:
    singular-indefinite `t-word`, singular-definite, and shared plural forms.
    Shared plural forms are persisted once and rendered into both plural cells on the table.
  - verb sections fill any missing verb-table forms:
    present, past, imperative, and past participle.
    The infinitive row is derived from the section's canonical lemma metadata unless a distinct saved infinitive row exists.
- The action is gated by verification state for that meaning section.
  It is enabled only when the meaning target and every currently saved variation target in that meaning are `verified`.
- When gated, the context-menu item stays visible but disabled with one of these labels:
  - `Waiting for verification...` when any target in the meaning is `queued`
  - `Retry verification first` when any target is `error`
  - `Resolve verification review first` when any target is `flagged`
  - `Complete variations unavailable` for any other non-verified state
- The completion action queues pronunciation generation only for newly added forms.
- After completion, Gemini re-verification is requeued as a single meaning-scoped review for that updated meaning section, not one request per variation row.
- The completion API response includes `queued_verification_targets`; the frontend registers those meaning targets with background tracking so the follow-up review continues to drive spinner state and final notifications even after the user leaves the lemma page.
- That completion-specific review keeps the saved lemma fixed and checks whether the completed surface forms fit that lemma/meaning; it does not use canonical-lemma mismatch alone as a reason to suggest moving the lemma.
- When that review flags the completed set, the backend exposes one meaning-level `Fix variations` apply action instead of per-variation actions or relocation actions.
- Existing per-surface verification records for that meaning are cleared before the completion review is requeued, so the refreshed page shows the meaning-level review as the source of truth for that completion pass.
- If the meaning lacks enough saved COR identity to resolve the paradigm, the action is skipped with a user-facing message.

## Body mode A: sectioned meanings (WordbankMeaningSections)

- If no meaning sections exist, shows `No saved meanings for this lemma.`
- Each section renders as a card with:
  - left border color from POS class
  - no extra selected-state border or ring; `selectedMeaningId` is used for scroll targeting and header context only
  - left-side metadata cluster: lemma label and section-level POS/morphology badges
  - verb meaning cards render the lemma in infinitive display form with `at <lemma>`
  - when backend detail payloads include section `gram_raw`, the section badge set is derived from that COR grammar so invariant lemma forms (for example `orange`) keep the same merged badge set shown in search
  - right-side semantic category badge cluster from `meaning_sections[].categories`
  - category badges stay right-aligned on wider layouts and wrap below the header content on narrow screens
  - optional combined translation line in `translation, gloss translation` format when a real English translation exists
  - gloss translation is supplemental disambiguation text; it does not replace a missing translation
- Surface forms under each meaning:
  - rendered in a divided list
  - each row uses `WordbankPronunciationWord`
  - section lists render only non-lemma variations for that meaning
  - top-level `surface_forms` may still include the lemma form as a separate deduped header/audio source
  - noun and adjective meanings render a shared 2x2 paradigm table as soon as at least one paradigm slot can be derived
  - verb meanings render the same shared table shell with fixed rows:
    `Infinitive`, `Present`, `Past`, `Imperative`, and `Past participle`
  - this means the initial saved noun / adjective / verb form is shown in the table immediately, even before any additional variations are saved
  - adjective tables use number on one axis and definiteness on the other; the singular-indefinite cell contains separate `n-word` and `t-word` lines
  - adjective same-form entries (for example `store` or invariant forms like `orange`) may render into multiple cells from merged `gram_raw`
  - verb same-form entries (for example a form whose merged `gram_raw` covers both past and imperative) may render into multiple verb rows
  - noun variations are ordered with non-slot/irregular forms first, then singular-definite, plural-indefinite, and plural-definite
  - saved POS/morphology badges normalize to the same reader-facing label style used in COR search where morphology allows it (for example adjective agreement uses `n-word` / `t-word` rather than `Common` / `Neuter`)
  - when a saved surface form has COR context, its details payload may also include `gram_raw`; those rows render badges from `gram_raw` first so search and word-page badges stay aligned
  - form-level badges are filtered to avoid repeating section-level badge labels

## Body mode B: flat variations (WordbankVariationGrid)

- Built from top-level `lemmaDetails.surface_forms`, excluding the normalized selected lemma form itself.
- noun, adjective, and verb flat pages prefer the shared paradigm table even when the only saved form is the lemma itself
- empty paradigm cells stay blank until manual saves or complete-variations fills them
- For non-paradigm pages, if there are no remaining variations, the grid renders nothing.
- Each variation tile includes:
  - pronunciation-enabled form title
  - right-click `Regenerate audio` on that specific word
  - form badges from saved-form metadata
  - optional `from <lemma>` line with merged lemma translation+gloss when lemma translation exists
  - POS-colored left border

## Pronunciation workflow behavior

Pronunciation behavior is shared by header + section rows + variation rows.

## Play flow (`GET /api/wordbank/pronunciation?form=<form>`)

- Form key is normalized first; empty key does nothing.
- Per-form loading state is set while request/playback runs.
- Pronunciation blobs are cached in-memory as object URLs by normalized form.
- On 404 from pronunciation endpoint, user gets: `No pronunciation is available yet for '<form>'.`
- Returned audio is validated for playable audio content-type.
- If a currently active audio element exists, it is paused before playing new audio.
- If playback fails due to unsupported audio once:
  - cache is cleared for that form
  - forced background regeneration is attempted
  - playback retries once

## Regenerate flow (`POST /api/wordbank/lexemes/pronunciation`)

- For explicit user regeneration, notification-enabled path is used and the request targets the exact right-clicked word (`stored_surface_form`) instead of a header-only lemma action.
- Automatic add/save/completion flows no longer call this endpoint from the browser.
  They queue lemma-scoped pronunciation work in the backend and let the word page refresh from persisted state.
- On `status === "generated"`:
  - cached pronunciation for that form is invalidated
  - `wordbankRefreshTick` increments
  - success toast shown when notify mode is enabled

## Verification workflow behavior

## Background verify

- Add flows no longer trigger browser-side Gemini verification calls.
- After every successful add, the backend enumerates the current saved word page and queues verification for each visible target.
- Manual retries also use backend queueing only:
  `POST /api/wordbank/lexemes/queue-verification` requeues one exact target by `(stored_lemma, meaning_id, stored_surface_form, review_intent)`.
- `Complete variations` uses a narrower follow-up path: it queues one meaning-level verification request for the updated meaning instead of requeueing each variation target separately.
- Only that completion-specific follow-up review is allowed to question or rewrite the generated variation set.
  The initial verification run after save is not allowed to suggest completing or correcting other paradigm members.
- Completion follow-up reviews are strict `fix_variations` workflows:
  - Gemini prompt examples only advertise `fix_variations`
  - backend normalization drops any other returned action types
  - apply rejects any non-`fix_variations` action for persisted `review_intent = "complete_variations"` records
- Target discovery rules:
  - non-sectioned page: one lemma/root target plus one target per non-lemma saved variation
  - sectioned page: one target per meaning section plus one target per saved variation within that meaning
  - no synthetic root target is added for sectioned pages unless a root-level saved record actually exists
- Results are persisted by backend target scope `(lemma, meaning_id, stored_surface_form)` and returned through subsequent lemma-detail fetches.
- Queue dedupe is stable per verification target, not per snapshot hash.
- Completion follow-up review records remain meaning-scoped only; once requeued, they replace stale per-surface completion records for that meaning instead of coexisting with them.
  Repeated edits or retries to the same target update the queued request generation instead of spawning competing duplicate jobs.
- Verification persistence is newest-request-wins:
  if a target changes while Gemini is already running, the stale run is discarded at persist time and the queue immediately keeps the latest request pending for the next worker claim.
- Verification evaluates the current persisted wordbank structure:
  lemma page -> meaning sections -> surface forms.
- Normal verification after save checks only whether the saved lemma / meaning / selected surface placement is correct.
  It does not fail just because other paradigm members are missing, and it does not suggest variation-completion work.
- Verification payloads include both the saved lemma and the best COR-backed canonical lemma identity when that dictionary lemma can be resolved from saved COR ids / lemma indexes.
- When COR indicates the saved lemma is an inflected form rather than the true dictionary lemma (for example `mor` vs `moder`), Gemini is prompted to flag the entry and suggest a `move_to_lemma` correction toward the canonical lemma.
- Exception: the completion-specific meaning review for `Complete variations` keeps the saved lemma fixed and treats canonical-lemma mismatch as a signal to question the generated variation set, not to rewrite the lemma.
- For that completion-specific review, Gemini/backend remediation is modeled as a single meaning-level `fix_variations` action that can rewrite the saved noun, adjective, or verb variations in one apply.
- New completion-review `fix_variations` actions can carry reviewed noun-slot form lists directly (`singular_indefinite_forms`, `singular_definite_forms`, `plural_indefinite_forms`, `plural_definite_forms`) or reviewed adjective-slot form lists directly (`singular_indefinite_n_word_forms`, `singular_indefinite_t_word_forms`, `singular_definite_forms`, `plural_indefinite_forms`, `plural_definite_forms`) so apply does not have to trust the same COR paradigm that produced the bad completion set.
- `singular_indefinite_forms` may include the saved lemma plus alternative spellings for the same slot; apply treats that reviewed list as the exact saved slot set and removes stale aliases.
- Older saved completion reviews that only have prose in `change_to_implement` are still applyable because the backend can extract those noun-slot targets from the persisted review text before mutating the meaning.
- Translation context comes only from the lemma or meaning section.
  Surface forms do not have independent translations in the verification model.
- Meaning glosses are treated as immutable COR disambiguators.
  Gemini may use them to identify the intended sense, but it does not propose gloss edits.
- For meaning-section verification, the reviewed section is sent as the current scope and not duplicated in the sibling-meaning list.
- When available, Gemini also receives translated gloss hints for the reviewed meaning, sibling meanings, and scoped surface forms to disambiguate homographs such as `mor`.
- Canonical lemma metadata is evaluated separately from the selected saved surface-form metadata.
- The same Gemini verification call also classifies the reviewed root / meaning scope into semantic categories.
  - Gemini receives the shared persisted category list plus the categories already assigned to that scope.
  - Gemini also receives the whole saved-word context for that lemma: reviewed scope metadata, gloss, translation scope, sibling meaning sections, and the full saved surface-form inventory with meaning links and morphology.
  - It may choose multiple existing categories.
  - If needed, it may mint up to 3 new broad categories, which are stored for later runs.
  - Category assignments are auto-applied with no confirmation step and show up through later lemma-detail fetches.
- Queue execution is backend-driven through the shared wordbank background-job runner.
  Multiple verification targets can execute in parallel through a bounded worker pool.
- Queued verification payloads carry a target snapshot hash.
  If the word page changes before a queued job runs, that stale job is skipped instead of overwriting a newer verification result.
- Success path stores a persisted verification success record with `requested_at` / `completed_at`.
- Error path stores a persisted verification error record with timestamps and suggested actions.
- When a queued target reaches a final state, the app pushes a target-specific in-session notification.

## Category rethink

- `POST /api/wordbank/lexemes/rethink-categories` reruns Gemini category classification for a specific root / meaning scope using the current shared category list and the categories already assigned to that scope.
- This path is triggered manually from the word-card context menu.
- It uses the same Gemini categorization payload as the initial verification run, including full saved surface-form context and sibling meaning context for the whole word page.
- Gemini may reuse multiple existing categories and may mint up to 3 new broad categories when needed.
- Successful recategorization replaces the full persisted category assignment set for that scope.
- Recategorization does not overwrite or re-review existing verification records.

## Action apply (`POST /api/wordbank/lexemes/apply-verification-changes`)

- Accepting a popover action calls apply endpoint with selected target and action payload.
- Apply requests always include the exact verification scope: `stored_lemma`, `meaning_id`, and `stored_surface_form`.
- Meaning-level completion-review fixes use `action_type=fix_variations` with `stored_surface_form=null`; applying that action reconciles the whole saved noun variation set for that meaning.
- `fix_variations` prefers reviewed noun-slot form lists carried by the saved action, then falls back to legacy scalar fields or forms recovered from the saved review text, and only uses COR slot metadata when a reviewed slot form is missing.
- On applied status:
  - success toast text depends on action type
  - backend persisted verification detail is pruned action-by-action
  - when the last Gemini suggestion for a target has been applied, backend persistence flips that resolved target to `verified` instead of removing verification state entirely
  - `wordbankRefreshTick` increments
  - app navigates to returned target lemma/meaning
- If apply does not change the visible variation set, the backend returns `status=skipped` and the review remains pending.
- On failure:
  - error toast shown

## Add flows that affect Wordbank state

## Single-word translation normalization

- Word-level provider translations used by Wordbank are normalized after lookup.
- Content words (for example nouns and verbs) remove obvious frame scaffolding, but noun phrases may stay multi-word when cleanup is not clearly safe.
- Function words (for example prepositions and conjunctions) may keep only short lexicalized context when removing all context would lose the meaning.
- Phrase translation is not part of this cleanup path.

## Add from playground token

- `POST /api/wordbank/lexemes`
- On success:
  - success toast
  - backend queues verification for the full current word page
  - backend also returns `queued_pronunciation_forms` for the shared pronunciation queue
  - while the open word page still has queued pronunciation forms without stored audio, lemma-details polling stays active for a bounded window so play buttons update without a manual refresh
  - token feedback submission (`source: "playground"`)
  - analysis + wordbank refresh ticks increment

## Add from sidebar search

- `POST /api/wordbank/lexemes`
- On success:
  - success toast
  - backend queues verification for the full current word page
  - backend also returns `queued_pronunciation_forms` for the shared pronunciation queue
  - token feedback submission (`source: "search"`)
  - if response includes `saved_snapshot`, details pane is hydrated immediately from snapshot
  - response also includes `queued_verification_targets`, which seed off-page verification tracking
  - if that snapshot includes queued verification, the header immediately shows `Verifying...`
  - while any open-page target remains queued, the word page polls until the persisted results become final
  - while the selected lemma still has queued pronunciation forms without stored audio, the same open-page polling loop also waits for those forms for a bounded window
  - analysis + wordbank refresh ticks increment
  - app navigates to wordbank and selects stored lemma/meaning
- For `search_seed` saves, backend persistence separates canonical lemma metadata from selected surface metadata:
  - lemma/root and newly created meaning-section tags come from the canonical COR lemma when `cor_lemma_idx` is available
  - the stored selected surface form keeps the chosen variant tags from the search result
  - saved `english_translation` comes only from the COR lemma translation; gloss translation remains separate disambiguation context
  - the word page now computes and returns gloss translations for search-saved meaning sections too, so homograph meanings can render `translation, gloss translation`
  - raw gloss text is not promoted into `english_translation`, and the UI omits untranslated gloss from translation lines
  - only the selected surface form is stored; search save does not hydrate the full paradigm into wordbank

## Complete variations follow-up

- `POST /api/wordbank/lexemes/complete-variations`
- On success:
  - missing paradigm members are inserted for the selected meaning
  - pronunciation queueing is merged through one lemma-scoped background job keyed by `stored_lemma`
  - `queued_pronunciation_forms` contains the forms still missing stored audio after the completion pass
  - the lemma itself may appear in that list when the root lemma row still needs pronunciation audio
  - the open word page keeps polling lemma details for a bounded window until those forms show `has_pronunciation=true` or the local timeout expires

## Behavioral test coverage map

The behaviors above are exercised across wordbank-focused tests with explicit roles:

- `renderer-only`: `frontend/src/test/app/app-wordbank-details.test.tsx`, `frontend/src/test/app/app-wordbank-actions.test.tsx`
- `request-shape`: `frontend/src/test/app/app-shell-search-actions.test.tsx`
- `contract`: `backend/tests/use_cases/test_wordbank_translation_details.py`, `backend/tests/api/test_wordbank_add_and_list_endpoint.py`
- `round-trip`: `backend/tests/use_cases/test_wordbank_add_and_list.py`, `backend/tests/api/test_wordbank_add_and_list_endpoint.py`
- `queue/orchestration`: `backend/tests/use_cases/test_wordbank_pronunciation_and_verification.py`
- shared contract fixtures for the frontend word page/search assertions live in `frontend/src/test/app/wordbank-contract-fixtures.ts`
