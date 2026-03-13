# Wordbank section behavior deep dive

This document describes the current, exact behavior of the **Wordbank section** in the frontend UI, including list mode, details mode, meaning sections, pronunciation flows, and Gemini verification interactions.

## Entry points and ownership

- Section switch (list vs details): `frontend/src/app/sections/wordbank-section.tsx`
- Wordbank data loading and detail fetches: `frontend/src/app/hooks/use-lexicon-data.ts`
- Wordbank workflows (add/pronunciation/verification wiring): `frontend/src/app/hooks/use-wordbank-workflows.ts`
- Details view composition:
  - `frontend/src/app/sections/wordbank/wordbank-details-view.tsx`
  - `frontend/src/app/sections/wordbank/wordbank-lemma-header.tsx`
  - `frontend/src/app/sections/wordbank/wordbank-meaning-sections.tsx`
  - `frontend/src/app/sections/wordbank/wordbank-variation-grid.tsx`
- List view rendering:
  - `frontend/src/app/sections/wordbank/wordbank-list-view.tsx`

## High-level mode behavior

The Wordbank section has two UI modes:

1. **List mode** when no lemma is selected.
2. **Details mode** when a lemma is selected.

`WordbankSection` makes this switch purely from `selectedLemma`: no lemma => `WordbankListView`, otherwise `WordbankDetailsView`.

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
- If the selected lemma/meaning verification is still `queued`, details are polled every 1.5s until the verification reaches a final state.
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
- Clicking a chip calls `onSelectLemma(lemma)` and moves to details mode.

## Details mode behavior (WordbankDetailsView)

Primary flow:

- Shows top-level details error alert when `lemmaDetailsError` exists.
- If loading and delayed skeleton gate is open and details are still absent, shows header skeleton.
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
- Header chooses a pronunciation playback form with this precedence:
  1. exact normalized match to selected lemma among selected-meaning forms + top-level forms + all section forms, with pronunciation available
  2. first available pronunciation form from that combined search list
  3. no pronunciation icon/action when none exist

## Header metadata and translation

- Header translation is suppressed in sectioned mode.
- In non-sectioned mode, translation prefers selected meaning translation then lemma translation.
- Header badges are shown only when `showSupplementaryMetadata` is true.
- Badge source in header:
  - POS/morphology from selected meaning (fallback lemma-level)
  - `gram_raw` from lemma-level surface form matching selected lemma

## Header actions

- **Regenerate Audio** button:
  - disabled while regeneration request is in progress
  - spinner icon while active
- **Verification status line**:
  - shows `Verifying since <timestamp>` while selected target verification is queued
  - shows `Verified <timestamp>` when selected target verification succeeded
  - shows `Review needed <timestamp>` when selected target verification failed/was flagged
- **Verification info** popover button:
  - disabled when no verification error for selected target
  - shows count badge for number of suggested actions
  - popover includes provider/reviewed-at/problem/change summary and action cards
  - each action card has `Accept Action` button that is disabled while apply is in progress
- Success badge:
  - displays `Verified` badge when selected lemma/meaning has verification success record
- Queued badge:
  - displays `Verifying...` badge with spinner when selected lemma/meaning has queued verification record

## Body mode A: sectioned meanings (WordbankMeaningSections)

- If no meaning sections exist, shows `No saved meanings for this lemma.`
- Each section renders as a card with:
  - left border color from POS class
  - selected-meaning highlight ring when `selectedMeaningId` matches section id
  - ordinal badge (1-based index)
  - lemma label
  - section-level badges from section POS/morphology
  - optional combined translation line (`english_translation + gloss_translation`)
- Surface forms under each meaning:
  - rendered in a divided list
  - each row uses `WordbankPronunciationWord`
  - form-level badges are filtered to avoid repeating section-level badge labels

## Body mode B: flat variations (WordbankVariationGrid)

- Built from top-level `lemmaDetails.surface_forms`, excluding the normalized selected lemma form itself.
- If there are no remaining variations, the grid renders nothing.
- Each variation tile includes:
  - pronunciation-enabled form title
  - form badges from saved-form metadata
  - optional `from <lemma>` line with merged lemma translation+gloss
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

- Can run as background best-effort after add operations.
- For explicit user regeneration, notification-enabled path is used.
- On `status === "generated"`:
  - cached pronunciation for that form is invalidated
  - `wordbankRefreshTick` increments
  - success toast shown when notify mode is enabled

## Verification workflow behavior

## Background verify (`POST /api/wordbank/lexemes/verify`)

- Triggered in background after add flows (except certain search-seed save paths).
- Results are persisted by backend target scope `(lemma, meaningId)` and returned through subsequent lemma-detail fetches.
- Success path stores a persisted verification success record with `requested_at` / `completed_at`.
- Error path stores a persisted verification error record with timestamps and suggested actions.
- When the open word page observes a queued-to-final transition, the app pushes an in-session notification.

## Action apply (`POST /api/wordbank/lexemes/apply-verification-changes`)

- Accepting a popover action calls apply endpoint with selected target and action payload.
- On applied status:
  - success toast text depends on action type
  - backend persisted verification detail is pruned (remove applied action or delete the record when it is fully resolved / moved)
  - `wordbankRefreshTick` increments
  - app navigates to returned target lemma/meaning
- On failure:
  - error toast shown

## Add flows that affect Wordbank state

## Single-word translation normalization

- Word-level provider translations used by Wordbank are normalized after lookup.
- Content words (for example nouns and verbs) prefer headword-only English output.
- Function words (for example prepositions and conjunctions) may keep only short lexicalized context when removing all context would lose the meaning.
- Phrase translation is not part of this cleanup path.

## Add from playground token

- `POST /api/wordbank/lexemes`
- On success:
  - success toast
  - background verify + pronunciation generation
  - token feedback submission (`source: "playground"`)
  - analysis + wordbank refresh ticks increment

## Add from sidebar search

- `POST /api/wordbank/lexemes`
- On success:
  - success toast
  - optional background verify/pronunciation (skipped when `searchSeed` is present)
  - token feedback submission (`source: "search"`)
  - if response includes `saved_snapshot`, details pane is hydrated immediately from snapshot
  - if that snapshot includes queued verification, the header immediately shows `Verifying...`
  - while that queued verification remains selected, the word page polls until the persisted result becomes final
  - analysis + wordbank refresh ticks increment
  - app navigates to wordbank and selects stored lemma/meaning

## Behavioral test coverage map

The behaviors above are exercised across wordbank-focused UI tests:

- `frontend/src/test/app/app-wordbank-details.test.tsx`
- `frontend/src/test/app/app-wordbank-actions.test.tsx`
- `frontend/src/test/app/app-shell-search-actions.test.tsx` (search-to-wordbank transitions)
- `frontend/src/test/app/app-shell-search-ranking-order.test.tsx` (open selected meaning from search)
