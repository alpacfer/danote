import {
  badgesForSavedForm,
  lemmaDisplayForSavedForm,
  lemmaTranslationWithGloss,
  posBadgeClass,
  type SentenceTokenCard,
} from "@/app/core"
import { Badge } from "@/components/ui/badge"

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
  const translationLine = lemmaTranslationWithGloss(
    token.english_translation,
    token.gloss_translation,
  )
  const badges = badgesForSavedForm({
    pos_tag: token.pos_tag,
    morphology: token.morphology,
  })

  return (
    <button
      type="button"
      className="bg-muted/35 hover:bg-accent/60 rounded-xl border px-3 py-2 text-left transition-colors"
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
      <div className="space-y-1">
        <p className="font-semibold break-words">{token.surface_form}</p>
        {lemmaDisplay && lemmaDisplay.toLocaleLowerCase("da-DK") !== token.surface_form.toLocaleLowerCase("da-DK") ? (
          <p className="text-muted-foreground text-xs break-words">from {lemmaDisplay}</p>
        ) : null}
        {translationLine ? (
          <p className="text-muted-foreground text-xs break-words">{translationLine}</p>
        ) : null}
        {badges.length > 0 ? (
          <div className="flex flex-wrap gap-1.5 pt-1">
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
    </button>
  )
}
