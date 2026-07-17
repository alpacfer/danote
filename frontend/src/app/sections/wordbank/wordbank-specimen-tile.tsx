import { BookOpenText, Link2, Sparkle, Sparkles, Trash2, Zap } from "lucide-react"

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
  const isRecent = wasActiveRecently(lemma.last_enriched_at)
  const materialTone = semanticCategoryMaterialTone(lemma.categories?.[0])

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
              data-material="word"
              data-material-tone={materialTone}
              data-mwe={isMultiWordLemma(lemma.lemma) ? "true" : "false"}
              data-grid-anchor="unit"
              data-grid-height="unit"
              style={{ viewTransitionName: wordViewTransitionName(lemma.lemma) }}
              onClick={() => runWordViewTransition(onSelect)}
            >
              <PosStamp posTags={posTags} />
              <span>{displayWord}</span>
              {lemma.variation_count > 1 ? (
                <span aria-hidden="true" className="text-muted-foreground text-xs">
                  · {lemma.variation_count}
                </span>
              ) : null}
              {isRecent ? (
                <Sparkle data-icon="inline-end" aria-label={`Recently enriched ${displayWord}`} />
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

function PosStamp({ posTags }: { posTags: string[] }) {
  const primary = posTags[0] ?? ""
  if (primary === "VERB" || primary === "AUX") {
    return <Zap data-icon="inline-start" aria-hidden="true" />
  }
  if (primary === "ADJ" || primary === "ADV") {
    return <Sparkles data-icon="inline-start" aria-hidden="true" />
  }
  if (primary === "ADP" || primary === "CCONJ" || primary === "SCONJ") {
    return <Link2 data-icon="inline-start" aria-hidden="true" />
  }
  return <BookOpenText data-icon="inline-start" aria-hidden="true" />
}

function wasActiveRecently(timestamp: string | null | undefined): boolean {
  if (!timestamp) return false
  const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(timestamp)
  const normalizedTimestamp = timestamp.replace(" ", "T")
  const activeAt = Date.parse(hasTimezone ? normalizedTimestamp : `${normalizedTimestamp}Z`)
  if (!Number.isFinite(activeAt)) return false
  const age = Date.now() - activeAt
  return age >= 0 && age <= 7 * 24 * 60 * 60 * 1000
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
