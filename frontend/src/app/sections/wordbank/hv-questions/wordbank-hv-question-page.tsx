import { useState } from "react"
import { BookOpenText, ChevronRight, Loader2, MessageSquareQuote } from "lucide-react"

import {
  corSecondaryBadgeClass,
  formatSentenceTranslation,
  normalizeSearchWord,
  posBadgeClass,
  primaryPosLabel,
  secondaryTagsForPos,
  type SentencebankSentence,
} from "@/app/core"
import { SentenceHighlightedText } from "@/app/components/sentence-highlighted-text"
import {
  HV_QUESTION_CATEGORY_LABELS,
  HV_QUESTION_WORDS,
  type HvQuestionEntry,
  type HvQuestionCategory,
} from "@/app/sections/wordbank/hv-questions/hv-question-data"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"

type WordbankHvQuestionPageProps = {
  sentences: SentencebankSentence[]
  generatingStaticExampleByLemma: Record<string, boolean>
  onGenerateStaticExample: (lemma: string) => void
  onOpenSentence?: (id: number) => void
}

export function WordbankHvQuestionPage({
  sentences,
  generatingStaticExampleByLemma,
  onGenerateStaticExample,
  onOpenSentence,
}: WordbankHvQuestionPageProps) {
  const grouped = groupHvWords()
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-6 pr-2">
          {grouped.map(([category, entries]) => (
            <section key={category} className="space-y-3" aria-labelledby={`hv-${category}`}>
              <h2 id={`hv-${category}`} className="text-base font-semibold">
                {HV_QUESTION_CATEGORY_LABELS[category]}
              </h2>
              <div className="grid items-start gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {entries.map((entry) => (
                  <HvQuestionCard
                    key={entry.lemma}
                    entry={entry}
                    relatedSentences={relatedSentencesFor(entry.lemma, sentences)}
                    isGeneratingExample={Boolean(generatingStaticExampleByLemma[entry.lemma])}
                    onGenerateStaticExample={onGenerateStaticExample}
                    onOpenSentence={onOpenSentence}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}

function HvQuestionCard({
  entry,
  relatedSentences,
  isGeneratingExample,
  onGenerateStaticExample,
  onOpenSentence,
}: {
  entry: HvQuestionEntry
  relatedSentences: SentencebankSentence[]
  isGeneratingExample: boolean
  onGenerateStaticExample: (lemma: string) => void
  onOpenSentence?: (id: number) => void
}) {
  const [isExamplesDialogOpen, setIsExamplesDialogOpen] = useState(false)
  const badges = badgesForHvEntry(entry)

  return (
    <>
      <ContextMenu>
        <ContextMenuTrigger asChild>
          <Card>
            <CardHeader className="gap-2">
              <div className="space-y-1">
                <CardTitle className="text-lg">{entry.lemma}</CardTitle>
                <p className="text-muted-foreground text-sm">{entry.translation}</p>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {badges.map((badge) => (
                  <Badge
                    key={`hv-${entry.lemma}-badge-${badge.label}`}
                    variant={badge.tone === "primary" ? "default" : "secondary"}
                    className={`text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(entry.posTag)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
                  >
                    {badge.label}
                  </Badge>
                ))}
              </div>
            </CardHeader>
            {relatedSentences.length > 0 ? (
              <CardContent>
                <Button
                  type="button"
                  variant="outline"
                  className="bg-muted/20 hover:bg-accent/60 h-auto w-full justify-between border-dashed px-3 py-3 text-left"
                  onClick={() => setIsExamplesDialogOpen(true)}
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <BookOpenText className="text-muted-foreground size-4 shrink-0" />
                    <span className="truncate">See examples</span>
                  </span>
                  <ChevronRight className="text-muted-foreground size-4 shrink-0" />
                </Button>
              </CardContent>
            ) : null}
          </Card>
        </ContextMenuTrigger>
        <ContextMenuContent>
          <ContextMenuItem
            disabled={isGeneratingExample}
            onSelect={() => onGenerateStaticExample(entry.lemma)}
          >
            {isGeneratingExample ? <Loader2 className="animate-spin" /> : <MessageSquareQuote />}
            {isGeneratingExample ? "Generating example..." : "Generate example"}
          </ContextMenuItem>
        </ContextMenuContent>
      </ContextMenu>
      <Dialog open={isExamplesDialogOpen} onOpenChange={setIsExamplesDialogOpen}>
        <DialogContent className="max-h-[min(720px,calc(100vh-2rem))] grid-rows-[auto_minmax(0,1fr)] sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>{entry.lemma} examples</DialogTitle>
            <DialogDescription className="sr-only">
              Saved example sentences for this HV question word.
            </DialogDescription>
          </DialogHeader>
          <ScrollArea className="min-h-0 pr-3">
            <div className="space-y-2">
              {relatedSentences.map((sentence) => (
                <button
                  key={sentence.id}
                  type="button"
                  className="hover:bg-accent/50 w-full rounded-md border p-3 text-left transition-colors"
                  onClick={() => {
                    setIsExamplesDialogOpen(false)
                    onOpenSentence?.(sentence.id)
                  }}
                  disabled={!onOpenSentence}
                >
                  <p className="text-sm font-medium leading-relaxed break-words">
                    <SentenceHighlightedText
                      sourceText={sentence.source_text}
                      tokens={sentence.tokens}
                      highlightedTokenIndexes={matchedTokenIndexes(entry.lemma, sentence)}
                    />
                  </p>
                  <p className="text-muted-foreground mt-1 text-xs break-words">
                    {formatSentenceTranslation(sentence.english_translation) || "No translation available."}
                  </p>
                </button>
              ))}
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </>
  )
}

function badgesForHvEntry(entry: HvQuestionEntry): Array<{ label: string; tone: "primary" | "secondary" }> {
  return [
    { label: primaryPosLabel(entry.posTag) ?? entry.posTag, tone: "primary" },
    ...secondaryTagsForPos(entry.posTag, entry.morphology).map((label) => ({
      label,
      tone: "secondary" as const,
    })),
  ]
}

function groupHvWords(): Array<[HvQuestionCategory, HvQuestionEntry[]]> {
  return (Object.keys(HV_QUESTION_CATEGORY_LABELS) as HvQuestionCategory[]).map((category) => [
    category,
    HV_QUESTION_WORDS.filter((entry) => entry.category === category),
  ])
}

function relatedSentencesFor(lemma: string, sentences: SentencebankSentence[]): SentencebankSentence[] {
  return sentences.filter((sentence) => matchedTokenIndexes(lemma, sentence).length > 0)
}

function matchedTokenIndexes(lemma: string, sentence: SentencebankSentence): number[] {
  const normalizedLemma = normalizeSearchWord(lemma)
  return (sentence.tokens ?? [])
    .filter((token) => (
      normalizeSearchWord(token.stored_lemma ?? token.lemma_candidate ?? "") === normalizedLemma
      || normalizeSearchWord(token.surface_form) === normalizedLemma
    ))
    .map((token) => token.token_index)
}
