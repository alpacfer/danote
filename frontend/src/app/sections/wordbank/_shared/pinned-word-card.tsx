import { useRef, type KeyboardEvent } from "react"

import { corSecondaryBadgeClass, posBadgeClass, type CorSearchBadge } from "@/app/core"
import { PaperReveal } from "@/app/sections/wordbank/_shared/paper-reveal"
import { metadataForPinnedWord } from "@/app/sections/wordbank/_shared/pinned-word-metadata"
import { wordPageBadgesForSavedForm } from "@/app/sections/wordbank/wordbank-card-badges"
import { applyPrimaryBadgeLabelOverride } from "@/app/sections/wordbank/wordbank-primary-pos-badge"
import { Badge } from "@/components/ui/badge"
import { Card, CardHeader, CardTitle } from "@/components/ui/card"
import {
  HoverCard,
  HoverCardTrigger,
} from "@/components/ui/hover-card"
import { ScrollableBadgeRow } from "@/components/ui/scrollable-badge-row"

export type PinnedWordEntry = {
  lemma: string
  translation: string
  playForm?: string | null
  posTag?: string | null
  morphology?: string | null
  badges?: CorSearchBadge[]
}

type PinnedWordCardProps = {
  entry: PinnedWordEntry
  onOpenWord: (lemma: string) => void
  hiddenBadges?: readonly string[]
}

export function PinnedWordCard({
  entry,
  onOpenWord,
  hiddenBadges,
}: PinnedWordCardProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const openWord = () => onOpenWord(entry.lemma)
  const metadata = metadataForPinnedWord(entry.lemma)
  const posTag = entry.posTag ?? metadata?.posTag ?? null
  const rawBadges = entry.badges
    ?? (entry.posTag || entry.morphology
      ? wordPageBadgesForSavedForm({ pos_tag: entry.posTag ?? null, morphology: entry.morphology ?? null })
      : metadata?.badges)
    ?? []
  const allBadges = applyPrimaryBadgeLabelOverride(rawBadges, {
    posTag: entry.posTag ?? null,
    morphology: entry.morphology ?? null,
    lemma: entry.lemma,
  })
  const hiddenSet = hiddenBadges && hiddenBadges.length > 0 ? new Set(hiddenBadges) : null
  const badges = hiddenSet ? allBadges.filter((badge) => !hiddenSet.has(badge.label)) : allBadges
  const translation = entry.translation.trim()

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Enter" && event.key !== " ") return
    event.preventDefault()
    openWord()
  }

  return (
    <HoverCard open={translation ? undefined : false} openDelay={70} closeDelay={100}>
      <HoverCardTrigger asChild>
        <Card
          ref={cardRef}
          role="button"
          tabIndex={0}
          aria-label={`Open ${entry.lemma} in wordbank`}
          aria-description={translation || undefined}
          onClick={openWord}
          onKeyDown={handleKeyDown}
          className="min-w-0 cursor-pointer overflow-hidden focus-visible:ring-ring/50 focus-visible:ring-2"
          data-material="reference"
          data-index-stock
          data-paper-stock
          data-paper-trigger
          data-grid-anchor="unit"
        >
          <CardHeader className="min-w-0 px-4 sm:px-6">
            <div className="flex min-w-0 items-start justify-between gap-2">
              <CardTitle className="font-lexical min-w-0 break-words text-xl font-semibold tracking-[-0.01em]">
                {entry.lemma}
              </CardTitle>
              {badges.length > 0 ? (
                <ScrollableBadgeRow className="min-w-0 flex-1 justify-end" fadeFromClass="from-card">
                  {badges.map((badge) => (
                    <Badge
                      key={`pinned-word-${entry.lemma}-${badge.label}`}
                      variant={badge.tone === "primary" ? "default" : "secondary"}
                      className={`shrink-0 text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(badge.label === "HV Word" ? "HV_WORD" : posTag)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
                    >
                      {badge.label}
                    </Badge>
                  ))}
                </ScrollableBadgeRow>
              ) : null}
            </div>
          </CardHeader>
        </Card>
      </HoverCardTrigger>
      {translation ? (
        <PaperReveal
          className="w-72 max-w-[calc(100vw-2rem)]"
          material="reference"
          onEscapeKeyDown={() => {
            window.setTimeout(() => cardRef.current?.focus(), 0)
          }}
        >
          <div className="flex flex-col gap-2 p-4" data-pinned-word-preview>
            <p className="font-lexical text-xl leading-6 font-semibold tracking-[-0.01em]">{entry.lemma}</p>
            <p className="text-sm font-medium">{translation}</p>
          </div>
        </PaperReveal>
      ) : null}
    </HoverCard>
  )
}
