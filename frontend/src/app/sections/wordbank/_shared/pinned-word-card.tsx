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
      className="cursor-pointer transition-colors hover:bg-accent/50 focus-visible:ring-ring/50 focus-visible:ring-2"
    >
      <CardHeader className="gap-2">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <CardTitle className="shrink-0 text-lg font-semibold">{entry.lemma}</CardTitle>
            {badges.length > 0 ? (
              <ScrollableBadgeRow className="flex-1" fadeFromClass="from-card">
                {badges.map((badge) => (
                  <Badge
                    key={`pinned-word-${entry.lemma}-${badge.label}`}
                    variant={badge.tone === "primary" ? "default" : "secondary"}
                    className={`shrink-0 text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(posTag)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
                  >
                    {badge.label}
                  </Badge>
                ))}
              </ScrollableBadgeRow>
            ) : null}
          </div>
          <p className="text-muted-foreground text-sm">{entry.translation}</p>
        </div>
      </CardHeader>
    </Card>
  )
}
