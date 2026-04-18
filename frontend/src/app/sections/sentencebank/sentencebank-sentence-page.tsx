import { useState } from "react"

import { formatSentenceTranslation, type SentencebankSentence } from "@/app/core"
import { SentenceHighlightedText } from "@/app/components/sentence-highlighted-text"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { SentencebankTokenButton } from "@/app/sections/sentencebank/sentencebank-token-button"
import { WordbankPronunciationWord } from "@/app/sections/wordbank/wordbank-pronunciation-word"
import { Clock3, RotateCcw } from "lucide-react"

type SentencebankSentencePageProps = {
  sentence: SentencebankSentence | null
  isLoadingTokens?: boolean
  pronunciationLoadingBySentenceId: Record<string, boolean>
  regeneratingPronunciationBySentenceId: Record<string, boolean>
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
  onPlayPronunciation: (sentenceId: number) => void
  onPlayPronunciationSlowly: (sentenceId: number) => void
  onRegeneratePronunciation: (sentenceId: number) => void
}

function wordCount(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length
}

export function SentencebankSentencePage({
  sentence,
  isLoadingTokens = false,
  pronunciationLoadingBySentenceId,
  regeneratingPronunciationBySentenceId,
  onOpenWordbankLemma,
  onOpenWordbankMeaning,
  onPlayPronunciation,
  onPlayPronunciationSlowly,
  onRegeneratePronunciation,
}: SentencebankSentencePageProps) {
  const [highlightedTokenIndex, setHighlightedTokenIndex] = useState<number | null>(null)

  if (!sentence) {
    return <p className="text-muted-foreground text-sm">Sentence not found.</p>
  }

  const skeletonCount = Math.max(wordCount(sentence.source_text), 1)
  const translation = formatSentenceTranslation(sentence.english_translation) ?? ""
  const sentenceId = sentence.id
  const isPlaying = Boolean(pronunciationLoadingBySentenceId[sentenceId])
  const isRegenerating = Boolean(regeneratingPronunciationBySentenceId[sentenceId])
  const pronunciationContextMenuItems = sentenceId > 0 ? [
    {
      icon: <Clock3 className="mr-2 size-4" />,
      label: isPlaying ? "Playing..." : "Say slowly",
      disabled: isPlaying,
      onSelect: () => onPlayPronunciationSlowly(sentenceId),
    },
    {
      icon: <RotateCcw className="mr-2 size-4" />,
      label: isRegenerating ? "Regenerating audio..." : "Regenerate audio",
      disabled: isRegenerating,
      separatorBefore: true,
      onSelect: () => onRegeneratePronunciation(sentenceId),
    },
  ] : []

  return (
    <ScrollArea className="min-h-0 flex-1">
      <div className="space-y-4 pr-1">
        <div className="space-y-1">
          <WordbankPronunciationWord
            form={sentence.source_text}
            hasPronunciation={sentence.has_pronunciation ?? false}
            pronunciationLoadingByForm={pronunciationLoadingBySentenceId}
            onPlayPronunciation={() => onPlayPronunciation(sentenceId)}
            contextMenuItems={pronunciationContextMenuItems}
            className="text-base font-medium leading-relaxed max-w-[70ch] break-words text-left whitespace-normal"
            iconClassName="size-4"
            as="span"
          >
            <SentenceHighlightedText
              sourceText={sentence.source_text}
              tokens={sentence.tokens}
              highlightedTokenIndexes={typeof highlightedTokenIndex === "number" ? [highlightedTokenIndex] : []}
            />
          </WordbankPronunciationWord>
          {translation ? (
            <p className="text-muted-foreground text-sm max-w-[70ch] break-words">{translation}</p>
          ) : isLoadingTokens ? (
            <Skeleton className="h-4 w-40" data-testid="sentence-page-translation-skeleton" />
          ) : (
            <p className="text-muted-foreground text-sm max-w-[70ch] break-words">No translation available.</p>
          )}
        </div>
        {isLoadingTokens ? (
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: skeletonCount }).map((_, i) => (
              <Skeleton key={i} className="h-16 rounded-md" />
            ))}
          </div>
        ) : (sentence.tokens?.length ?? 0) > 0 ? (
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {(sentence.tokens ?? []).map((token) => (
              <SentencebankTokenButton
                key={`sentence-${sentence.id}-token-${token.token_index}-${token.surface_form}`}
                token={token}
                onOpenWordbankLemma={onOpenWordbankLemma}
                onOpenWordbankMeaning={onOpenWordbankMeaning}
                onHighlightTokenIndex={setHighlightedTokenIndex}
              />
            ))}
          </div>
        ) : null}
      </div>
    </ScrollArea>
  )
}
