import {
  badgesForSavedForm,
  lemmaDisplayForSavedForm,
  lemmaTranslationWithGloss,
  posBadgeClass,
  type SentenceTokenCard,
} from "@/app/core"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { type SentencebankSentence } from "@/app/core"

export type SentencebankSectionProps = {
  sentencebankError: string | null
  isSentencebankLoading: boolean
  sentences: SentencebankSentence[]
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
}

export function SentencebankSection({
  sentencebankError,
  isSentencebankLoading,
  sentences,
  onOpenWordbankLemma,
  onOpenWordbankMeaning,
}: SentencebankSectionProps) {
  if (sentencebankError) {
    return (
      <p className="text-destructive text-sm" role="alert">
        {sentencebankError}
      </p>
    )
  }

  if (isSentencebankLoading && sentences.length === 0) {
    return (
      <div className="space-y-3">
        <Card>
          <CardContent className="space-y-2">
            <Skeleton className="h-5 w-48" />
            <Skeleton className="h-4 w-32" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="space-y-2">
            <Skeleton className="h-5 w-56" />
            <Skeleton className="h-4 w-36" />
          </CardContent>
        </Card>
      </div>
    )
  }

  if (sentences.length === 0) {
    return <p className="text-muted-foreground text-sm">No saved sentences yet. Select a sentence in Playground to add one.</p>
  }

  return (
    <ScrollArea className="min-h-0 flex-1">
      <div className="space-y-3 pr-1">
        {sentences.map((sentence) => (
          <Card key={sentence.id}>
            <CardContent className="space-y-2">
              <p className="text-base font-medium leading-relaxed max-w-[70ch] break-words">{sentence.source_text}</p>
              <p className="text-muted-foreground text-sm max-w-[70ch] break-words">
                {sentence.english_translation?.trim() || "No translation available."}
              </p>
              {(sentence.tokens?.length ?? 0) > 0 ? (
                <div className="grid gap-2 pt-2 sm:grid-cols-2 xl:grid-cols-3">
                  {(sentence.tokens ?? []).map((token) => (
                    <SentenceTokenButton
                      key={`sentence-${sentence.id}-token-${token.token_index}-${token.surface_form}`}
                      token={token}
                      onOpenWordbankLemma={onOpenWordbankLemma}
                      onOpenWordbankMeaning={onOpenWordbankMeaning}
                    />
                  ))}
                </div>
              ) : null}
            </CardContent>
          </Card>
        ))}
      </div>
    </ScrollArea>
  )
}

function SentenceTokenButton({
  token,
  onOpenWordbankLemma,
  onOpenWordbankMeaning,
}: {
  token: SentenceTokenCard
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
}) {
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
