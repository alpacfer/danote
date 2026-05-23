import { Eye, Plus } from "lucide-react"

import {
  badgesForSavedForm,
  corSecondaryBadgeClass,
  lemmaDisplayForSavedForm,
  lemmaTranslationWithGloss,
  posBadgeClass,
  type SentenceTokenCard,
} from "@/app/core"
import { enrichSentenceTokenWithBuiltins } from "@/app/sections/sentencebank/builtin-token-enrichment"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

type SentencebankTokenButtonProps = {
  token: SentenceTokenCard
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
  onAddUnsavedToken: (token: SentenceTokenCard) => void
  onHighlightTokenIndex?: (tokenIndex: number | null) => void
}

export function SentencebankTokenButton({
  token: rawToken,
  onOpenWordbankLemma,
  onOpenWordbankMeaning,
  onAddUnsavedToken,
  onHighlightTokenIndex,
}: SentencebankTokenButtonProps) {
  const token = enrichSentenceTokenWithBuiltins(rawToken)
  const lemmaDisplay = lemmaDisplayForSavedForm({
    form: token.surface_form,
    lemma: token.stored_lemma ?? token.surface_form,
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
    // Pass the stored lemma so MWE tokens ("gav op", "Pas på") render the
    // "Phrasal verb" badge on the sentence breakdown card instead of "Verb".
    lemma: token.stored_lemma,
  })
  const isSaved = token.save_status !== "unsaved" && typeof token.stored_lemma === "string" && token.stored_lemma.length > 0

  return (
    <Card className="overflow-hidden py-0 gap-0 min-w-44">
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
            if (!isSaved || !token.stored_lemma) {
              onAddUnsavedToken(token)
              return
            }
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
            </div>
            {translationLine ? (
              <div className="text-muted-foreground text-sm italic break-words">{translationLine}</div>
            ) : null}
            {badges.length > 0 ? (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {badges.map((badge) => (
                  <Badge
                    key={`sentence-token-${token.token_index}-${badge.label}`}
                    variant={badge.tone === "primary" ? "default" : "secondary"}
                    className={`text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(token.pos_tag ?? null)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
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
