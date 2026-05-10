import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  DAYS_OF_WEEK,
  MONTHS,
  SEASONS,
} from "@/app/sections/wordbank/days-months-seasons/days-months-seasons-data"
import {
  BASIC_NUMBER_ROWS,
  ORDINAL_NUMBER_ROWS,
  TENS_NUMBER_ROWS,
} from "@/app/sections/wordbank/numbers/numbers-data"
import {
  DURATION_ROWS,
  FREQUENCY_ROWS,
  RELATIVE_DAY_ROWS,
} from "@/app/sections/wordbank/time-expressions/time-expressions-data"
import {
  PinnedPageLayout,
  PinnedWordGrid,
  type PinnedPageTabId,
  type PinnedWordEntry,
  sentinelForPinnedPageTab,
  usePinnedPageAudio,
} from "@/app/sections/wordbank/_shared"

type Props = {
  defaultTab: PinnedPageTabId
  onOpenWord: (lemma: string) => void
  onOpenTab: (sentinel: string) => void
}

export function WordbankNumbersTimePage({ defaultTab, onOpenWord, onOpenTab }: Props) {
  const audio = usePinnedPageAudio()

  return (
    <PinnedPageLayout title="Numbers & Time">
      <Tabs value={defaultTab} onValueChange={(value) => onOpenTab(sentinelForPinnedPageTab("numbers_time", value as PinnedPageTabId))}>
        <div className="flex flex-col gap-4">
          <TabsList>
            <TabsTrigger value="cardinal_numbers">Cardinal Numbers</TabsTrigger>
            <TabsTrigger value="ordinal_numbers">Ordinal Numbers</TabsTrigger>
            <TabsTrigger value="days">Days</TabsTrigger>
            <TabsTrigger value="months">Months</TabsTrigger>
            <TabsTrigger value="seasons">Seasons</TabsTrigger>
            <TabsTrigger value="time_words">Time Words</TabsTrigger>
          </TabsList>
          <PinnedTab value="cardinal_numbers" entries={cardinalEntries()} audio={audio} onOpenWord={onOpenWord} />
          <PinnedTab value="ordinal_numbers" entries={ordinalEntries()} audio={audio} onOpenWord={onOpenWord} />
          <PinnedTab value="days" entries={calendarEntries(DAYS_OF_WEEK)} audio={audio} onOpenWord={onOpenWord} />
          <PinnedTab value="months" entries={calendarEntries(MONTHS)} audio={audio} onOpenWord={onOpenWord} />
          <PinnedTab value="seasons" entries={calendarEntries(SEASONS)} audio={audio} onOpenWord={onOpenWord} />
          <PinnedTab value="time_words" entries={timeWordEntries()} audio={audio} onOpenWord={onOpenWord} />
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
      />
    </TabsContent>
  )
}

function cardinalEntries(): PinnedWordEntry[] {
  return [...BASIC_NUMBER_ROWS, ...TENS_NUMBER_ROWS].map((row) => ({
    lemma: row.word,
    translation: String(row.number),
    posTag: "NUM",
  }))
}

function ordinalEntries(): PinnedWordEntry[] {
  return ORDINAL_NUMBER_ROWS.map((row) => ({
    lemma: row.ordinal,
    translation: row.english,
    description: String(row.number),
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

function timeWordEntries(): PinnedWordEntry[] {
  return [...RELATIVE_DAY_ROWS, ...DURATION_ROWS, ...FREQUENCY_ROWS]
    .filter((row) => !row.lemma.includes(" ") && !row.lemma.includes("…"))
    .map((row) => ({
      lemma: row.lemma,
      translation: row.english,
      posTag: ["altid", "ofte", "sjældent", "aldrig"].includes(row.lemma) ? "ADV" : "ADP",
    }))
}
