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
  tone: "sky" | "sea" | "butter" | "plum" | "clay"
}

const REFERENCE_DECK_VISUALS: Record<PinnedPageId, ReferenceDeckVisual> = {
  pronouns: {
    description: "People and pointing words",
    tone: "plum",
  },
  hv_questions: {
    description: "Danish question words",
    tone: "butter",
  },
  prepositions: {
    description: "Place and relation words",
    tone: "sky",
  },
  conjunctions: {
    description: "Connecting words",
    tone: "sea",
  },
  numbers_time: {
    description: "Counting and calendar words",
    tone: "clay",
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
        className="text-muted-foreground flex h-8 items-center text-xs font-semibold tracking-wide uppercase"
      >
        Reference collections
      </h2>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-5" data-grid-anchor="unit" data-reference-drawer>
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
    <Card
      className="h-16 gap-0 overflow-hidden py-0 last:col-span-2 md:last:col-span-1"
      data-material="reference"
      data-material-tone={visual.tone}
      data-grid-anchor="unit"
      data-grid-height="unit"
    >
      <CardContent className="h-full p-0">
        <Button
          type="button"
          variant="ghost"
          className="h-full w-full justify-start rounded-none px-3 py-2 text-left whitespace-normal"
          aria-label={`Open ${page.title} reference`}
          onClick={onClick}
        >
          <ReferenceDeckIcon pageId={page.id} />
          <span className="flex min-w-0 flex-1 flex-col items-start gap-1">
            <span className="truncate font-semibold">{page.title}</span>
            <span className="text-muted-foreground hidden truncate text-xs leading-tight sm:block">
              {visual.description}
            </span>
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
