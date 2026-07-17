import {
  CalendarDays,
  ChevronRight,
  CircleHelp,
  Link2,
  Signpost,
  Users,
} from "lucide-react"

import type {
  PinnedPageId,
  PinnedPageMeta,
} from "@/app/sections/wordbank/_shared/pinned-pages-registry"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

type ReferenceDeckVisual = {
  description: string
}

const REFERENCE_DECK_VISUALS: Record<PinnedPageId, ReferenceDeckVisual> = {
  pronouns: {
    description: "People and pointing words",
  },
  hv_questions: {
    description: "Danish question words",
  },
  prepositions: {
    description: "Place and relation words",
  },
  conjunctions: {
    description: "Connecting words",
  },
  numbers_time: {
    description: "Counting and calendar words",
  },
}

export function WordbankReferenceDecks({
  pages,
  onSelectLemma,
}: {
  pages: PinnedPageMeta[]
  onSelectLemma: (lemma: string) => void
}) {
  return (
    <section className="flex flex-col gap-2" aria-labelledby="wordbank-reference-heading">
      <h2
        id="wordbank-reference-heading"
        className="text-muted-foreground text-xs font-semibold tracking-wide uppercase"
      >
        Reference collections
      </h2>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(10rem,1fr))] gap-3 pb-1 pr-1">
        {pages.map((page) => (
          <ReferenceDeck key={page.sentinel} page={page} onClick={() => onSelectLemma(page.sentinel)} />
        ))}
      </div>
    </section>
  )
}

function ReferenceDeck({ page, onClick }: { page: PinnedPageMeta; onClick: () => void }) {
  const visual = REFERENCE_DECK_VISUALS[page.id]

  return (
    <Card className="gap-0 overflow-hidden py-0">
      <CardContent className="p-0">
        <Button
          type="button"
          variant="ghost"
          className="h-auto min-h-20 w-full justify-start rounded-none px-4 py-3 text-left whitespace-normal"
          aria-label={`Open ${page.title} reference`}
          onClick={onClick}
        >
          <ReferenceDeckIcon pageId={page.id} />
          <span className="flex min-w-0 flex-1 flex-col items-start gap-1">
            <span className="font-semibold">{page.title}</span>
            <span className="text-muted-foreground text-xs leading-tight">{visual.description}</span>
          </span>
          <ChevronRight data-icon="inline-end" aria-hidden="true" className="text-muted-foreground" />
        </Button>
      </CardContent>
    </Card>
  )
}

function ReferenceDeckIcon({ pageId }: { pageId: PinnedPageId }) {
  const props = {
    "data-icon": "inline-start" as const,
    "aria-hidden": true,
    className: "text-muted-foreground",
  }
  if (pageId === "pronouns") return <Users {...props} />
  if (pageId === "hv_questions") return <CircleHelp {...props} />
  if (pageId === "prepositions") return <Signpost {...props} />
  if (pageId === "conjunctions") return <Link2 {...props} />
  return <CalendarDays {...props} />
}
