import { Trash2 } from "lucide-react"

import {
  isMultiWordLemma,
  primaryPosLabel,
  semanticCategoryMaterialTone,
  type WordbankLemma,
} from "@/app/core"
import {
  runWordViewTransition,
  wordViewTransitionName,
} from "@/app/sections/wordbank/wordbank-view-transition"
import {
  wordbankSpecimenDescription,
  wordbankSpecimenTranslationGroups,
} from "@/app/sections/wordbank/wordbank-specimen-preview-data"
import { WordbankSpecimenPreview } from "@/app/sections/wordbank/wordbank-specimen-preview"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuGroup,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card"

type WordbankSpecimenTileProps = {
  lemma: WordbankLemma
  unreadCount: number
  onSelect: () => void
  onRequestDelete: () => void
}

export function WordbankSpecimenTile({
  lemma,
  unreadCount,
  onSelect,
  onRequestDelete,
}: WordbankSpecimenTileProps) {
  const displayWord = lemma.display_lemma?.trim() || lemma.lemma
  const posTags = normalizedPosTags(lemma)
  const posLabels = posTags.map((posTag) => primaryPosLabel(posTag) ?? posTag)
  const translationGroups = wordbankSpecimenTranslationGroups(lemma)
  const previewDescription = wordbankSpecimenDescription(posLabels, translationGroups)
  const hasPreview = Boolean(previewDescription)
  const materialTone = semanticCategoryMaterialTone(lemma.categories?.[0])

  return (
    <HoverCard open={hasPreview ? undefined : false} openDelay={300} closeDelay={200}>
      <ContextMenu>
        <HoverCardTrigger asChild>
          <ContextMenuTrigger asChild>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="w-full min-w-0 justify-start"
              aria-label={displayWord}
              aria-description={hasPreview ? previewDescription : undefined}
              data-testid={`wordbank-specimen-${lemma.lemma}`}
              data-material="word"
              data-material-tone={materialTone}
              data-index-stock
              data-mwe={isMultiWordLemma(lemma.lemma) ? "true" : "false"}
              data-grid-anchor="unit"
              data-grid-height="unit"
              style={{ viewTransitionName: wordViewTransitionName(lemma.lemma) }}
              onClick={() => runWordViewTransition(onSelect)}
            >
              <span className="truncate">{displayWord}</span>
              <UnreadMarker count={unreadCount} displayWord={displayWord} />
            </Button>
          </ContextMenuTrigger>
        </HoverCardTrigger>
        {hasPreview ? (
          <HoverCardContent
            align="start"
            side="top"
            sideOffset={8}
            collisionPadding={16}
            className="w-80 max-w-[calc(100vw-2rem)] p-0"
            data-material="word"
            data-material-tone={materialTone}
            data-index-stock
          >
            <WordbankSpecimenPreview
              displayWord={displayWord}
              posLabels={posLabels}
              translationGroups={translationGroups}
            />
          </HoverCardContent>
        ) : null}
        <ContextMenuContent>
          <ContextMenuGroup>
            <ContextMenuItem variant="destructive" onSelect={onRequestDelete}>
              <Trash2 />
              Delete whole lemma
            </ContextMenuItem>
          </ContextMenuGroup>
        </ContextMenuContent>
      </ContextMenu>
    </HoverCard>
  )
}

function UnreadMarker({ count, displayWord }: { count: number; displayWord: string }) {
  if (count <= 0) return null
  if (count > 1) {
    return (
      <Badge aria-label={`${count} pending verifications for ${displayWord}`} className="ml-0.5 min-w-5 px-1.5">
        {count}
      </Badge>
    )
  }
  return (
    <span
      aria-label={`Pending verification for ${displayWord}`}
      className="bg-primary inline-flex size-2.5 rounded-full"
    />
  )
}

function normalizedPosTags(lemma: WordbankLemma): string[] {
  return Array.from(
    new Set((lemma.pos_tags ?? []).map((posTag) => posTag.trim().toUpperCase()).filter(Boolean)),
  )
}
