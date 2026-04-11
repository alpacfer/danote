# Sentencebank Sentence Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add sentence detail page: clicking sentence in list → page with token cards; clicking linked sentence in word page → sentencebank sentence page.

**Architecture:** Mirror wordbank pattern. Add `selectedSentenceId` to navigation. `SentencebankSection` switches on it. Extract token button + list view + sentence page into `sentencebank/` subfolder. Wordbank components get optional `onOpenSentence` prop. No new fetches — sentence page looks up from already-loaded `sentences` array.

**Tech Stack:** React 19, TypeScript, Tailwind CSS v4, shadcn/ui, Vitest + RTL

---

## File Map

| Action | Path |
|--------|------|
| Modify | `frontend/src/app/hooks/app/use-section-navigation.ts` |
| Create | `frontend/src/app/sections/sentencebank/sentencebank-token-button.tsx` |
| Create | `frontend/src/app/sections/sentencebank/sentencebank-list-view.tsx` |
| Create | `frontend/src/app/sections/sentencebank/sentencebank-sentence-page.tsx` |
| Modify | `frontend/src/app/sections/sentencebank-section.tsx` |
| Modify | `frontend/src/app/sections/sentencebank-section-props.ts` |
| Modify | `frontend/src/app/sections/wordbank/wordbank-section-types.ts` |
| Modify | `frontend/src/app/sections/wordbank/wordbank-linked-sentences.tsx` |
| Modify | `frontend/src/app/sections/wordbank/wordbank-word-page.tsx` |
| Modify | `frontend/src/app/sections/wordbank-section-props.ts` |
| Modify | `frontend/src/app/hooks/app/use-app-controller.ts` |
| Modify | `frontend/src/App.tsx` |
| Modify | `frontend/src/app/sections/section-props-adapters.test.ts` |
| Modify | `frontend/src/test/app/app-sentencebank.test.tsx` |
| Modify | `frontend/src/test/app/app-wordbank-details.test.tsx` |

---

## Task 1: Navigation — add `selectedSentenceId` + `openSentence`

**Files:**
- Modify: `frontend/src/app/hooks/app/use-section-navigation.ts`

- [ ] **Step 1: Add state + new actions**

Replace full file content:

```ts
import { useState } from "react"

import { type AppSection } from "@/app/core"

export function useSectionNavigation() {
  const [activeSection, setActiveSection] = useState<AppSection>("playground")
  const [selectedLemma, setSelectedLemma] = useState<string | null>(null)
  const [selectedMeaningId, setSelectedMeaningId] = useState<number | null>(null)
  const [selectedSentenceId, setSelectedSentenceId] = useState<number | null>(null)

  return {
    activeSection,
    selectedLemma,
    selectedMeaningId,
    selectedSentenceId,
    setActiveSection,
    setSelectedLemma,
    setSelectedMeaningId,
    setSelectedSentenceId,
    selectPlayground: () => {
      setActiveSection("playground")
      setSelectedMeaningId(null)
      setSelectedSentenceId(null)
    },
    selectNotes: () => {
      setActiveSection("notes")
      setSelectedLemma(null)
      setSelectedMeaningId(null)
      setSelectedSentenceId(null)
    },
    selectWordbank: () => {
      setActiveSection("wordbank")
      setSelectedLemma(null)
      setSelectedMeaningId(null)
      setSelectedSentenceId(null)
    },
    selectSentencebank: () => {
      setActiveSection("sentencebank")
      setSelectedLemma(null)
      setSelectedMeaningId(null)
      setSelectedSentenceId(null)
    },
    selectDeveloper: () => {
      setActiveSection("developer")
      setSelectedLemma(null)
      setSelectedMeaningId(null)
      setSelectedSentenceId(null)
    },
    openWordbankLemma: (lemma: string) => {
      setActiveSection("wordbank")
      setSelectedLemma(lemma)
      setSelectedMeaningId(null)
      setSelectedSentenceId(null)
    },
    openWordbankMeaning: (lemma: string, meaningId: number) => {
      setActiveSection("wordbank")
      setSelectedLemma(lemma)
      setSelectedMeaningId(meaningId)
      setSelectedSentenceId(null)
    },
    openWordbankRoot: () => {
      setActiveSection("wordbank")
      setSelectedLemma(null)
      setSelectedMeaningId(null)
      setSelectedSentenceId(null)
    },
    openSentence: (id: number) => {
      setActiveSection("sentencebank")
      setSelectedSentenceId(id)
      setSelectedLemma(null)
      setSelectedMeaningId(null)
    },
  }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors from this file (other files will have errors until later tasks complete — that's fine at this stage).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/hooks/app/use-section-navigation.ts
git commit -m "feat(nav): add selectedSentenceId and openSentence to section navigation"
```

---

## Task 2: Extract `SentenceTokenButton`

**Files:**
- Create: `frontend/src/app/sections/sentencebank/sentencebank-token-button.tsx`

No behavior change. Pure extraction so list view and sentence page share it.

- [ ] **Step 1: Create token button file**

```tsx
import {
  badgesForSavedForm,
  lemmaDisplayForSavedForm,
  lemmaTranslationWithGloss,
  posBadgeClass,
  type SentenceTokenCard,
} from "@/app/core"
import { Badge } from "@/components/ui/badge"

type SentencebankTokenButtonProps = {
  token: SentenceTokenCard
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
}

export function SentencebankTokenButton({
  token,
  onOpenWordbankLemma,
  onOpenWordbankMeaning,
}: SentencebankTokenButtonProps) {
  const lemmaDisplay = lemmaDisplayForSavedForm({
    form: token.surface_form,
    lemma: token.stored_lemma,
    pos_tag: token.pos_tag,
  })
  const translationLine = lemmaTranslationWithGloss(
    token.english_translation,
    token.gloss_translation,
  )
  const badges = badgesForSavedForm({
    pos_tag: token.pos_tag,
    morphology: token.morphology,
  })

  return (
    <button
      type="button"
      className="bg-muted/35 hover:bg-accent/60 rounded-xl border px-3 py-2 text-left transition-colors"
      onClick={() => {
        if (typeof token.meaning_id === "number") {
          onOpenWordbankMeaning(token.stored_lemma, token.meaning_id)
          return
        }
        onOpenWordbankLemma(token.stored_lemma)
      }}
    >
      <div className="space-y-1">
        <p className="font-semibold break-words">{token.surface_form}</p>
        {lemmaDisplay && lemmaDisplay.toLocaleLowerCase("da-DK") !== token.surface_form.toLocaleLowerCase("da-DK") ? (
          <p className="text-muted-foreground text-xs break-words">from {lemmaDisplay}</p>
        ) : null}
        {translationLine ? (
          <p className="text-muted-foreground text-xs break-words">{translationLine}</p>
        ) : null}
        {badges.length > 0 ? (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {badges.map((badge) => (
              <Badge
                key={`sentence-token-${token.token_index}-${badge.label}`}
                variant={badge.tone === "primary" ? "outline" : "secondary"}
                className={`text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(token.pos_tag ?? null)}` : ""}`.trim()}
              >
                {badge.label}
              </Badge>
            ))}
          </div>
        ) : null}
      </div>
    </button>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/sections/sentencebank/sentencebank-token-button.tsx
git commit -m "refactor(sentencebank): extract SentencebankTokenButton to shared file"
```

---

## Task 3: Create `SentencebankListView`

**Files:**
- Create: `frontend/src/app/sections/sentencebank/sentencebank-list-view.tsx`

Clickable sentence cards. No token grid. Skeleton + empty state stay here.

- [ ] **Step 1: Create list view file**

```tsx
import { type SentencebankSentence } from "@/app/core"
import { Card, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"

type SentencebankListViewProps = {
  sentencebankError: string | null
  isSentencebankLoading: boolean
  sentences: SentencebankSentence[]
  onOpenSentence: (id: number) => void
}

export function SentencebankListView({
  sentencebankError,
  isSentencebankLoading,
  sentences,
  onOpenSentence,
}: SentencebankListViewProps) {
  if (sentencebankError) {
    return (
      <p className="text-destructive text-sm" role="alert">
        {sentencebankError}
      </p>
    )
  }

  if (isSentencebankLoading && sentences.length === 0) {
    return (
      <div className="space-y-3">
        <Card>
          <CardContent className="space-y-2">
            <Skeleton className="h-5 w-48" />
            <Skeleton className="h-4 w-32" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="space-y-2">
            <Skeleton className="h-5 w-56" />
            <Skeleton className="h-4 w-36" />
          </CardContent>
        </Card>
      </div>
    )
  }

  if (sentences.length === 0) {
    return <p className="text-muted-foreground text-sm">No saved sentences yet. Select a sentence in Playground to add one.</p>
  }

  return (
    <ScrollArea className="min-h-0 flex-1">
      <div className="space-y-3 pr-1">
        {sentences.map((sentence) => (
          <button
            key={sentence.id}
            type="button"
            className="w-full text-left"
            onClick={() => onOpenSentence(sentence.id)}
          >
            <Card className="hover:bg-accent/40 transition-colors cursor-pointer">
              <CardContent className="space-y-2">
                <p className="text-base font-medium leading-relaxed max-w-[70ch] break-words">{sentence.source_text}</p>
                <p className="text-muted-foreground text-sm max-w-[70ch] break-words">
                  {sentence.english_translation?.trim() || "No translation available."}
                </p>
              </CardContent>
            </Card>
          </button>
        ))}
      </div>
    </ScrollArea>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/sections/sentencebank/sentencebank-list-view.tsx
git commit -m "feat(sentencebank): add SentencebankListView with clickable sentence cards"
```

---

## Task 4: Create `SentencebankSentencePage`

**Files:**
- Create: `frontend/src/app/sections/sentencebank/sentencebank-sentence-page.tsx`

Shows sentence text + translation + token card grid.

- [ ] **Step 1: Create sentence page file**

```tsx
import { type SentencebankSentence } from "@/app/core"
import { ScrollArea } from "@/components/ui/scroll-area"
import { SentencebankTokenButton } from "@/app/sections/sentencebank/sentencebank-token-button"

type SentencebankSentencePageProps = {
  sentence: SentencebankSentence | null
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
}

export function SentencebankSentencePage({
  sentence,
  onOpenWordbankLemma,
  onOpenWordbankMeaning,
}: SentencebankSentencePageProps) {
  if (!sentence) {
    return <p className="text-muted-foreground text-sm">Sentence not found.</p>
  }

  return (
    <ScrollArea className="min-h-0 flex-1">
      <div className="space-y-4 pr-1">
        <div className="space-y-1">
          <p className="text-base font-medium leading-relaxed max-w-[70ch] break-words">{sentence.source_text}</p>
          <p className="text-muted-foreground text-sm max-w-[70ch] break-words">
            {sentence.english_translation?.trim() || "No translation available."}
          </p>
        </div>
        {(sentence.tokens?.length ?? 0) > 0 ? (
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {(sentence.tokens ?? []).map((token) => (
              <SentencebankTokenButton
                key={`sentence-${sentence.id}-token-${token.token_index}-${token.surface_form}`}
                token={token}
                onOpenWordbankLemma={onOpenWordbankLemma}
                onOpenWordbankMeaning={onOpenWordbankMeaning}
              />
            ))}
          </div>
        ) : null}
      </div>
    </ScrollArea>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/sections/sentencebank/sentencebank-sentence-page.tsx
git commit -m "feat(sentencebank): add SentencebankSentencePage with token card grid"
```

---

## Task 5: Update `SentencebankSection`

**Files:**
- Modify: `frontend/src/app/sections/sentencebank-section.tsx`

Add `selectedSentenceId` + `onOpenSentence` props. Switch on `selectedSentenceId`. Remove inline token rendering (delegated to child files). Remove `SentenceTokenButton` (moved to `sentencebank-token-button.tsx`).

- [ ] **Step 1: Replace sentencebank-section.tsx**

```tsx
import { type SentencebankSentence } from "@/app/core"
import { SentencebankListView } from "@/app/sections/sentencebank/sentencebank-list-view"
import { SentencebankSentencePage } from "@/app/sections/sentencebank/sentencebank-sentence-page"

export type SentencebankSectionProps = {
  sentencebankError: string | null
  isSentencebankLoading: boolean
  sentences: SentencebankSentence[]
  selectedSentenceId: number | null
  onOpenSentence: (id: number) => void
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
}

export function SentencebankSection({
  sentencebankError,
  isSentencebankLoading,
  sentences,
  selectedSentenceId,
  onOpenSentence,
  onOpenWordbankLemma,
  onOpenWordbankMeaning,
}: SentencebankSectionProps) {
  if (selectedSentenceId !== null) {
    const sentence = sentences.find((s) => s.id === selectedSentenceId) ?? null
    return (
      <SentencebankSentencePage
        sentence={sentence}
        onOpenWordbankLemma={onOpenWordbankLemma}
        onOpenWordbankMeaning={onOpenWordbankMeaning}
      />
    )
  }

  return (
    <SentencebankListView
      sentencebankError={sentencebankError}
      isSentencebankLoading={isSentencebankLoading}
      sentences={sentences}
      onOpenSentence={onOpenSentence}
    />
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/sections/sentencebank-section.tsx
git commit -m "feat(sentencebank): switch section on selectedSentenceId"
```

---

## Task 6: Update sentencebank adapter (TDD)

**Files:**
- Modify: `frontend/src/app/sections/sentencebank-section-props.ts`
- Modify: `frontend/src/app/sections/section-props-adapters.test.ts`

- [ ] **Step 1: Write failing test**

In `frontend/src/app/sections/section-props-adapters.test.ts`, replace the existing `"maps sentencebank props without alteration"` test:

```ts
it("maps sentencebank props without alteration", () => {
  const sentences = [{ id: 1, source_text: "Hej", english_translation: "Hi" }]
  const openWordbankLemma = vi.fn()
  const openWordbankMeaning = vi.fn()
  const openSentence = vi.fn()

  const result = buildSentencebankSectionProps({
    sentencebankError: null,
    isSentencebankLoading: false,
    sentences: sentences as never,
    openWordbankLemma,
    openWordbankMeaning,
    selectedSentenceId: 42,
    openSentence,
  })

  expect(result).toEqual({
    sentencebankError: null,
    isSentencebankLoading: false,
    sentences,
    onOpenWordbankLemma: openWordbankLemma,
    onOpenWordbankMeaning: openWordbankMeaning,
    selectedSentenceId: 42,
    onOpenSentence: openSentence,
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd frontend && npx vitest run src/app/sections/section-props-adapters.test.ts 2>&1 | tail -20
```

Expected: fails — `selectedSentenceId`/`openSentence` not in adapter args yet.

- [ ] **Step 3: Update adapter**

Replace `frontend/src/app/sections/sentencebank-section-props.ts`:

```ts
import { type ComponentProps } from "react"

import { SentencebankSection } from "@/app/sections/sentencebank-section"

export type SentencebankSectionAdapterArgs = {
  sentencebankError: ComponentProps<typeof SentencebankSection>["sentencebankError"]
  isSentencebankLoading: ComponentProps<typeof SentencebankSection>["isSentencebankLoading"]
  sentences: ComponentProps<typeof SentencebankSection>["sentences"]
  selectedSentenceId: ComponentProps<typeof SentencebankSection>["selectedSentenceId"]
  openSentence: ComponentProps<typeof SentencebankSection>["onOpenSentence"]
  openWordbankLemma: ComponentProps<typeof SentencebankSection>["onOpenWordbankLemma"]
  openWordbankMeaning: ComponentProps<typeof SentencebankSection>["onOpenWordbankMeaning"]
}

export function buildSentencebankSectionProps({
  sentencebankError,
  isSentencebankLoading,
  sentences,
  selectedSentenceId,
  openSentence,
  openWordbankLemma,
  openWordbankMeaning,
}: SentencebankSectionAdapterArgs): ComponentProps<typeof SentencebankSection> {
  return {
    sentencebankError,
    isSentencebankLoading,
    sentences,
    selectedSentenceId,
    onOpenSentence: openSentence,
    onOpenWordbankLemma: openWordbankLemma,
    onOpenWordbankMeaning: openWordbankMeaning,
  }
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
cd frontend && npx vitest run src/app/sections/section-props-adapters.test.ts 2>&1 | tail -20
```

Expected: all tests in file pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/sections/sentencebank-section-props.ts frontend/src/app/sections/section-props-adapters.test.ts
git commit -m "feat(sentencebank): add selectedSentenceId + openSentence to sentencebank adapter"
```

---

## Task 7: Update wordbank components

**Files:**
- Modify: `frontend/src/app/sections/wordbank/wordbank-section-types.ts`
- Modify: `frontend/src/app/sections/wordbank/wordbank-linked-sentences.tsx`
- Modify: `frontend/src/app/sections/wordbank/wordbank-word-page.tsx`

Add optional `onOpenSentence?: (id: number) => void`. Backwards-compatible — absent = static cards.

- [ ] **Step 1: Add prop to WordbankSectionProps**

In `wordbank-section-types.ts`, add at the end of the type (before closing `}`):

```ts
  onOpenSentence?: (id: number) => void
```

- [ ] **Step 2: Update WordbankLinkedSentences**

Replace `frontend/src/app/sections/wordbank/wordbank-linked-sentences.tsx`:

```tsx
import { type LemmaDetailsResponse } from "@/app/core"
import { Card, CardContent } from "@/components/ui/card"

type LinkedSentence = NonNullable<LemmaDetailsResponse["linked_sentences"]>[number]

type WordbankLinkedSentencesProps = {
  linkedSentences: LemmaDetailsResponse["linked_sentences"] | undefined
  onOpenSentence?: (id: number) => void
}

export function WordbankLinkedSentences({
  linkedSentences,
  onOpenSentence,
}: WordbankLinkedSentencesProps) {
  if (!linkedSentences || linkedSentences.length === 0) {
    return null
  }

  return (
    <section className="space-y-4 pt-2" aria-labelledby="wordbank-linked-sentences-heading">
      <h2
        id="wordbank-linked-sentences-heading"
        className="text-muted-foreground text-[11px] font-semibold uppercase tracking-wide"
      >
        Sentences
      </h2>
      <div className="space-y-3">
        {linkedSentences.map((sentence: LinkedSentence) => {
          const content = (
            <Card
              key={`linked-sentence-${sentence.id}`}
              className={onOpenSentence ? "hover:bg-accent/40 transition-colors cursor-pointer" : undefined}
            >
              <CardContent className="space-y-1">
                <p className="text-base font-medium leading-relaxed break-words">{sentence.source_text}</p>
                <p className="text-muted-foreground text-sm break-words">
                  {sentence.english_translation?.trim() || "No translation available."}
                </p>
              </CardContent>
            </Card>
          )

          if (onOpenSentence) {
            return (
              <button
                key={`linked-sentence-btn-${sentence.id}`}
                type="button"
                className="w-full text-left"
                onClick={() => onOpenSentence(sentence.id)}
              >
                {content}
              </button>
            )
          }

          return content
        })}
      </div>
    </section>
  )
}
```

- [ ] **Step 3: Update WordbankWordPage**

In `wordbank-word-page.tsx`:

Add `onOpenSentence?: (id: number) => void` to the `WordbankWordPageProps` Pick type — add a line after the last `|` before the closing `>`:

Find the Pick type ending and add:
```ts
  | "onOpenSentence"
```

Then add `onOpenSentence` to destructured props in the function signature, and pass it to `WordbankLinkedSentences`:

Find:
```tsx
          <WordbankLinkedSentences
            linkedSentences={activeLemmaDetails.linked_sentences}
          />
```

Replace with:
```tsx
          <WordbankLinkedSentences
            linkedSentences={activeLemmaDetails.linked_sentences}
            onOpenSentence={onOpenSentence}
          />
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors from wordbank files at this point (adapter not yet updated — errors from controller are ok).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/sections/wordbank/wordbank-section-types.ts frontend/src/app/sections/wordbank/wordbank-linked-sentences.tsx frontend/src/app/sections/wordbank/wordbank-word-page.tsx
git commit -m "feat(wordbank): add optional onOpenSentence to linked sentences + word page"
```

---

## Task 8: Update wordbank adapter (TDD)

**Files:**
- Modify: `frontend/src/app/sections/wordbank-section-props.ts`
- Modify: `frontend/src/app/sections/section-props-adapters.test.ts`

- [ ] **Step 1: Write failing test**

In `section-props-adapters.test.ts`, add to the `"builds wordbank props with safe async wrappers"` test. After `const openRelatedWordTarget = vi.fn()` add:

```ts
const openSentence = vi.fn()
```

Add `openSentence` to the `buildWordbankSectionProps` call (after `openRelatedWordTarget`):

```ts
      openSentence,
```

After existing `expect` calls (after `expect(revertChange).toHaveBeenCalledWith(4)`), add:

```ts
    result.onOpenSentence?.(41)
    expect(openSentence).toHaveBeenCalledWith(41)
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd frontend && npx vitest run src/app/sections/section-props-adapters.test.ts 2>&1 | tail -20
```

Expected: fails — `openSentence` not in adapter args.

- [ ] **Step 3: Update wordbank adapter**

In `frontend/src/app/sections/wordbank-section-props.ts`:

Add to `WordbankSectionAdapterArgs` type (after `openRelatedWordTarget` line):
```ts
  openSentence?: (id: number) => void
```

Add to the return object of `buildWordbankSectionProps` (after `onOpenRelatedWordTarget` line):
```ts
    onOpenSentence: args.openSentence,
```

- [ ] **Step 4: Run test — expect PASS**

```bash
cd frontend && npx vitest run src/app/sections/section-props-adapters.test.ts 2>&1 | tail -20
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/sections/wordbank-section-props.ts frontend/src/app/sections/section-props-adapters.test.ts
git commit -m "feat(wordbank): add openSentence to wordbank adapter"
```

---

## Task 9: Wire app controller + App.tsx

**Files:**
- Modify: `frontend/src/app/hooks/app/use-app-controller.ts`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Wire sentencebank props in use-app-controller.ts**

Find the `sentencebankSectionProps: buildSentencebankSectionProps({` block (lines ~150–156) and update it:

```ts
    sentencebankSectionProps: buildSentencebankSectionProps({
      sentencebankError: lexiconData.sentencebankError,
      isSentencebankLoading: lexiconData.isSentencebankLoading,
      sentences: lexiconData.sentences,
      selectedSentenceId: navigation.selectedSentenceId,
      openSentence: navigation.openSentence,
      openWordbankLemma: navigation.openWordbankLemma,
      openWordbankMeaning: navigation.openWordbankMeaning,
    }),
```

- [ ] **Step 2: Wire wordbank props in use-app-controller.ts**

Find `openRelatedWordTarget: wordbank.openRelatedWordTarget,` in the `wordbankSectionProps` block and add after it:

```ts
      openSentence: navigation.openSentence,
```

- [ ] **Step 3: Expose openSentence from controller return**

In the return object of `useAppController` (after `openWordbankRoot: navigation.openWordbankRoot,`), add:

```ts
    openSentence: navigation.openSentence,
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/hooks/app/use-app-controller.ts
git commit -m "feat: wire openSentence and selectedSentenceId through app controller"
```

---

## Task 10: Update integration tests + run full suite

**Files:**
- Modify: `frontend/src/test/app/app-sentencebank.test.tsx`
- Modify: `frontend/src/test/app/app-wordbank-details.test.tsx`

- [ ] **Step 1: Update app-sentencebank.test.tsx**

Replace the full file:

```tsx
import { fireEvent, mockFetchImplementation, renderApp, screen, within } from "@/test/app-test-helpers"

describe("App sentencebank", () => {
  it("shows saved sentences in sentencebank list (no token cards)", async () => {
    mockFetchImplementation({
      sentencebankResponse: {
        items: [
          {
            id: 1,
            source_text: "Jeg elsker dansk",
            english_translation: "i love danish",
            created_at: "2026-02-28T12:00:00.000Z",
            tokens: [
              {
                token_index: 0,
                surface_form: "Jeg",
                stored_lemma: "jeg",
                lexeme_id: 11,
                meaning_id: null,
                pos_tag: "PRON",
                morphology: "PronType=Prs",
                english_translation: "i",
                gloss_translation: null,
              },
            ],
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /sentencebank/i }))

    expect(await screen.findByText(/jeg elsker dansk/i)).toBeInTheDocument()
    expect(screen.getByText(/i love danish/i)).toBeInTheDocument()
    // token buttons not shown in list
    expect(screen.queryByRole("button", { name: /^jeg$/i })).not.toBeInTheDocument()
  })

  it("clicking sentence in list shows sentence page with token cards", async () => {
    mockFetchImplementation({
      sentencebankResponse: {
        items: [
          {
            id: 1,
            source_text: "Jeg elsker dansk",
            english_translation: "i love danish",
            created_at: "2026-02-28T12:00:00.000Z",
            tokens: [
              {
                token_index: 0,
                surface_form: "Jeg",
                stored_lemma: "jeg",
                lexeme_id: 11,
                meaning_id: null,
                pos_tag: "PRON",
                morphology: "PronType=Prs",
                english_translation: "i",
                gloss_translation: null,
              },
              {
                token_index: 1,
                surface_form: "elsker",
                stored_lemma: "elske",
                lexeme_id: 12,
                meaning_id: 3,
                pos_tag: "VERB",
                morphology: "Tense=Pres|VerbForm=Fin|Voice=Act",
                english_translation: "love",
                gloss_translation: "love",
              },
            ],
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /sentencebank/i }))
    await screen.findByText(/jeg elsker dansk/i)

    // click the sentence card to open sentence page
    fireEvent.click(screen.getByRole("button", { name: /jeg elsker dansk/i }))

    expect(screen.getByRole("button", { name: /jeg/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /elsker/i })).toBeInTheDocument()
  })

  it("clicking token on sentence page opens wordbank word page", async () => {
    mockFetchImplementation({
      sentencebankResponse: {
        items: [
          {
            id: 1,
            source_text: "Jeg elsker dansk",
            english_translation: "i love danish",
            created_at: "2026-02-28T12:00:00.000Z",
            tokens: [
              {
                token_index: 0,
                surface_form: "elsker",
                stored_lemma: "elske",
                lexeme_id: 12,
                meaning_id: 3,
                pos_tag: "VERB",
                morphology: "Tense=Pres|VerbForm=Fin|Voice=Act",
                english_translation: "love",
                gloss_translation: "love",
              },
            ],
          },
        ],
      },
      lemmaDetailsResponse: {
        lemma: "elske",
        english_translation: "love",
        pos_tag: "VERB",
        morphology: "VerbForm=Inf|Voice=Act",
        is_sectioned: true,
        meaning_sections: [
          {
            id: 3,
            meaning_key: "love",
            gloss: "love",
            english_translation: "love",
            pos_tag: "VERB",
            morphology: "VerbForm=Inf|Voice=Act",
            surface_forms: [],
          },
        ],
        surface_forms: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /sentencebank/i }))
    await screen.findByText(/jeg elsker dansk/i)

    // open sentence page first
    fireEvent.click(screen.getByRole("button", { name: /jeg elsker dansk/i }))

    // now click token to go to wordbank
    fireEvent.click(await screen.findByRole("button", { name: /elsker/i }))

    expect(await screen.findByRole("heading", { name: /^elske$/i })).toBeInTheDocument()
    expect(screen.getByText(/^love$/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run sentencebank tests — expect PASS**

```bash
cd frontend && npx vitest run src/test/app/app-sentencebank.test.tsx 2>&1 | tail -20
```

Expected: all 3 tests pass.

- [ ] **Step 3: Add linked-sentence click test to app-wordbank-details.test.tsx**

After the existing `"contract-backed: word page renders linked sentence cards without nested token cards"` test, add:

```ts
  it("contract-backed: clicking linked sentence in word page opens sentencebank sentence page", async () => {
    const linkedSentenceFixture: LemmaDetailsResponse = cloneContractFixture(teacherSectionedWordPageContractFixture)
    linkedSentenceFixture.linked_sentences = [
      {
        id: 41,
        source_text: "Læreren hjælper lærere",
        english_translation: "the teacher helps teachers",
        created_at: "2026-04-10T12:00:00.000Z",
        matched_token_indexes: [0],
        tokens: [
          {
            token_index: 0,
            surface_form: "Læreren",
            stored_lemma: "lærer",
            lexeme_id: 8,
            meaning_id: 1,
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Def",
            gloss: "teacher",
            english_translation: "teacher",
            gloss_translation: "teacher",
          },
        ],
      },
    ]

    mockFetchImplementation({
      sentencebankResponse: {
        items: [
          {
            id: 41,
            source_text: "Læreren hjælper lærere",
            english_translation: "the teacher helps teachers",
            created_at: "2026-04-10T12:00:00.000Z",
            tokens: [
              {
                token_index: 0,
                surface_form: "Læreren",
                stored_lemma: "lærer",
                lexeme_id: 8,
                meaning_id: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Def",
                english_translation: "teacher",
                gloss_translation: "teacher",
              },
            ],
          },
        ],
      },
      lemmasResponse: {
        items: [{ lemma: "lærer", variation_count: 1 }],
      },
      lemmaDetailsResponse: linkedSentenceFixture,
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /lærer/i }))

    expect(await screen.findByRole("heading", { name: /^lærer$/i })).toBeInTheDocument()

    // click linked sentence → navigate to sentencebank sentence page
    fireEvent.click(screen.getByRole("button", { name: /Læreren hjælper lærere/i }))

    // now in sentencebank sentence page
    expect(await screen.findByRole("button", { name: /Læreren/i })).toBeInTheDocument()
  })
```

- [ ] **Step 4: Run wordbank details tests — expect PASS**

```bash
cd frontend && npx vitest run src/test/app/app-wordbank-details.test.tsx 2>&1 | tail -20
```

Expected: all tests pass.

- [ ] **Step 5: Run full frontend test suite**

```bash
cd frontend && npx vitest run 2>&1 | tail -30
```

Expected: all tests pass.

- [ ] **Step 6: Run lint**

```bash
cd frontend && npx eslint src --max-warnings=0 2>&1 | tail -20
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/test/app/app-sentencebank.test.tsx frontend/src/test/app/app-wordbank-details.test.tsx
git commit -m "test: update sentencebank + wordbank tests for sentence page navigation"
```

---

## Final verification

- [ ] Run `make test` from repo root — all tests pass
- [ ] Run `make lint` from repo root — no errors
