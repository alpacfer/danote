import { useState } from "react"
import { BookOpenText, ChevronRight, Loader2, MessageSquareQuote } from "lucide-react"

import {
  corSecondaryBadgeClass,
  posBadgeClass,
  primaryPosLabel,
  secondaryTagsForPos,
  type SentencebankSentence,
} from "@/app/core"
import { WordbankPronunciationWord } from "@/app/sections/wordbank/wordbank-pronunciation-word"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import { PinnedExamplesDialog } from "@/app/sections/wordbank/_shared/pinned-examples-dialog"
import { relatedSentencesFor } from "@/app/sections/wordbank/_shared/pinned-page-token-matchers"

export type PinnedLemmaEntry = {
  lemma: string
  translation: string
  posTag?: string | null
  morphology?: string | null
  note?: string | null
}

type PinnedLemmaCardProps = {
  entry: PinnedLemmaEntry
  sentences?: SentencebankSentence[]
  pronunciationLoadingByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  generatingExample?: boolean
  onGenerateExample?: (lemma: string) => void
  onOpenSentence?: (id: number) => void
}

export function PinnedLemmaCard({
  entry,
  sentences,
  pronunciationLoadingByForm,
  onPlayPronunciation,
  generatingExample,
  onGenerateExample,
  onOpenSentence,
}: PinnedLemmaCardProps) {
  const [isExamplesDialogOpen, setIsExamplesDialogOpen] = useState(false)
  const related = sentences ? relatedSentencesFor(entry.lemma, sentences) : []
  const badges = badgesFor(entry)
  const card = (
    <Card>
      <CardHeader className="gap-2">
        <div className="space-y-1">
          <CardTitle className="text-lg">
            <WordbankPronunciationWord
              form={entry.lemma}
              hasPronunciation={true}
              pronunciationLoadingByForm={pronunciationLoadingByForm}
              onPlayPronunciation={onPlayPronunciation}
              className="text-lg font-semibold"
            />
          </CardTitle>
          <p className="text-muted-foreground text-sm">{entry.translation}</p>
          {entry.note ? (
            <p className="text-muted-foreground/80 text-xs italic">{entry.note}</p>
          ) : null}
        </div>
        {badges.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {badges.map((badge) => (
              <Badge
                key={`${entry.lemma}-${badge.label}`}
                variant={badge.tone === "primary" ? "default" : "secondary"}
                className={`text-xs ${
                  badge.tone === "primary"
                    ? `border ${posBadgeClass(entry.posTag ?? "")}`
                    : `border ${corSecondaryBadgeClass(badge.label)}`
                }`.trim()}
              >
                {badge.label}
              </Badge>
            ))}
          </div>
        ) : null}
      </CardHeader>
      {related.length > 0 ? (
        <CardContent>
          <Button
            type="button"
            variant="outline"
            className="bg-muted/20 hover:bg-accent/60 h-auto w-full justify-between border-dashed px-3 py-3 text-left"
            onClick={() => setIsExamplesDialogOpen(true)}
          >
            <span className="flex min-w-0 items-center gap-2">
              <BookOpenText className="text-muted-foreground size-4 shrink-0" />
              <span className="truncate">See examples</span>
            </span>
            <ChevronRight className="text-muted-foreground size-4 shrink-0" />
          </Button>
        </CardContent>
      ) : null}
    </Card>
  )

  return (
    <>
      {onGenerateExample ? (
        <ContextMenu>
          <ContextMenuTrigger asChild>{card}</ContextMenuTrigger>
          <ContextMenuContent>
            <ContextMenuItem
              disabled={Boolean(generatingExample)}
              onSelect={() => onGenerateExample(entry.lemma)}
            >
              {generatingExample ? <Loader2 className="animate-spin" /> : <MessageSquareQuote />}
              {generatingExample ? "Generating example..." : "Generate example"}
            </ContextMenuItem>
          </ContextMenuContent>
        </ContextMenu>
      ) : (
        card
      )}
      <PinnedExamplesDialog
        lemma={entry.lemma}
        open={isExamplesDialogOpen}
        onOpenChange={setIsExamplesDialogOpen}
        sentences={related}
        onOpenSentence={onOpenSentence}
      />
    </>
  )
}

function badgesFor(entry: PinnedLemmaEntry): Array<{ label: string; tone: "primary" | "secondary" }> {
  const badges: Array<{ label: string; tone: "primary" | "secondary" }> = []
  const pos = entry.posTag
  if (pos) {
    badges.push({ label: primaryPosLabel(pos) ?? pos, tone: "primary" })
    for (const tag of secondaryTagsForPos(pos, entry.morphology ?? null)) {
      badges.push({ label: tag, tone: "secondary" })
    }
  }
  return badges
}
