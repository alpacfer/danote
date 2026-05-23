import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  QUESTION_WORDS,
  type QuestionWordCategory,
} from "@/app/sections/wordbank/question-words/question-words-data"
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

const TAB_BY_CATEGORY: Record<QuestionWordCategory, PinnedPageTabId> = {
  people_things: "hv_people_things",
  choice: "hv_choice",
  place_time_manner_reason: "hv_place_time_manner",
}

export function WordbankHvQuestionsPage({ defaultTab, onOpenWord, onOpenTab }: Props) {
  return (
    <PinnedPageLayout title="HV Questions">
      <Tabs value={defaultTab} onValueChange={(value) => onOpenTab(sentinelForPinnedPageTab("hv_questions", value as PinnedPageTabId))}>
        <div className="flex flex-col gap-4">
          <TabsList>
            <TabsTrigger value="hv_people_things">People &amp; Things</TabsTrigger>
            <TabsTrigger value="hv_choice">Choice</TabsTrigger>
            <TabsTrigger value="hv_place_time_manner">Place, Time, Manner &amp; Reason</TabsTrigger>
          </TabsList>
          <PinnedTab value="hv_people_things" entries={entriesForCategory("people_things")} onOpenWord={onOpenWord} />
          <PinnedTab value="hv_choice" entries={entriesForCategory("choice")} onOpenWord={onOpenWord} />
          <PinnedTab value="hv_place_time_manner" entries={entriesForCategory("place_time_manner_reason")} onOpenWord={onOpenWord} />
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
        hiddenBadges={hiddenBadgesForPinnedTab("hv_questions", value)}
      />
    </TabsContent>
  )
}

function entriesForCategory(category: QuestionWordCategory): PinnedWordEntry[] {
  return QUESTION_WORDS.filter((entry) => entry.category === category).map((entry) => ({
    lemma: entry.lemma,
    translation: entry.translation,
    posTag: entry.posTag,
    morphology: entry.morphology,
  }))
}

export { TAB_BY_CATEGORY }
