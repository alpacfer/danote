import { Tabs, TabsContent, TabsTrigger } from "@/components/ui/tabs"
import {
  DEMONSTRATIVE_ROWS,
  INDEFINITE_PRONOUN_ROWS,
  PERSONAL_PRONOUN_ROWS,
  POSSESSIVE_PRONOUN_ROWS,
  RELATIVE_PRONOUN_ROWS,
  pronounTranslation,
} from "@/app/sections/wordbank/pronouns/pronouns-data"
import {
  PinnedPageLayout,
  PinnedTabsList,
  PinnedWordGrid,
  type PinnedPageTabId,
  type PinnedWordEntry,
  hiddenBadgesForPinnedTab,
  sentinelForPinnedPageTab,
} from "@/app/sections/wordbank/_shared"

type Props = {
  defaultTab: PinnedPageTabId
  onOpenWord: (lemma: string) => void
  onOpenTab: (sentinel: string) => void
}

export function WordbankPronounsPage({ defaultTab, onOpenWord, onOpenTab }: Props) {
  return (
    <PinnedPageLayout title="Pronouns">
      <Tabs className="min-w-0" value={defaultTab} onValueChange={(value) => onOpenTab(sentinelForPinnedPageTab("pronouns", value as PinnedPageTabId))}>
        <div className="flex min-w-0 flex-col gap-4">
          <PinnedTabsList activeTab={defaultTab} ariaLabel="Pronoun categories">
            <TabsTrigger value="personal">Personal</TabsTrigger>
            <TabsTrigger value="possessive">Possessive</TabsTrigger>
            <TabsTrigger value="demonstrative">Demonstrative</TabsTrigger>
            <TabsTrigger value="relative">Relative</TabsTrigger>
            <TabsTrigger value="indefinite">Indefinite</TabsTrigger>
          </PinnedTabsList>
          <PinnedTab value="personal" entries={personalEntries()} onOpenWord={onOpenWord} />
          <PinnedTab value="possessive" entries={possessiveEntries()} onOpenWord={onOpenWord} />
          <PinnedTab value="demonstrative" entries={demonstrativeEntries()} onOpenWord={onOpenWord} />
          <PinnedTab value="relative" entries={relativeEntries()} onOpenWord={onOpenWord} />
          <PinnedTab value="indefinite" entries={indefiniteEntries()} onOpenWord={onOpenWord} />
        </div>
      </Tabs>
    </PinnedPageLayout>
  )
}

function PinnedTab({
  value,
  entries,
  onOpenWord,
}: {
  value: PinnedPageTabId
  entries: PinnedWordEntry[]
  onOpenWord: (lemma: string) => void
}) {
  return (
    <TabsContent value={value}>
      <PinnedWordGrid
        entries={entries}
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
