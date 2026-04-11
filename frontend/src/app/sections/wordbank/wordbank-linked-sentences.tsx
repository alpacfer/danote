import { type LemmaDetailsResponse } from "@/app/core"
import { Card, CardContent } from "@/components/ui/card"

type LinkedSentence = NonNullable<LemmaDetailsResponse["linked_sentences"]>[number]

type WordbankLinkedSentencesProps = {
  linkedSentences: LemmaDetailsResponse["linked_sentences"] | undefined
  onOpenSentence?: (id: number) => void
}

export function WordbankLinkedSentences({
  linkedSentences,
  onOpenSentence,
}: WordbankLinkedSentencesProps) {
  if (!linkedSentences || linkedSentences.length === 0) {
    return null
  }

  return (
    <section className="space-y-4 pt-2" aria-labelledby="wordbank-linked-sentences-heading">
      <h2
        id="wordbank-linked-sentences-heading"
        className="text-muted-foreground text-[11px] font-semibold uppercase tracking-wide"
      >
        Sentences
      </h2>
      <div className="space-y-3">
        {linkedSentences.map((sentence: LinkedSentence) => {
          const content = (
            <Card
              key={`linked-sentence-${sentence.id}`}
              className={onOpenSentence ? "hover:bg-accent/40 transition-colors cursor-pointer" : undefined}
            >
              <CardContent className="space-y-1">
                <p className="text-base font-medium leading-relaxed break-words">{sentence.source_text}</p>
                <p className="text-muted-foreground text-sm break-words">
                  {sentence.english_translation?.trim() || "No translation available."}
                </p>
              </CardContent>
            </Card>
          )

          if (onOpenSentence) {
            return (
              <button
                key={`linked-sentence-btn-${sentence.id}`}
                type="button"
                className="w-full text-left"
                onClick={() => onOpenSentence(sentence.id)}
              >
                {content}
              </button>
            )
          }

          return content
        })}
      </div>
    </section>
  )
}
