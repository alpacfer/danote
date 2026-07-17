import { formatSentenceTranslation, type LemmaDetailsResponse } from "@/app/core"
import { SentenceHighlightedText } from "@/app/components/sentence-highlighted-text"
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

  const sortedSentences = [...linkedSentences].sort(
    (left, right) => Date.parse(right.created_at) - Date.parse(left.created_at),
  )
  const [featuredSentence, ...remainingSentences] = sortedSentences

  return (
    <section className="flex flex-col gap-4 pt-2" aria-labelledby="wordbank-linked-sentences-heading" data-grid-anchor="unit">
      <h2
        id="wordbank-linked-sentences-heading"
        className="text-muted-foreground flex h-8 items-center text-[11px] font-semibold uppercase tracking-wide"
      >
        Sentences
      </h2>
      <div className="grid gap-4">
        {[featuredSentence].map((sentence: LinkedSentence) => {
          const content = (
            <Card
              key={`linked-sentence-${sentence.id}`}
              className={onOpenSentence ? "hover:bg-accent/40 transition-colors cursor-pointer" : undefined}
              data-material="sentence"
              data-featured="true"
              data-grid-anchor="unit"
            >
              <CardContent className="flex flex-col gap-2 px-4 md:px-6">
                <p className="text-base font-medium leading-relaxed break-words">
                  <SentenceHighlightedText
                    sourceText={sentence.source_text}
                    tokens={sentence.tokens}
                    highlightedTokenIndexes={sentence.matched_token_indexes}
                  />
                </p>
                <p className="text-muted-foreground text-sm break-words">
                  {formatSentenceTranslation(sentence.english_translation) || "No translation available."}
                </p>
              </CardContent>
            </Card>
          )

          if (onOpenSentence) {
            return (
              <button
                key={`linked-sentence-btn-${sentence.id}`}
                type="button"
                className="text-left"
                onClick={() => onOpenSentence(sentence.id)}
              >
                {content}
              </button>
            )
          }

          return content
        })}
      </div>
      {remainingSentences.length > 0 ? (
        <>
          <h3 className="text-muted-foreground flex h-8 items-center text-[11px] font-semibold uppercase tracking-wide">
            More sentences
          </h3>
          <div className="grid gap-4 md:grid-cols-2">
            {remainingSentences.map((sentence) => (
              <LinkedSentenceCard key={sentence.id} sentence={sentence} onOpenSentence={onOpenSentence} />
            ))}
          </div>
        </>
      ) : null}
    </section>
  )
}

function LinkedSentenceCard({
  sentence,
  onOpenSentence,
}: {
  sentence: LinkedSentence
  onOpenSentence?: (id: number) => void
}) {
  const card = (
    <Card data-material="sentence" data-grid-anchor="unit">
      <CardContent className="flex flex-col gap-2 px-4 md:px-6">
        <p className="font-medium leading-6 break-words">
          <SentenceHighlightedText
            sourceText={sentence.source_text}
            tokens={sentence.tokens}
            highlightedTokenIndexes={sentence.matched_token_indexes}
          />
        </p>
        <p className="text-muted-foreground text-sm leading-6 break-words">
          {formatSentenceTranslation(sentence.english_translation) || "No translation available."}
        </p>
      </CardContent>
    </Card>
  )
  if (!onOpenSentence) return card
  return (
    <button type="button" className="text-left" onClick={() => onOpenSentence(sentence.id)}>
      {card}
    </button>
  )
}
