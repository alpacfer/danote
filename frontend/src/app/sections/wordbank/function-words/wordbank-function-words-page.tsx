import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ARTICLE_ROWS } from "@/app/sections/wordbank/articles-gender/articles-gender-data"
import {
  COORDINATING_CONJUNCTION_ROWS,
  SUBORDINATING_CONJUNCTION_ROWS,
} from "@/app/sections/wordbank/conjunctions/conjunctions-data"
import { PREPOSITION_ROWS } from "@/app/sections/wordbank/prepositions/prepositions-data"
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

export function WordbankFunctionWordsPage({ defaultTab, onOpenWord, onOpenTab }: Props) {
  const audio = usePinnedPageAudio()

  return (
    <PinnedPageLayout title="Function Words">
      <Tabs value={defaultTab} onValueChange={(value) => onOpenTab(sentinelForPinnedPageTab("function_words", value as PinnedPageTabId))}>
        <div className="flex flex-col gap-4">
          <TabsList>
            <TabsTrigger value="articles">Articles</TabsTrigger>
            <TabsTrigger value="prepositions">Prepositions</TabsTrigger>
            <TabsTrigger value="conjunctions">Conjunctions</TabsTrigger>
          </TabsList>
          <PinnedTab value="articles" entries={articleEntries()} audio={audio} onOpenWord={onOpenWord} />
          <PinnedTab value="prepositions" entries={prepositionEntries()} audio={audio} onOpenWord={onOpenWord} />
          <PinnedTab value="conjunctions" entries={conjunctionEntries()} audio={audio} onOpenWord={onOpenWord} />
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

function articleEntries(): PinnedWordEntry[] {
  return ARTICLE_ROWS.map((row) => ({
    lemma: row.lemma,
    translation: row.english,
    description: row.description,
    playForm: row.playForm,
    posTag: "DET",
    morphology: row.lemma === "-en"
      ? "Gender=Com|Number=Sing"
      : row.lemma === "-et"
        ? "Gender=Neut|Number=Sing"
        : row.lemma === "-ne"
          ? "Number=Plur"
          : row.lemma === "en"
            ? "Gender=Com|Number=Sing"
            : "Gender=Neut|Number=Sing",
  }))
}

function prepositionEntries(): PinnedWordEntry[] {
  return PREPOSITION_ROWS.map((row) => ({
    lemma: row.lemma,
    translation: row.translation,
    posTag: "ADP",
  }))
}

function conjunctionEntries(): PinnedWordEntry[] {
  return [...COORDINATING_CONJUNCTION_ROWS, ...SUBORDINATING_CONJUNCTION_ROWS].map((row) => ({
    lemma: row.lemma,
    translation: row.translation,
    posTag: ["og", "eller", "men", "for", "så"].includes(row.lemma) ? "CCONJ" : "SCONJ",
  }))
}
