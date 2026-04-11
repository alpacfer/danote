import { type SentencebankSentence } from "@/app/core"
import { ScrollArea } from "@/components/ui/scroll-area"
import { SentencebankTokenButton } from "@/app/sections/sentencebank/sentencebank-token-button"

type SentencebankSentencePageProps = {
  sentence: SentencebankSentence | null
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
}

export function SentencebankSentencePage({
  sentence,
  onOpenWordbankLemma,
  onOpenWordbankMeaning,
}: SentencebankSentencePageProps) {
  if (!sentence) {
    return <p className="text-muted-foreground text-sm">Sentence not found.</p>
  }

  return (
    <ScrollArea className="min-h-0 flex-1">
      <div className="space-y-4 pr-1">
        <div className="space-y-1">
          <p className="text-base font-medium leading-relaxed max-w-[70ch] break-words">{sentence.source_text}</p>
          <p className="text-muted-foreground text-sm max-w-[70ch] break-words">
            {sentence.english_translation?.trim() || "No translation available."}
          </p>
        </div>
        {(sentence.tokens?.length ?? 0) > 0 ? (
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {(sentence.tokens ?? []).map((token) => (
              <SentencebankTokenButton
                key={`sentence-${sentence.id}-token-${token.token_index}-${token.surface_form}`}
                token={token}
                onOpenWordbankLemma={onOpenWordbankLemma}
                onOpenWordbankMeaning={onOpenWordbankMeaning}
              />
            ))}
          </div>
        ) : null}
      </div>
    </ScrollArea>
  )
}
