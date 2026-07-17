import { Trash2 } from "lucide-react"

import { primaryPosLabel, type WordbankLemma } from "@/app/core"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuGroup,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

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
  const tooltipPos = posTags.map((posTag) => primaryPosLabel(posTag) ?? posTag).join(" · ")

  return (
    <Tooltip>
      <ContextMenu>
        <TooltipTrigger asChild>
          <ContextMenuTrigger asChild>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="w-auto"
              aria-label={displayWord}
              data-testid={`wordbank-specimen-${lemma.lemma}`}
              onClick={onSelect}
            >
              <span>{displayWord}</span>
              {lemma.variation_count > 1 ? (
                <span aria-hidden="true" className="text-muted-foreground text-xs">
                  · {lemma.variation_count}
                </span>
              ) : null}
              <UnreadMarker count={unreadCount} displayWord={displayWord} />
            </Button>
          </ContextMenuTrigger>
        </TooltipTrigger>
        <TooltipContent sideOffset={6}>
          <div className="flex max-w-64 flex-col gap-1">
            {lemma.english_translation ? <span className="font-medium">{lemma.english_translation}</span> : null}
            <span>{tooltipPos || "Word"}</span>
          </div>
        </TooltipContent>
        <ContextMenuContent>
          <ContextMenuGroup>
            <ContextMenuItem variant="destructive" onSelect={onRequestDelete}>
              <Trash2 />
              Delete whole lemma
            </ContextMenuItem>
          </ContextMenuGroup>
        </ContextMenuContent>
      </ContextMenu>
    </Tooltip>
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
