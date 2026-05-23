import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  DAYS_OF_WEEK,
  MONTHS,
} from "@/app/sections/wordbank/days-months-seasons/days-months-seasons-data"
import {
  BASIC_NUMBER_ROWS,
  ENGLISH_CARDINALS,
  ORDINAL_NUMBER_ROWS,
  TENS_NUMBER_ROWS,
} from "@/app/sections/wordbank/numbers/numbers-data"
import {
  PinnedPageLayout,
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

export function WordbankNumbersTimePage({ defaultTab, onOpenWord, onOpenTab }: Props) {
  return (
    <PinnedPageLayout title="Numbers & Time">
      <Tabs value={defaultTab} onValueChange={(value) => onOpenTab(sentinelForPinnedPageTab("numbers_time", value as PinnedPageTabId))}>
        <div className="flex flex-col gap-4">
          <TabsList>
            <TabsTrigger value="cardinal_numbers">Cardinal Numbers</TabsTrigger>
            <TabsTrigger value="ordinal_numbers">Ordinal Numbers</TabsTrigger>
            <TabsTrigger value="days">Days</TabsTrigger>
            <TabsTrigger value="months">Months</TabsTrigger>
          </TabsList>
          <PinnedTab value="cardinal_numbers" entries={cardinalEntries()} onOpenWord={onOpenWord} />
          <PinnedTab value="ordinal_numbers" entries={ordinalEntries()} onOpenWord={onOpenWord} />
          <PinnedTab value="days" entries={calendarEntries(DAYS_OF_WEEK)} onOpenWord={onOpenWord} />
          <PinnedTab value="months" entries={calendarEntries(MONTHS)} onOpenWord={onOpenWord} />
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
        hiddenBadges={hiddenBadgesForPinnedTab("numbers_time", value)}
      />
    </TabsContent>
  )
}

function cardinalEntries(): PinnedWordEntry[] {
  return [...BASIC_NUMBER_ROWS, ...TENS_NUMBER_ROWS].map((row) => ({
    lemma: row.word,
    translation: ENGLISH_CARDINALS[row.number] ?? String(row.number),
    posTag: "NUM",
  }))
}

function ordinalEntries(): PinnedWordEntry[] {
  return ORDINAL_NUMBER_ROWS.map((row) => ({
    lemma: row.ordinal,
    translation: row.english,
    posTag: row.ordinal === "hundrede" ? "NUM" : "ADJ",
  }))
}

function calendarEntries(rows: Array<{ lemma: string; english: string }>): PinnedWordEntry[] {
  return rows.map((row) => ({
    lemma: row.lemma,
    translation: row.english,
    posTag: "NOUN",
  }))
}
