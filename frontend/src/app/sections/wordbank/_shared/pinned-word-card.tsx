import type { KeyboardEvent } from "react"

import { corSecondaryBadgeClass, posBadgeClass, type CorSearchBadge } from "@/app/core"
import { metadataForPinnedWord } from "@/app/sections/wordbank/_shared/pinned-word-metadata"
import { wordPageBadgesForSavedForm } from "@/app/sections/wordbank/wordbank-card-badges"
import { applyPrimaryBadgeLabelOverride } from "@/app/sections/wordbank/wordbank-primary-pos-badge"
import { Badge } from "@/components/ui/badge"
import { Card, CardHeader, CardTitle } from "@/components/ui/card"
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

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Enter" && event.key !== " ") return
    event.preventDefault()
    openWord()
  }

  return (
    <Card
      role="button"
      tabIndex={0}
      aria-label={`Open ${entry.lemma} in wordbank`}
      onClick={openWord}
      onKeyDown={handleKeyDown}
      className="min-w-0 cursor-pointer overflow-hidden transition-colors hover:bg-accent/50 focus-visible:ring-ring/50 focus-visible:ring-2"
    >
      <CardHeader className="min-w-0 gap-2 px-4 sm:px-6">
        <div className="flex min-w-0 flex-col gap-x-2 gap-y-1 md:grid md:grid-cols-[auto_1fr]">
          <CardTitle className="break-words text-lg font-semibold md:col-start-1 md:row-start-1">{entry.lemma}</CardTitle>
          {badges.length > 0 ? (
            <ScrollableBadgeRow className="order-3 w-full min-w-0 flex-1 md:order-none md:col-start-2 md:row-start-1 md:w-auto" fadeFromClass="from-card">
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
          <p className="text-muted-foreground order-2 break-words text-sm md:order-none md:col-span-2 md:row-start-2">{entry.translation}</p>
        </div>
      </CardHeader>
    </Card>
  )
}
