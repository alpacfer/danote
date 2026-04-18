import { Eye, Plus } from "lucide-react"

import {
  badgesForSavedForm,
  lemmaDisplayForSavedForm,
  lemmaTranslationWithGloss,
  posBadgeClass,
  type SentenceTokenCard,
} from "@/app/core"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

type SentencebankTokenButtonProps = {
  token: SentenceTokenCard
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
  onHighlightTokenIndex?: (tokenIndex: number | null) => void
}

export function SentencebankTokenButton({
  token,
  onOpenWordbankLemma,
  onOpenWordbankMeaning,
  onHighlightTokenIndex,
}: SentencebankTokenButtonProps) {
  const lemmaDisplay = lemmaDisplayForSavedForm({
    form: token.surface_form,
    lemma: token.stored_lemma,
    pos_tag: token.pos_tag,
  })
  const showLemma =
    lemmaDisplay &&
    lemmaDisplay.toLocaleLowerCase("da-DK") !== token.surface_form.toLocaleLowerCase("da-DK")
  const translationLine = lemmaTranslationWithGloss(
    token.english_translation,
    token.gloss_translation,
  )
  const badges = badgesForSavedForm({
    pos_tag: token.pos_tag,
    morphology: token.morphology,
  })
  const isSaved = typeof token.meaning_id === "number"

  return (
    <Card className="overflow-hidden py-0 gap-0">
      <CardContent className="p-0">
        <Button
          type="button"
          variant="ghost"
          className="hover:bg-accent/60 h-auto w-full items-center justify-between rounded-none px-4 py-4 text-left"
          onMouseEnter={() => onHighlightTokenIndex?.(token.token_index)}
          onMouseLeave={() => onHighlightTokenIndex?.(null)}
          onFocus={() => onHighlightTokenIndex?.(token.token_index)}
          onBlur={() => onHighlightTokenIndex?.(null)}
          onClick={() => {
            if (typeof token.meaning_id === "number") {
              onOpenWordbankMeaning(token.stored_lemma, token.meaning_id)
              return
            }
            onOpenWordbankLemma(token.stored_lemma)
          }}
        >
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-baseline gap-x-1.5 gap-y-0.5">
              <span className="font-semibold break-words">{token.surface_form}</span>
              {showLemma ? (
                <span className="text-muted-foreground text-sm break-words">from {lemmaDisplay}</span>
              ) : null}
              {translationLine ? (
                <span className="text-muted-foreground text-sm italic break-words">({translationLine})</span>
              ) : null}
            </div>
            {badges.length > 0 ? (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {badges.map((badge) => (
                  <Badge
                    key={`sentence-token-${token.token_index}-${badge.label}`}
                    variant={badge.tone === "primary" ? "outline" : "secondary"}
                    className={`text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(token.pos_tag ?? null)}` : ""}`.trim()}
                  >
                    {badge.label}
                  </Badge>
                ))}
              </div>
            ) : null}
          </div>
          {isSaved ? (
            <Eye className="text-muted-foreground ml-3 size-4 shrink-0 self-center" />
          ) : (
            <Plus className="text-muted-foreground ml-3 size-4 shrink-0 self-center" />
          )}
        </Button>
      </CardContent>
    </Card>
  )
}
