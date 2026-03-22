# App shell behavior

This document captures the app-shell composition contract in the frontend, including section ownership, navigation state transitions, sidebar/breadcrumb interaction rules, notification-center behavior, shared refresh ticks, and where tests validate these behaviors.

## 1. Composition and ownership

### Root shell composition (`frontend/src/App.tsx`)

`App.tsx` owns shell-level composition and wiring:

- Initializes all cross-section state and actions by calling `useAppController()`.
- Wraps the page in `SidebarProvider` and uses `SidebarInset` for the main content area.
- Renders the shell chrome (`AppSidebar`, mobile `SidebarTrigger`, and `AppBreadcrumb`).
- Gates playground-only header actions (`PlaygroundHeaderActions`) so notification/save controls render only when `activeSection === "playground"`.
- Delegates section body rendering to `SectionContent` by passing section-specific prop bundles.

`App.tsx` should stay an orchestration layer: state derivation and side-effect workflows are expected to remain in hooks/composition modules, not in the component body.

### Section layout switch (`frontend/src/app/layout/section-content.tsx`)

`SectionContent` is the canonical section multiplexer:

- Input: `activeSection` plus typed props for each section component.
- Behavior: exactly one section component is rendered at a time.
- Routing contract:
  - `"playground"` -> `PlaygroundSection`
  - `"notes"` -> `NotesSection`
  - `"wordbank"` -> `WordbankSection`
  - `"sentencebank"` -> `SentencebankSection`
  - fallback -> `DeveloperSection`

No additional app-shell side effects should be added here; it is intentionally a pure render switch.

### Chrome ownership (`frontend/src/app/chrome/*`)

#### Sidebar (`frontend/src/app/chrome/sidebar/app-sidebar.tsx`)

`AppSidebar` owns:

- Search-first sidebar header layout with no standalone app title label.
- Primary section navigation buttons (Playground, Notes, Wordbank, Sentencebank, Developer).
- Wordbank unread count badge presentation in nav.
- Command search dialog open/close state and query state.
- Search aggregation + ranking through `useSidebarSearch` + `useSidebarSearchRanking`.
- Search result action dispatch (`onOpenSavedNote`, `onOpenWordbankLemma`, `onOpenWordbankMeaning`, `onAddWordFromSearch`).
- Keyboard shortcuts through `useSidebarHotkeys` (`Alt+P/N/W/S/D` and search toggle).

#### Breadcrumb (`frontend/src/app/chrome/app-breadcrumb.tsx`)

`AppBreadcrumb` owns the current page trail label policy:

- Playground: current active note name (fallback `Playground`).
- Notes: `Notes`.
- Sentencebank: `Sentencebank`.
- Developer: `Developer`.
- Wordbank:
  - root: `Wordbank` as page text.
  - lemma detail: clickable `Wordbank` parent + current `selectedLemma` tail.

#### Header actions

`PlaygroundHeaderActions` (`frontend/src/app/sections/playground-header-actions.tsx`) is used as shell header chrome in playground mode and owns:

- Save / create-new-note button behavior and labeling.
- Notification bell visual state, unread count, and popover rendering.
- Verification-progress spinner state in the notification trigger.

## 2. Section switching contract

Section navigation state is centralized in `useSectionNavigation()`.

### Core state

- `activeSection: AppSection`
- `selectedLemma: string | null`
- `selectedMeaningId: number | null`

### Navigation handlers and selection reset rules

- `selectPlayground()`:
  - `activeSection = "playground"`
  - clears `selectedMeaningId`
  - preserves `selectedLemma`
- `selectNotes()`:
  - `activeSection = "notes"`
  - clears `selectedLemma` and `selectedMeaningId`
- `selectWordbank()`:
  - `activeSection = "wordbank"`
  - clears `selectedLemma` and `selectedMeaningId` (opens wordbank root)
- `selectSentencebank()`:
  - `activeSection = "sentencebank"`
  - clears `selectedLemma` and `selectedMeaningId`
- `selectDeveloper()`:
  - `activeSection = "developer"`
  - clears `selectedLemma` and `selectedMeaningId`
- `openWordbankLemma(lemma)`:
  - `activeSection = "wordbank"`
  - sets `selectedLemma = lemma`
  - clears `selectedMeaningId`
- `openWordbankMeaning(lemma, meaningId)`:
  - `activeSection = "wordbank"`
  - sets `selectedLemma = lemma`
  - sets `selectedMeaningId = meaningId`
- `openWordbankRoot()`:
  - `activeSection = "wordbank"`
  - clears `selectedLemma` and `selectedMeaningId`

### Note selection state (`activeSavedNote` / `selectedNote` equivalent)

The app shell tracks active note selection through `useNotesPersistence()` (`activeNoteId` -> `activeSavedNote`):

- Opening a saved note from notes list or command search calls `openSavedNoteById` -> `openSavedNoteInPlayground`.
- This restores note content/tokens/metadata, sets `activeNoteId`, marks autosave as saved, and navigates to `activeSection = "playground"`.
- Breadcrumb title in playground mode reflects `activeSavedNote?.name`.

## 3. Sidebar + breadcrumb interplay

### Sidebar open/close behavior

Via shared shadcn sidebar primitives (`SidebarProvider`, `Sidebar`, `SidebarTrigger`):

- Desktop:
  - Sidebar is rendered as inset/offcanvas and can collapse/expand.
  - `Ctrl/Cmd + b` toggles sidebar open state.
- Mobile:
  - Sidebar renders as a sheet (`openMobile` state).
  - The `SidebarTrigger` button in the mobile header toggles that sheet.

### Mobile trigger behavior

`App.tsx` renders a header only on `md:hidden` breakpoints with:

- `SidebarTrigger`
- no extra app title text; the trigger stands alone

This provides mobile navigation access without rendering desktop rail interactions.

### Selected target routing and breadcrumb sync

- Sidebar nav buttons call section-select handlers from `useAppController`.
- Search results can route to:
  - note -> `openSavedNoteById` -> playground + active note loaded.
  - wordbank lemma/meaning -> `openWordbankLemma` / `openWordbankMeaning`.
- Breadcrumb renders from `activeSection`, `selectedLemma`, and `activeSavedNote` from the same controller state, so navigation and breadcrumb are synchronized by construction.
- In lemma detail view, clicking breadcrumb `Wordbank` calls `openWordbankRoot()` and resets lemma/meaning selection.

## 4. Notification center semantics

Notification state is managed by `useNotificationCenter()` and surfaced through `PlaygroundHeaderActions`.

### Unread indicators

- Every pushed notification starts with `read: false`.
- `unreadNotifications` is derived by filtering `!read`.
- `hasUnreadNotifications` drives bell styling (`default` variant when unread, otherwise `outline`).
- Unread count shown on bell comes from `unreadNotifications.length`.
- Wordbank-specific unread badge in sidebar comes from unread `kind === "word_verification"` notifications.
- Word verification notifications are current-state records, not an append-only event log:
  - each target is keyed by `(lemma, meaningId, surfaceForm)` via `targetKey`
  - queued, review-needed, and retry updates upsert the same notification row for that target
  - verified or skipped settlements remove any existing current-state notification row for that target, so unchanged Gemini success is silent
  - sidebar lemma badges are derived from unread current-state verification targets grouped by lemma

### Open/close

- Popover open state is controlled by `isNotificationsOpen` + `setIsNotificationsOpen` in app controller.
- Bell button is disabled only when there are no unread notifications and verification is not currently running.
- If verification is running, bell shows spinner icon and remains available as status affordance.
- Verification-running state can come from backend-queued wordbank jobs even when the user has already navigated away from that lemma page; the frontend tracks queued targets returned from add responses and polls those lemmas until each target settles.
- Completion-variations follow-up reviews for noun, adjective, and verb meaning sections participate in the same off-page tracking flow using the explicit `queued_verification_targets` returned by the complete-variations API response.

### Mark-read behavior

- Global mark-read API exists: `markAllNotificationsAsRead()`.
- Automatic read-on-navigation is no longer used for word verification notifications.
- Targeted mark-read now happens only when the user opens the word-page verification popover.
- Matching rules for targeted mark-read:
  - only unread `word_verification` notifications are eligible
  - the popover marks read only the verification targets currently visible on that word page
  - matching uses the same per-target `targetKey` used for notification upserts, so meaning-level and surface-level verification rows stay distinct

## 5. Shared refresh ticks and propagation

`useAppFoundation()` provides refresh ticks consumed by data hooks and workflows:

- `wordbankRefreshTick`
- `sentencebankRefreshTick`
- analysis refresh tick (inside `useAnalysis`, updated through `setAnalysisRefreshTick` passed into wordbank workflows)

### Cross-section update flows

- Adding a word (playground token add or search add) increments:
  - analysis refresh tick
  - wordbank refresh tick
  This keeps token analysis and wordbank UI synchronized after persistence.

- Saving a sentence to sentencebank increments:
  - sentencebank refresh tick
  This refreshes sentencebank lists and closes phrase popover through `onSentenceSaved` composition behavior.

- Pronunciation regeneration and verification workflows can bump wordbank refresh tick, allowing wordbank detail/list views to re-fetch updated lemma data.

- `useLexiconData()` receives `activeSection`, `selectedLemma`, and both refresh ticks, so background data fetch behavior responds both to navigation targets and mutation side effects.

## 6. App-shell test coverage map (`frontend/src/test/app/app-shell-*.test.tsx`)

Current app-shell tests are search/shell focused.

### `app-shell-search-basics.test.tsx`

Covers:

- shell baseline render (header/status/nav)
- sidebar navigation presence
- command dialog open + mixed results behavior
- saved lemma top action/eye icon behavior
- fallback and minimal-query behavior for wordbank API search

### `app-shell-search-actions.test.tsx`

Covers:

- COR grouped variant rendering and add actions
- post-add section/open behavior and metadata row expectations
- local COR request debounce + cache behavior
- opening saved snapshot word page before detail reload completion

### `app-shell-search-errors.test.tsx`

Covers:

- translation failure degradation (untranslated COR still shown)
- network failure while adding from search
- API error propagation while adding from search

### `app-shell-search-ranking-order.test.tsx`

Covers:

- exact-form homograph add-action ordering
- opening selected saved meaning section from search
- saved row presentation consistency
- exact-query gating for saved-prefix matches
- priority order: saved exact match above add-variation candidates

### `app-shell-search-ranking-results.test.tsx`

Covers:

- second-line suppression when gloss is absent
- retaining alternative add options with exact saved forms
- saved-variation eye icon behavior with alternatives preserved
- hiding only saved COR id while keeping homonym alternatives

### `app-shell-search-ranking-selection.test.tsx`

Covers:

- selection ordering between exact-lemma open and linked variation rows
- existing-lemma variation priority vs other COR options
- exact-query gating for saved lemmas with non-legacy badges

### `app-shell-search-ranking-state.test.tsx`

Covers:

- preserving added result visibility/selection across exact-query transitions
- resetting command selection to first result on new search updates

### Coverage gap note

These app-shell tests currently emphasize sidebar command search ranking, actions, and resilience. They do not directly assert mobile sidebar trigger behavior or explicit breadcrumb click-back behavior; those contracts are primarily covered by implementation coupling in `App.tsx`, `AppBreadcrumb`, and shared sidebar primitives.
