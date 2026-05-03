import { useState } from "react"

import { formatSentenceTranslation, type SentencebankSentence, type SentenceTokenCard } from "@/app/core"
import { SentenceHighlightedText } from "@/app/components/sentence-highlighted-text"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { SentencebankTokenButton } from "@/app/sections/sentencebank/sentencebank-token-button"
import { WordbankPronunciationWord } from "@/app/sections/wordbank/wordbank-pronunciation-word"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Clock3, Plus, RotateCcw } from "lucide-react"

type SentencebankSentencePageProps = {
  sentence: SentencebankSentence | null
  isLoadingTokens?: boolean
  pronunciationLoadingBySentenceId: Record<string, boolean>
  regeneratingPronunciationBySentenceId: Record<string, boolean>
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
  onAddUnsavedToken: (sentenceId: number, token: SentenceTokenCard) => void
  onPlayPronunciation: (sentenceId: number) => void
  onPlayPronunciationSlowly: (sentenceId: number) => void
  onRegeneratePronunciation: (sentenceId: number) => void
}

function pendingTokenSurfaces(text: string): string[] {
  const matches = text.match(/[\p{L}\p{N}_]+(?:['’.-][\p{L}\p{N}_]+)*/gu)
  if (matches && matches.length > 0) {
    return matches
  }
  return text.trim().split(/\s+/).filter(Boolean)
}

function PendingSentenceTokenCard({ surface }: { surface: string }) {
  return (
    <Card className="overflow-hidden py-0 gap-0" data-testid="sentence-page-pending-token-card">
      <CardContent className="p-0">
        <Button
          type="button"
          variant="ghost"
          disabled
          className="h-auto min-h-16 w-full items-center justify-between rounded-none px-4 py-4 text-left opacity-100"
        >
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-baseline gap-x-1.5 gap-y-0.5">
              <span className="font-semibold break-words">{surface}</span>
              <Skeleton className="h-3 w-16" />
            </div>
            <Skeleton className="mt-2 h-3 w-24" />
            <div className="mt-2 flex flex-wrap gap-1.5">
              <Skeleton className="h-5 w-14 rounded-full" />
              <Skeleton className="h-5 w-20 rounded-full" />
            </div>
          </div>
          <Plus className="text-muted-foreground ml-3 size-4 shrink-0 self-center opacity-50" />
        </Button>
      </CardContent>
    </Card>
  )
}

export function SentencebankSentencePage({
  sentence,
  isLoadingTokens = false,
  pronunciationLoadingBySentenceId,
  regeneratingPronunciationBySentenceId,
  onOpenWordbankLemma,
  onOpenWordbankMeaning,
  onAddUnsavedToken,
  onPlayPronunciation,
  onPlayPronunciationSlowly,
  onRegeneratePronunciation,
}: SentencebankSentencePageProps) {
  const [highlightedTokenIndex, setHighlightedTokenIndex] = useState<number | null>(null)

  if (!sentence) {
    return <p className="text-muted-foreground text-sm">Sentence not found.</p>
  }

  const pendingSurfaces = pendingTokenSurfaces(sentence.source_text)
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
            {(pendingSurfaces.length > 0 ? pendingSurfaces : [sentence.source_text]).map((surface, i) => (
              <PendingSentenceTokenCard key={`pending-sentence-token-${i}-${surface}`} surface={surface} />
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
                onAddUnsavedToken={(unsavedToken) => onAddUnsavedToken(sentence.id, unsavedToken)}
                onHighlightTokenIndex={setHighlightedTokenIndex}
              />
            ))}
          </div>
        ) : null}
      </div>
    </ScrollArea>
  )
}
