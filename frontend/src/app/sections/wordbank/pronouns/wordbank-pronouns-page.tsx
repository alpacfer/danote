import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  DEMONSTRATIVE_ROWS,
  INDEFINITE_PRONOUN_ROWS,
  PERSONAL_PRONOUN_ROWS,
  POSSESSIVE_PRONOUN_ROWS,
  RELATIVE_PRONOUN_ROWS,
  pronounTranslation,
} from "@/app/sections/wordbank/pronouns/pronouns-data"
import { QUESTION_WORDS } from "@/app/sections/wordbank/question-words/question-words-data"
import {
  PinnedPageLayout,
  PinnedWordGrid,
  type PinnedPageTabId,
  type PinnedWordEntry,
  hiddenBadgesForPinnedTab,
  sentinelForPinnedPageTab,
  usePinnedPageAudio,
} from "@/app/sections/wordbank/_shared"

type Props = {
  defaultTab: PinnedPageTabId
  onOpenWord: (lemma: string) => void
  onOpenTab: (sentinel: string) => void
}

export function WordbankPronounsPage({ defaultTab, onOpenWord, onOpenTab }: Props) {
  const audio = usePinnedPageAudio()

  return (
    <PinnedPageLayout title="Pronouns">
      <Tabs value={defaultTab} onValueChange={(value) => onOpenTab(sentinelForPinnedPageTab("pronouns", value as PinnedPageTabId))}>
        <div className="flex flex-col gap-4">
          <TabsList>
            <TabsTrigger value="personal">Personal</TabsTrigger>
            <TabsTrigger value="possessive">Possessive</TabsTrigger>
            <TabsTrigger value="demonstrative">Demonstrative</TabsTrigger>
            <TabsTrigger value="relative">Relative</TabsTrigger>
            <TabsTrigger value="indefinite">Indefinite</TabsTrigger>
            <TabsTrigger value="question_words">Question Words</TabsTrigger>
          </TabsList>
          <PinnedTab value="personal" entries={personalEntries()} audio={audio} onOpenWord={onOpenWord} />
          <PinnedTab value="possessive" entries={possessiveEntries()} audio={audio} onOpenWord={onOpenWord} />
          <PinnedTab value="demonstrative" entries={demonstrativeEntries()} audio={audio} onOpenWord={onOpenWord} />
          <PinnedTab value="relative" entries={relativeEntries()} audio={audio} onOpenWord={onOpenWord} />
          <PinnedTab value="indefinite" entries={indefiniteEntries()} audio={audio} onOpenWord={onOpenWord} />
          <PinnedTab value="question_words" entries={questionWordEntries()} audio={audio} onOpenWord={onOpenWord} />
        </div>
      </Tabs>
    </PinnedPageLayout>
  )
}

function PinnedTab({
  value,
  entries,
  audio,
  onOpenWord,
}: {
  value: PinnedPageTabId
  entries: PinnedWordEntry[]
  audio: ReturnType<typeof usePinnedPageAudio>
  onOpenWord: (lemma: string) => void
}) {
  return (
    <TabsContent value={value}>
      <PinnedWordGrid
        entries={entries}
        pronunciationLoadingByForm={audio.loadingByForm}
        onPlayPronunciation={audio.playForm}
        onOpenWord={onOpenWord}
        hiddenBadges={hiddenBadgesForPinnedTab("pronouns", value)}
      />
    </TabsContent>
  )
}

function personalEntries(): PinnedWordEntry[] {
  return dedupePinnedEntries(PERSONAL_PRONOUN_ROWS.flatMap((row) => {
    const entries: PinnedWordEntry[] = []
    if (row.nominative) {
      entries.push(toPronounEntry(row.nominative))
    }
    entries.push(toPronounEntry(row.accusative))
    return entries
  }))
}

function possessiveEntries(): PinnedWordEntry[] {
  return POSSESSIVE_PRONOUN_ROWS.flatMap((row) => [
    toPronounEntry(row.common),
    toPronounEntry(row.neuter),
    toPronounEntry(row.plural),
  ])
}

function demonstrativeEntries(): PinnedWordEntry[] {
  return DEMONSTRATIVE_ROWS.flatMap((row) => [
    toPronounEntry(row.common),
    toPronounEntry(row.neuter),
    toPronounEntry(row.plural),
  ])
}

function relativeEntries(): PinnedWordEntry[] {
  return RELATIVE_PRONOUN_ROWS.map((row) => ({
    lemma: row.lemma,
    translation: row.english,
  }))
}

function indefiniteEntries(): PinnedWordEntry[] {
  return INDEFINITE_PRONOUN_ROWS.map((row) => ({
    lemma: row.lemma,
    translation: row.english,
  }))
}

function questionWordEntries(): PinnedWordEntry[] {
  return QUESTION_WORDS.map((entry) => ({
    lemma: entry.lemma,
    translation: entry.translation,
    posTag: entry.posTag,
    morphology: entry.morphology,
  }))
}

function toPronounEntry(lemma: string): PinnedWordEntry {
  return {
    lemma,
    translation: pronounTranslation(lemma) ?? "",
  }
}

function dedupePinnedEntries(entries: PinnedWordEntry[]): PinnedWordEntry[] {
  const seen = new Set<string>()
  return entries.filter((entry) => {
    const key = entry.lemma.trim().toLocaleLowerCase("da-DK")
    if (!key || seen.has(key)) return false
    seen.add(key)
    return true
  })
}
