# Sentencebank Sentence Page

**Date:** 2026-04-11  
**Status:** Approved

## Summary

Add a sentence detail page to the sentencebank section. Clicking a sentence in the list navigates to the sentence page, which shows the word token cards. The list no longer shows token cards inline. In the wordbank word page, clicking a linked sentence navigates to the sentencebank section and opens its sentence page.

## Navigation Layer

### Changes to `useSectionNavigation`

Add `selectedSentenceId: number | null` (initialized `null`) alongside existing `selectedLemma`.

New actions:
- `openSentence(id: number)` — sets `activeSection` to `"sentencebank"`, sets `selectedSentenceId` to `id`, clears `selectedLemma` and `selectedMeaningId`
- `selectSentencebank()` — already clears lemma/meaningId; also clears `selectedSentenceId`
- `selectWordbank()`, `selectPlayground()`, `selectNotes()`, `selectDeveloper()` — clear `selectedSentenceId`
- `openWordbankLemma()`, `openWordbankMeaning()`, `openWordbankRoot()` — clear `selectedSentenceId`

`openSentence` is exposed from `useAppController` → `App.tsx`.

## Components

### `SentencebankSection` (modified)

New props: `selectedSentenceId: number | null`, `onOpenSentence: (id: number) => void`.

Switch logic:
- `selectedSentenceId !== null` → render `SentencebankSentencePage`
- otherwise → render `SentencebankListView`

### `sentencebank/sentencebank-list-view.tsx` (new)

Extracted from current `sentencebank-section.tsx` list rendering. Changes:
- Each sentence `Card` is wrapped in a `button` (or given `onClick`) that calls `onOpenSentence(sentence.id)`
- Token card grid removed entirely
- Skeleton and empty states stay here

### `sentencebank/sentencebank-sentence-page.tsx` (new)

Props: `sentence: SentencebankSentence`, `onOpenWordbankLemma`, `onOpenWordbankMeaning`.

Looks up sentence from already-loaded `sentences` array by `selectedSentenceId` in the section component — passes it down as `sentence`. Shows a "not found" fallback if id has no match.

Renders:
- Sentence text + translation (same style as list cards)
- Token card grid (`SentenceTokenButton` instances, moved from list view)

`SentenceTokenButton` moves to a shared file (`sentencebank/sentencebank-token-button.tsx`) so both page and any future views can import it cleanly.

### `WordbankLinkedSentences` (modified)

New optional prop: `onOpenSentence?: (id: number) => void`.

When provided, each sentence card becomes clickable (button wrapper or `onClick`) and calls `onOpenSentence(sentence.id)`. When absent, cards remain static (backwards-compatible).

### `WordbankWordPage` (modified)

New optional prop: `onOpenSentence?: (id: number) => void`. Passed through to `WordbankLinkedSentences`.

## Data Flow

```
useSectionNavigation
  selectedSentenceId, openSentence
    → useAppFoundation (navigation)
      → use-app-controller
        → App.tsx (exposes openSentence)
        → buildSentencebankSectionProps (passes selectedSentenceId, onOpenSentence)
        → buildWordbankSectionProps (passes onOpenSentence)
```

No new fetch. Sentence page uses the `sentences` array already loaded by `useLexiconData`. Lookup is `sentences.find(s => s.id === selectedSentenceId)`.

## Breadcrumb

No change required. The breadcrumb already shows "Sentencebank" when `activeSection === "sentencebank"`. The sentence page lives within that section — no additional breadcrumb level needed.

## Prop Adapter Changes

### `sentencebank-section-props.ts`

`SentencebankSectionAdapterArgs` gains:
- `selectedSentenceId: number | null`
- `openSentence: (id: number) => void`

`buildSentencebankSectionProps` maps them to `onOpenSentence` and `selectedSentenceId`.

### `wordbank-section-props.ts`

`WordbankSectionAdapterArgs` gains:
- `openSentence?: (id: number) => void`

`buildWordbankSectionProps` maps it to `onOpenSentence`.

## File Structure

```
frontend/src/app/sections/
  sentencebank-section.tsx          (modified — switch logic only)
  sentencebank-section-props.ts     (modified — new props)
  wordbank-section-props.ts         (modified — new prop)
  sentencebank/
    sentencebank-list-view.tsx      (new — extracted list)
    sentencebank-sentence-page.tsx  (new — sentence detail)
    sentencebank-token-button.tsx   (new — extracted SentenceTokenButton)
  wordbank/
    wordbank-linked-sentences.tsx   (modified — optional onOpenSentence)
    wordbank-word-page.tsx          (modified — optional onOpenSentence)

frontend/src/app/hooks/app/
  use-section-navigation.ts         (modified — selectedSentenceId, openSentence)
```

## Testing

- `app-sentencebank.test.tsx` — add: click sentence → sentence page renders tokens; clicking sentence in word page linked sentences navigates to sentencebank sentence page
- `section-props-adapters.test.ts` — update sentencebank adapter test for new props; add wordbank adapter test for openSentence
- `app-wordbank-details.test.tsx` — add: linked sentence click triggers openSentence
