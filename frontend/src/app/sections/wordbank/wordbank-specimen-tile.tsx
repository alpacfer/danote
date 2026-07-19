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
import { useSpecimenCardExpansion } from "@/app/sections/wordbank/use-specimen-card-expansion"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuGroup,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"

type WordbankSpecimenTileProps = {
  lemma: WordbankLemma
  unreadCount: number
  expanded: boolean
  onExpandedChange: (open: boolean) => void
  onSelect: () => void
  onRequestDelete: () => void
}

export function WordbankSpecimenTile({
  lemma,
  unreadCount,
  expanded,
  onExpandedChange,
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
  const {
    alignment,
    anchorRef,
    direction,
    previewRef,
    surfaceRef,
    onBlur,
    onFocus,
    onKeyDown,
    onPointerDown,
    onPointerEnter,
    onPointerLeave,
  } = useSpecimenCardExpansion({
    enabled: hasPreview,
    open: expanded,
    onOpenChange: onExpandedChange,
  })
  const openWord = () => runWordViewTransition(onSelect)

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>
        <div
          ref={anchorRef}
          className="relative h-8 min-w-0"
          data-wordbank-expandable-card
          data-state={expanded ? "open" : "closed"}
          data-direction={direction}
          data-align={alignment}
          data-grid-anchor="unit"
          data-grid-height="unit"
          onPointerDown={onPointerDown}
          onPointerEnter={onPointerEnter}
          onPointerLeave={onPointerLeave}
        >
          <div
            ref={surfaceRef}
            aria-hidden="true"
            data-wordbank-expansion-surface
            data-material="word"
            data-material-tone={materialTone}
            data-index-stock
            data-paper-stock
            data-mwe={isMultiWordLemma(lemma.lemma) ? "true" : "false"}
            onClick={hasPreview ? openWord : undefined}
          >
            {hasPreview ? (
              <div ref={previewRef} data-wordbank-expansion-preview>
                <WordbankSpecimenPreview
                  posTags={posTags}
                  translationGroups={translationGroups}
                />
              </div>
            ) : null}
          </div>
          <div className="relative">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="w-full min-w-0 justify-start"
              aria-label={displayWord}
              aria-description={hasPreview ? previewDescription : undefined}
              data-testid={`wordbank-specimen-${lemma.lemma}`}
              data-mwe={isMultiWordLemma(lemma.lemma) ? "true" : "false"}
              data-wordbank-expansion-trigger
              style={{ viewTransitionName: wordViewTransitionName(lemma.lemma) }}
              onBlur={onBlur}
              onClick={openWord}
              onFocus={onFocus}
              onKeyDown={onKeyDown}
            >
              <span
                className="font-lexical truncate font-semibold tracking-[-0.01em]"
                data-wordbank-expansion-title
              >
                {displayWord}
              </span>
              <UnreadMarker count={unreadCount} displayWord={displayWord} />
            </Button>
          </div>
        </div>
      </ContextMenuTrigger>
      <ContextMenuContent>
        <ContextMenuGroup>
          <ContextMenuItem variant="destructive" onSelect={onRequestDelete}>
            <Trash2 />
            Delete whole lemma
          </ContextMenuItem>
        </ContextMenuGroup>
      </ContextMenuContent>
    </ContextMenu>
  )
}

function UnreadMarker({ count, displayWord }: { count: number; displayWord: string }) {
  if (count <= 0) return null
  if (count > 1) {
    return (
      <Badge
        aria-label={`${count} pending verifications for ${displayWord}`}
        className="ml-0.5 min-w-5 px-1.5"
        data-wordbank-unread-marker
      >
        {count}
      </Badge>
    )
  }
  return (
    <span
      aria-label={`Pending verification for ${displayWord}`}
      className="bg-primary inline-flex size-2.5 rounded-full"
      data-wordbank-unread-marker
    />
  )
}

function normalizedPosTags(lemma: WordbankLemma): string[] {
  return Array.from(
    new Set((lemma.pos_tags ?? []).map((posTag) => posTag.trim().toUpperCase()).filter(Boolean)),
  )
}
