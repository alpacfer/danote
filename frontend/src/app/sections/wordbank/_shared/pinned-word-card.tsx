import type { KeyboardEvent } from "react"

import { corSecondaryBadgeClass, posBadgeClass, type CorSearchBadge } from "@/app/core"
import { metadataForPinnedWord } from "@/app/sections/wordbank/_shared/pinned-word-metadata"
import { wordPageBadgesForSavedForm } from "@/app/sections/wordbank/wordbank-card-badges"
import { WordbankPronunciationWord } from "@/app/sections/wordbank/wordbank-pronunciation-word"
import { Badge } from "@/components/ui/badge"
import { Card, CardHeader, CardTitle } from "@/components/ui/card"

export type PinnedWordEntry = {
  lemma: string
  translation: string
  description?: string | null
  playForm?: string | null
  posTag?: string | null
  morphology?: string | null
  badges?: CorSearchBadge[]
}

type PinnedWordCardProps = {
  entry: PinnedWordEntry
  pronunciationLoadingByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  onOpenWord: (lemma: string) => void
}

export function PinnedWordCard({
  entry,
  pronunciationLoadingByForm,
  onPlayPronunciation,
  onOpenWord,
}: PinnedWordCardProps) {
  const openWord = () => onOpenWord(entry.lemma)
  const metadata = metadataForPinnedWord(entry.lemma)
  const posTag = entry.posTag ?? metadata?.posTag ?? null
  const badges = entry.badges
    ?? (entry.posTag || entry.morphology
      ? wordPageBadgesForSavedForm({ pos_tag: entry.posTag ?? null, morphology: entry.morphology ?? null })
      : metadata?.badges)
    ?? []

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
          <CardTitle
            className="text-lg"
            onClick={(event) => event.stopPropagation()}
          >
            <WordbankPronunciationWord
              form={entry.lemma}
              playForm={entry.playForm ?? entry.lemma}
              hasPronunciation={true}
              pronunciationLoadingByForm={pronunciationLoadingByForm}
              onPlayPronunciation={onPlayPronunciation}
              className="text-lg font-semibold"
            />
          </CardTitle>
          <p className="text-muted-foreground text-sm">{entry.translation}</p>
          {entry.description ? (
            <p className="text-muted-foreground/80 text-xs">{entry.description}</p>
          ) : null}
          {badges.length > 0 ? (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {badges.map((badge) => (
                <Badge
                  key={`pinned-word-${entry.lemma}-${badge.label}`}
                  variant={badge.tone === "primary" ? "default" : "secondary"}
                  className={`text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(posTag)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
                >
                  {badge.label}
                </Badge>
              ))}
            </div>
          ) : null}
        </div>
      </CardHeader>
    </Card>
  )
}
