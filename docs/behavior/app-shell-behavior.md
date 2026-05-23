# App shell behavior

App-shell composition contract: section ownership, navigation state, sidebar/breadcrumb interaction, notification center, shared refresh ticks, test coverage.

## 1. Composition and ownership

### Root shell composition (`frontend/src/App.tsx`)

`App.tsx` owns:
- Cross-section state/actions via `useAppController()`
- Signed-in versus guest entry state: Clerk tokens for accounts, guest bearer
  tokens from `POST /api/guest/sessions`
- `SidebarProvider` + `SidebarInset` wrapper
- Chrome: `AppSidebar`, mobile `SidebarTrigger`, `AppBreadcrumb`
- Delegates section body to `SectionContent` with typed prop bundles

Stays orchestration layer: state/side-effects in hooks, not component body.

### Guest entry

- Signed-out users see `Sign in` and `Continue as guest`.
- Starting guest mode stores an anonymous browser id in `localStorage`, a guest
  bearer token in `sessionStorage`, and renders the normal app shell without
  the API-key gate.
- Guest workspaces are scoped to a newly created backend guest user each time
  guest mode is started; wordbank/sentencebank data is not restored across new
  guest sessions.
- The Account section shows guest status and remaining daily searches instead
  of Clerk profile controls or API-key forms.
- The Account section includes a destructive start-fresh action for every
  account type. It deletes the current user's saved words and sentences while
  pruning custom categories left unassigned by the reset, restoring the
  standard starter categories, and keeping sign-in, guest session, API keys,
  trial status, and daily usage counters intact.

### Section layout switch (`frontend/src/app/layout/section-content.tsx`)

`SectionContent`: canonical section multiplexer. Input: `activeSection` + typed props. Exactly one section rendered:
- `"wordbank"` -> `WordbankSection`
- `"sentencebank"` -> `SentencebankSection`
- fallback -> `DeveloperSection`

Pure render switch; no app-shell side effects.

### Chrome ownership (`frontend/src/app/chrome/*`)

#### Sidebar (`frontend/src/app/chrome/sidebar/app-sidebar.tsx`)

- Header title: `danote`, clicking it opens the Wordbank root
- Section nav buttons: Wordbank, Sentencebank, Developer
- Wordbank unread badge in nav
- Command search dialog state + query state
- Search aggregation/ranking: `useSidebarSearch` + `useSidebarSearchRanking`
- Search result actions: `onOpenWordbankLemma`, `onOpenWordbankMeaning`, `onAddWordFromSearch`
- Keyboard shortcuts: `useSidebarHotkeys` (`Alt+W/S/D`, search toggle)

#### Breadcrumb (`frontend/src/app/chrome/app-breadcrumb.tsx`)

Page trail labels:
- Sentencebank: `Sentencebank`
- Developer: `Developer`
- Wordbank root: `Wordbank`; lemma detail: clickable `Wordbank` + `selectedLemma` tail
- Built-in Wordbank reference tails use grouped labels: `Pronouns`, `Function Words`, `Numbers & Time`

## 2. Section switching contract

Centralized in `useSectionNavigation()`.

### Core state

- `activeSection: AppSection`
- `selectedLemma: string | null`
- `selectedMeaningId: number | null`

### Navigation handlers and selection reset rules

- `selectWordbank()`: `activeSection = "wordbank"`, clears `selectedLemma` + `selectedMeaningId` (root)
- `selectSentencebank()`: `activeSection = "sentencebank"`, clears `selectedLemma` + `selectedMeaningId`
- `selectDeveloper()`: `activeSection = "developer"`, clears `selectedLemma` + `selectedMeaningId`
- `openWordbankLemma(lemma)`: `activeSection = "wordbank"`, maps built-in words to grouped pinned sentinels, clears `selectedMeaningId`
- `openWordbankLemmaRaw(lemma)`: `activeSection = "wordbank"`, keeps the raw lemma for pinned word-card and command-search saved-row click-through, clears `selectedMeaningId`
- `openWordbankPinnedTab(sentinel)`: `activeSection = "wordbank"`, writes a tab-specific pinned sentinel so browser Back/Forward restores the selected pinned tab
- `openWordbankMeaning(lemma, meaningId)`: `activeSection = "wordbank"`, sets both
- `openWordbankRoot()`: `activeSection = "wordbank"`, clears `selectedLemma` + `selectedMeaningId`

### Note selection state

Notes section navigation is retired. Saved-note persistence code remains dormant for existing local data, but no app-shell route, sidebar item, keyboard shortcut, or command-palette page opens `NotesSection`.

## 3. Sidebar + breadcrumb interplay

### Sidebar open/close

Via shadcn sidebar primitives:
- Desktop: inset/offcanvas, collapse/expand; `Ctrl/Cmd+b` toggles
- Mobile: sheet (`openMobile`); `SidebarTrigger` toggles

### Mobile trigger

`App.tsx` header on `md:hidden`: `SidebarTrigger` only, no app title text.

### Selected target routing and breadcrumb sync

- Nav buttons call section-select handlers from `useAppController`
- Sidebar title calls `selectWordbank()` and resets to the Wordbank root
- Search results route to:
  - saved wordbank lemma rows → `openWordbankLemmaRaw`
  - saved wordbank meaning rows → `openWordbankMeaning`
  - sentence-token saved word clicks → raw word-page navigation
  - built-in collection links → sentinel-aware `openWordbankLemma`
- Mobile command search writes a transient browser-history entry while open;
  browser Back closes the full-screen search page and restores the page that was
  visible before search instead of stepping through app section history.
- Breadcrumb renders from same controller state (`activeSection`, `selectedLemma`) → nav + breadcrumb synchronized by construction
- Lemma detail: clicking breadcrumb `Wordbank` → `openWordbankRoot()`, resets lemma/meaning

### Sign-in return behavior

- Clerk sign-in triggers force successful sign-in and sign-up confirmation flows
  back to the app root so browser Back does not return users to the account
  confirmation step after entry.

## 4. Notification center semantics

State: `useNotificationCenter()`; surface: sidebar/header notification controls.

### Unread indicators

- Pushed notifications start `read: false`; `unreadNotifications` = filtered `!read`
- `hasUnreadNotifications` drives bell variant (`default` unread, `outline` otherwise)
- Unread count = `unreadNotifications.length`
- Wordbank sidebar badge: only unread action-required `word_verification` (`flagged`/`error`), not queued/in-progress
- Word verification notifications = current-state records (not append-only event log):
  - keyed by `(lemma, meaningId, surfaceForm)` via `targetKey`
  - queued/in-progress → no notification row
  - review-needed/retry-needed → upsert same row
  - verified/skipped → remove row (silent success)
  - sidebar badges: unread current-state targets grouped by lemma

### Open/close

- Popover state: `isNotificationsOpen` + `setIsNotificationsOpen` in app controller
- Bell disabled: no unread + not currently verifying
- Verifying → spinner icon, bell stays available as status affordance
- In-progress → spinner only; no unread count until target reaches action-required state
- Verification-running state persists from backend-queued jobs even after navigating away; frontend tracks queued targets from add responses, polls until settled
- Completion-variations follow-up reviews participate in same off-page tracking via `queued_verification_targets` from complete-variations response

### Mark-read behavior

- Global: `markAllNotificationsAsRead()`
- Auto read-on-navigation: no longer used for word verification
- Targeted: only when user opens word-page verification popover
- Matching: only unread `word_verification`; popover marks only visible targets on that word page; uses same `targetKey` as upserts (meaning-level and surface-level rows stay distinct)

## 5. Shared refresh ticks and propagation

`useAppFoundation()` provides:
- `wordbankRefreshTick`
- `sentencebankRefreshTick`
- analysis refresh tick (via `useAnalysis`, `setAnalysisRefreshTick` passed to wordbank workflows)

### Cross-section update flows

- Adding word from search → increments analysis + wordbank refresh ticks
- Saving sentence to sentencebank → increments sentencebank refresh tick → refreshes lists
- Account start-fresh action → clears local wordbank/sentencebank state and
  increments both refresh ticks
- Pronunciation regeneration + verification workflows → may bump wordbank refresh tick
- `useLexiconData()` receives `activeSection`, `selectedLemma`, both refresh ticks → background fetch responds to navigation + mutation side effects

## 6. App-shell test coverage map (`frontend/src/test/app/app-shell-*.test.tsx`)

### `app-shell-search-basics.test.tsx`

Shell baseline render, sidebar nav presence, command dialog open + mixed results, saved lemma eye icon, wordbank API search fallback/ minimal-query behavior

### `app-shell-search-actions.test.tsx`

COR grouped variants + add actions, post-add section/open behavior + metadata, local COR debounce + cache, opening saved snapshot word page before detail reload

### `app-shell-search-errors.test.tsx`

Translation failure degradation (untranslated COR shown), network failure on add, API error propagation on add

### `app-shell-search-ranking-order.test.tsx`

Exact-form homograph add-action ordering, opening selected saved meaning, saved row consistency, exact-query gating for saved-prefix, priority: saved exact above add-variation

### `app-shell-search-ranking-results.test.tsx`

Second-line suppression without gloss, retaining alternative adds with exact saved forms, saved-variation eye with alternatives, hiding only saved COR id while keeping homonym alternatives

### `app-shell-search-ranking-selection.test.tsx`

Selection ordering: exact-lemma open vs linked variation, existing-lemma variation priority vs COR options, exact-query gating for saved lemmas with non-legacy badges

### `app-shell-search-ranking-state.test.tsx`

Added result visibility/selection across exact-query transitions, command selection reset to first result on new search

### Coverage gap note

Tests emphasize sidebar command search ranking/actions/resilience. Mobile sidebar trigger and explicit breadcrumb click-back not directly asserted; covered by implementation coupling in `App.tsx`, `AppBreadcrumb`, shared sidebar primitives.
