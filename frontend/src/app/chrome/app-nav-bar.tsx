import { useMemo } from "react"
import { ArrowLeft, ArrowRight } from "lucide-react"

import { type SentencebankSentence } from "@/app/core"
import { type NavEntry } from "@/app/hooks/app/use-section-navigation"
import { parseHvQuestionSentinel } from "@/app/sections/wordbank/hv-questions/hv-question-data"
import { parseNumbersSentinel } from "@/app/sections/wordbank/numbers/numbers-data"
import { parsePronounSentinel, PRONOUN_CATEGORY_LABELS } from "@/app/sections/wordbank/pronouns/pronouns-data"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

type SentenceLookup = Map<number, string>

function describeLemma(selectedLemma: string): string {
  if (parseHvQuestionSentinel(selectedLemma)) return "HV Question Words"
  if (parseNumbersSentinel(selectedLemma)) return "Numbers"
  const pronounCategory = parsePronounSentinel(selectedLemma)
  if (pronounCategory) return PRONOUN_CATEGORY_LABELS[pronounCategory]
  return selectedLemma
}

function describeNavEntry(entry: NavEntry, sentenceLookup: SentenceLookup): string {
  if (entry.section === "developer") return "Developer"
  if (entry.section === "wordbank") {
    if (entry.selectedLemma) return describeLemma(entry.selectedLemma)
    return "Wordbank"
  }
  if (entry.pendingSentence) {
    const text = entry.pendingSentence.source_text.trim()
    return text || "New sentence"
  }
  if (entry.selectedSentenceId != null) {
    const text = sentenceLookup.get(entry.selectedSentenceId)?.trim()
    return text || "Sentence"
  }
  return "Sentencebank"
}

export type AppNavBarProps = {
  currentEntry: NavEntry
  previousEntry: NavEntry | null
  nextEntry: NavEntry | null
  canGoBack: boolean
  canGoForward: boolean
  onBack: () => void
  onForward: () => void
  sentences: SentencebankSentence[]
}

export function AppNavBar({
  currentEntry,
  previousEntry,
  nextEntry,
  canGoBack,
  canGoForward,
  onBack,
  onForward,
  sentences,
}: AppNavBarProps) {
  const sentenceLookup = useMemo(() => {
    const map: SentenceLookup = new Map()
    for (const sentence of sentences) {
      map.set(sentence.id, sentence.source_text)
    }
    return map
  }, [sentences])

  const currentLabel = describeNavEntry(currentEntry, sentenceLookup)
  const previousLabel = previousEntry ? describeNavEntry(previousEntry, sentenceLookup) : null
  const nextLabel = nextEntry ? describeNavEntry(nextEntry, sentenceLookup) : null

  return (
    <TooltipProvider delayDuration={200}>
      <nav
        aria-label="Section navigation"
        className="flex w-full min-w-0 items-center gap-3"
      >
        <div className="flex shrink-0 items-center gap-1">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={onBack}
                disabled={!canGoBack}
                aria-label={previousLabel ? `Back to ${previousLabel}` : "Back"}
              >
                <ArrowLeft className="size-4" aria-hidden />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              {previousLabel ? `Back to ${previousLabel}` : "No previous page"}
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={onForward}
                disabled={!canGoForward}
                aria-label={nextLabel ? `Forward to ${nextLabel}` : "Forward"}
              >
                <ArrowRight className="size-4" aria-hidden />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              {nextLabel ? `Forward to ${nextLabel}` : "No next page"}
            </TooltipContent>
          </Tooltip>
        </div>

        <div
          aria-current="page"
          className={cn(
            "min-w-0 flex-1 truncate text-left text-2xl leading-[1.1] font-semibold tracking-tight",
          )}
        >
          {currentLabel}
        </div>
      </nav>
    </TooltipProvider>
  )
}
