# Playground section behavior

This document describes runtime behavior for the playground section UI, including the editor, token/phrase popovers, and save dialog.

## 1) Entry points and ownership

### Main composition path

- `useAppController` is the top-level assembly point for playground state and handlers. It combines:
  - `useAppFoundation` (shared app state/services),
  - `usePlaygroundComposition` (popover + note workspace state),
  - `useWordbankComposition` (word/sentence save actions),
  - then passes everything through `buildPlaygroundProps` to section props. (`frontend/src/app/hooks/app/use-app-controller.ts`, `frontend/src/app/hooks/app/controller/use-playground-composition.ts`, `frontend/src/app/hooks/app/controller/build-playground-props.ts`)
- `PlaygroundSection` is intentionally thin and renders the three playground UI subcomponents plus `NotesEditor`.

### UI ownership

- `frontend/src/app/sections/playground-section.tsx`
  - Renders:
    - `PlaygroundSaveDialog`
    - `PlaygroundPhrasePopover`
    - `PlaygroundHighlightPopover`
    - `NotesEditor`
  - Displays character count (`noteText.length`) and section-level analysis error text.
- `frontend/src/app/sections/playground/playground-highlight-popover.tsx`
  - Pure rendering for token popover body + action buttons.
- `frontend/src/app/sections/playground/playground-phrase-popover.tsx`
  - Pure rendering for selected phrase popover + sentencebank action.
- `frontend/src/app/sections/playground/playground-save-dialog.tsx`
  - Save/create note dialog UI and submit/cancel wiring.
- `frontend/src/components/notes-editor.tsx`
  - Tiptap editor lifecycle, text synchronization, highlight click handling, delayed selection-settle callback.

### Relevant controller/hooks in `frontend/src/app/hooks/app/*`

- `controller/use-app-foundation.ts`: owns `noteText`, analysis hook, lexicon/notes/navigation/notifications bootstrapping.
- `controller/use-playground-composition.ts`: binds playground popovers (`usePlaygroundPopovers`) with note workspace (`useNoteWorkspace`).
- `controller/build-playground-props.ts`: adapts composed hooks to `PlaygroundSectionProps`, including wrapper handlers (open wordbank, add token, add sentence, editor change/selection).
- `use-app-controller.ts`: final prop wiring into section.

## 2) Analysis lifecycle

### Debounce timing

- Analyze request debounces by `ANALYZE_DEBOUNCE_MS = 450` ms.
- Input is preprocessed with `finalizedAnalysisText()`:
  - trailing whitespace means “token is complete”, so text is analyzed,
  - without trailing whitespace, trailing in-progress word is dropped.

### Abort/cancel and stale-request rules

- `useAnalysis` keeps:
  - `activeControllerRef` for aborting the in-flight `/api/analyze` request,
  - `latestRequestIdRef` to guard against out-of-order responses.
- Before each new analyze request, previous controller is aborted.
- Only the response whose `requestId` matches `latestRequestIdRef.current` updates tokens/error.
- On unmount, active request is aborted.

### Empty-input handling

- When finalized analysis input is empty:
  - current request is aborted,
  - tokens and analysis error are cleared in a queued timeout.

### Loading/error rendering

- There is no dedicated global spinner for `/api/analyze` in playground section.
- On failure, `analysisError` is shown under editor in a destructive alert paragraph.
- On success, `noteHighlights` are recomputed from `noteText + tokens`.

## 3) Highlight interaction rules

### Clickable vs ignored classes

#### Tokens that can produce clickable highlights

- Highlight mapping includes classifications: `known`, `new`, `variation`, `typo_likely`.
- Clicks are only captured from marks matching `mark.clickable-word[data-token-index]`.

#### Tokens that are explicitly ignored for highlighting/popover

- Proper nouns (`pos_tag === "PROPN"`) and numerals (`pos_tag === "NUM"`) are skipped in highlight mapping.
- Even if a highlight exists, `openHighlightPopover` exits early for:
  - `classification === "typo_likely"`
  - `pos_tag === "PROPN"`
  - `pos_tag === "NUM"`

Result: typo_likely/proper-noun/numeral tokens do not open token popovers or trigger token translation calls.

## 4) Token popover actions (add/open)

### Open behavior

- Clicking a highlight calls `openHighlightPopover(tokenIndex, coords...)`.
- Popover anchor side is chosen by viewport heuristic (`preferredPopoverSide`).
- Opening token popover closes phrase popover.
- Token translation generation is requested (`generateTranslationForToken`) unless translation cache already has a non-null value for one of token keys.

### Primary action behavior

- `open_wordbank` action:
  - button uses eye icon, disabled when lemma missing,
  - click closes highlight popover, then navigates to Wordbank lemma.
- Add actions (`add_as_new` / `add_variation`):
  - button uses plus icon,
  - disabled while `addingTokens[addLoadingKey(token)]` is true,
  - click starts async `addTokenToWordbank(...)` and closes popover immediately.

### Optimistic vs post-response updates

- Add-to-wordbank is **not optimistic** for token classification.
- Updates happen after API success:
  - success toast (`payload.message`),
  - verification/pronunciation background jobs kicked off,
  - feedback posted,
  - refresh ticks incremented (`analysis` + `wordbank`) to re-fetch/re-analyze.
- On error:
  - error toast shown,
  - loading key is cleared in `finally`.

### Toast/error semantics

- Success: `toast.success(payload.message)` from backend response.
- Failure: `toast.error(error.message || fallback)`.

## 5) Phrase popover + sentencebank add behavior

### Selection normalization + eligibility

- Editor selection settles after 180 ms stability window (`scheduleSelectionSettled`).
- Selected text is normalized (`\s+` collapse + trim).
- Phrase popover only opens if normalized selection has multiple words (`hasMultipleWords`).
- Single-word or empty selections close phrase popover and reset phrase translation progress.

### Phrase translation behavior

- Phrase translation request starts after `PHRASE_TRANSLATION_DELAY_MS = 1000` ms.
- If phrase key already exists in translation map, no new request is made.
- Delay timer is cleared on reset/unmount.
- Only latest phrase key updates phrase loading/error state guards.

### Sentencebank add + duplicate prevention

- `addSentenceToSentencebank` re-normalizes text before save.
- Save is skipped when:
  - normalized selection is empty/single-word, or
  - normalized selection already exists in current sentence list (keyed by normalized phrase).
- During save: button disabled via `isSavingSentence`.
- Also disabled when `isSelectedPhraseSaved` is true.
- On success:
  - success toast,
  - sentencebank refresh tick increment,
  - optional `onSentenceSaved` callback closes phrase popover (wired in controller composition).
- On failure: error toast.

## 6) Save dialog behavior

### Validation

- Name is trimmed on submit path.
- Empty name -> `toast.error("Note name is required.")` and no save.

### Create/update behavior

- Dialog mode:
  - `initial` (save current note)
  - `create_new` (save current active note silently, then create/activate an empty new note record)
- Duplicate detection is case-insensitive on trimmed name.
- Duplicate in `initial` mode:
  - conflict message shown,
  - user can choose “Overwrite existing” (save using existing note id).
- Duplicate in `create_new` mode:
  - conflict message shown,
  - user can choose “Use existing note” (switch active note for autosave).

### Close/reset rules

- Opening dialog resets mode, pre-fills `noteNameDraft` to `Note N`, clears duplicate conflict.
- Changing dialog input clears duplicate conflict.
- Closing dialog (`onOpenChange(false)` or Cancel) clears duplicate conflict.
- Successful save/create/conflict-resolution closes dialog.

## 7) Keyboard/focus behavior

- Highlight click handler forces Tiptap selection to clicked location, then calls `view.focus()` to keep editor focus.
- Popovers prevent auto-focus stealing via `onOpenAutoFocus={(e) => e.preventDefault()}`.
- Typing in editor routes through `onNoteTextChange`, which clears playground transient state (both popovers + transient translation errors), effectively dismissing open popovers.
- Phrase popover dismissal conditions:
  - selection cleared,
  - selection is not multi-word,
  - external close event.
- Highlight popover dismissal conditions:
  - external close event,
  - note text change,
  - selecting phrase (phrase popover open path closes highlight popover).

## 8) Empty/error states and character count behavior

### Character count

- Playground always renders count as raw `noteText.length` in bottom-right editor overlay.

### Empty states

- Empty editor shows placeholder text: `Type lesson notes here...`.
- Token popover translation fallback when absent: `No translation available.`.
- Phrase popover translation fallback when absent: `No translation available.`.

### Error states

- Section analysis error rendered as alert paragraph under editor.
- Token translation failure renders inline destructive text in token popover.
- Phrase translation failure renders inline destructive text in phrase popover.

## 9) Test coverage map (`frontend/src/test/app/app-playground-*.test.tsx`)

- `app-playground-editor.test.tsx`
  - Editor input behavior, spellcheck/autocorrect attrs,
  - analyze debounce timing,
  - trailing-token finalization behavior,
  - stale analyze response protection,
  - highlight rendering classes, line-start token coverage, hash comment mark behavior.
- `app-playground-popovers-guards.test.tsx`
  - Guards for `typo_likely`, `PROPN`, `NUM` interactions,
  - adjective/AUX metadata rendering in popovers,
  - translation endpoint call expectations for guarded paths.
- `app-playground-popovers-nouns.test.tsx`
  - Noun popover content and lemma subtitle behavior,
  - enrich-cache reuse on reopen,
  - known-token “open in wordbank” flow,
  - noun translation skeleton + duplicate lemma subtitle suppression.
- `app-playground-popovers-verbs.test.tsx`
  - Verb popover metadata labels (including participle mapping),
  - translation reuse when context/POS degrades,
  - popover metadata updates when POS context changes.
- `app-playground-actions.test.tsx`
  - Focus retention when opening popover,
  - popover dismissal on typing,
  - add-to-wordbank success flow (backend call + re-analysis + toast),
  - add-to-wordbank error toast path.

## Documentation parity

- This file is the documentation update for playground behavior details requested in this change.
