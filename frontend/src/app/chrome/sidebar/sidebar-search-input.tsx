import { X, ChevronDown } from "lucide-react"
import { useMemo, useState, useEffect, type KeyboardEventHandler } from "react"

import {
  SENTENCE_VERIFY_MAX_CHARS,
  type SentenceSearchPreviewResponse,
} from "@/app/core"
import type { SearchLanguageMode } from "@/app/chrome/sidebar/sidebar-search-types"
import { Button } from "@/components/ui/button"
import { CommandInput } from "@/components/ui/command"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

import {
  ENGLISH_SEARCH_PHRASES,
  DANISH_SEARCH_PHRASES,
  shuffleArray,
} from "./sidebar-search-constants"
import {
  mapVerificationErrorsToRawInput,
  buildSegments,
} from "./sidebar-search-helpers"

type SidebarSearchInputProps = {
  value: string
  searchLanguageMode: SearchLanguageMode
  onLanguageModeChange: (mode: SearchLanguageMode) => void
  sentenceSearchPreview: SentenceSearchPreviewResponse | null
  onValueChange: (value: string) => void
  onCloseSearch: () => void
  onKeyDown?: KeyboardEventHandler<HTMLElement>
  wordbankDidYouMean?: string | null
  corDidYouMean?: string | null
  enDidYouMean?: string | null
  isSentenceMode?: boolean
}

export function SidebarSearchInput({
  value,
  searchLanguageMode,
  onLanguageModeChange,
  sentenceSearchPreview,
  onValueChange,
  onCloseSearch,
  onKeyDown,
  wordbankDidYouMean = null,
  corDidYouMean = null,
  enDidYouMean = null,
  isSentenceMode = false,
}: SidebarSearchInputProps) {
  const phrases = searchLanguageMode === "en" ? ENGLISH_SEARCH_PHRASES : DANISH_SEARCH_PHRASES
  const shuffledPhrases = useMemo(() => shuffleArray(phrases), [phrases])

  const [phraseIndex, setPhraseIndex] = useState(0)
  const [displayText, setDisplayText] = useState("")
  const [isDeleting, setIsDeleting] = useState(false)

  const [prevValue, setPrevValue] = useState(value)
  if (value !== prevValue) {
    setPrevValue(value)
    if (value === "") {
      setPhraseIndex(0)
      setDisplayText("")
      setIsDeleting(false)
    }
  }

  const isTest =
    (typeof import.meta !== "undefined" && import.meta.env?.MODE === "test") ||
    (typeof window !== "undefined" && "__VITEST__" in window)

  useEffect(() => {
    if (isTest || shuffledPhrases.length === 0) return

    const currentPhrase = shuffledPhrases[phraseIndex]
    let timer: ReturnType<typeof setTimeout>

    const tick = () => {
      if (!isDeleting) {
        if (displayText.length < currentPhrase.length) {
          setDisplayText(currentPhrase.substring(0, displayText.length + 1))
          timer = setTimeout(tick, 90)
        } else {
          timer = setTimeout(() => {
            setIsDeleting(true)
          }, 4500)
        }
      } else if (displayText.length > 0) {
        setDisplayText(currentPhrase.substring(0, displayText.length - 1))
        timer = setTimeout(tick, 35)
      } else {
        setIsDeleting(false)
        setPhraseIndex((prev) => (prev + 1) % shuffledPhrases.length)
        timer = setTimeout(() => {}, 500)
      }
    }

    timer = setTimeout(tick, isDeleting ? 35 : displayText.length === 0 ? 500 : 90)

    return () => clearTimeout(timer)
  }, [displayText, isDeleting, phraseIndex, shuffledPhrases, isTest])

  const rawErrors = useMemo(
    () => {
      if (isSentenceMode) {
        const previewErrors = sentenceSearchPreview?.query_language === "en"
          ? []
          : sentenceSearchPreview?.errors ?? []
        return mapVerificationErrorsToRawInput(value, previewErrors)
      } else {
        const dym = wordbankDidYouMean || corDidYouMean || enDidYouMean
        if (dym && value.trim() && value.trim().toLowerCase() !== dym.toLowerCase()) {
          return [{
            start: 0,
            end: value.length,
            message: `Did you mean "${dym}"?`,
          }]
        }
        return []
      }
    },
    [isSentenceMode, sentenceSearchPreview, value, wordbankDidYouMean, corDidYouMean, enDidYouMean],
  )

  const segments = useMemo(() => buildSegments(value, rawErrors), [rawErrors, value])

  const segmentsWithRanges = useMemo(() => {
    return segments.map((segment, index) => {
      const start = segments.slice(0, index).reduce((sum, s) => sum + s.text.length, 0)
      const end = start + segment.text.length
      return { ...segment, start, end }
    })
  }, [segments])

  const overlay = rawErrors.length > 0 ? (
    <div data-testid="sentence-search-input-overlay">
      {segmentsWithRanges.map((segment, index) => (
        segment.message ? (
          <span
            key={`${segment.text}-${index}`}
            className="underline decoration-[var(--danote-typo-underline)] decoration-[1.5px] decoration-wavy underline-offset-[3px] cursor-pointer hover:opacity-80 transition-all pointer-events-auto"
            style={{ textDecorationStyle: "wavy" }}
            title={segment.message}
            onClick={(e) => {
              e.preventDefault()
              e.stopPropagation()
              if (!isSentenceMode) {
                const dym = wordbankDidYouMean || corDidYouMean || enDidYouMean
                if (dym) {
                  onValueChange(dym)
                  return
                }
              }
              const correctedText = sentenceSearchPreview?.corrected_text
              if (correctedText) {
                const wordsBefore = value.substring(0, segment.start).match(/[\p{L}\p{N}'’-]+/gu) || []
                const origIndex = wordsBefore.length
                const corrWords = correctedText.match(/[\p{L}\p{N}'’-]+/gu) || []
                const matchWord = corrWords[origIndex]
                if (matchWord) {
                  const before = value.substring(0, segment.start)
                  const after = value.substring(segment.end)
                  onValueChange(`${before}${matchWord}${after}`)
                }
              }
            }}
          >
            {segment.text}
          </span>
        ) : (
          <span key={`${segment.text}-${index}`}>{segment.text}</span>
        )
      ))}
    </div>
  ) : null

  const hasValue = value.length > 0
  const toggleLanguage = () => {
    setPhraseIndex(0)
    setDisplayText("")
    setIsDeleting(false)
    onLanguageModeChange(searchLanguageMode === "da" ? "en" : "da")
  }

  const desktopLanguageButton = (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          type="button"
          variant="outline"
          className="h-7 w-7 rounded-sm text-[10px] font-bold tracking-wider transition-all duration-200 select-none shadow-none border-border bg-background hover:bg-accent hover:text-accent-foreground text-foreground shrink-0 p-0 flex items-center justify-center self-center"
          onClick={toggleLanguage}
          onMouseDown={(e) => {
            e.preventDefault()
          }}
          onPointerDown={(e) => {
            e.preventDefault()
          }}
          aria-label={
            searchLanguageMode === "da"
              ? "Switch to English search"
              : "Switch to Danish search"
          }
        >
          {searchLanguageMode === "da" ? "DA" : "EN"}
        </Button>
      </TooltipTrigger>
      <TooltipContent side="left" align="center" className="text-xs">
        {searchLanguageMode === "da"
          ? "Danish search. Click to switch to English."
          : "English search. Click to switch to Danish."}
      </TooltipContent>
    </Tooltip>
  )

  const responsiveLanguageButton = (
    <>
      <div className="max-md:hidden flex items-center justify-center self-center shrink-0">
        {desktopLanguageButton}
      </div>
    </>
  )

  return (
    <div className="flex flex-col w-full">
      <div
        data-slot="sidebar-search-input-row"
        className="flex items-center [&_[data-slot=command-input-wrapper]]:flex-1 max-md:w-full max-md:gap-3 max-md:px-4 max-md:py-3 max-md:pb-[calc(0.75rem+env(safe-area-inset-bottom))] max-md:bg-popover max-md:[&_[data-slot=command-input-wrapper]]:m-0 max-md:[&_[data-slot=command-input-wrapper]]:h-11 max-md:[&_[data-slot=command-input-wrapper]]:min-h-11 max-md:[&_[data-slot=command-input-wrapper]]:rounded-2xl max-md:[&_[data-slot=command-input-wrapper]]:bg-background max-md:[&_[data-slot=command-input-wrapper]]:border-border max-md:[&_[data-slot=command-input-wrapper]]:shadow-lg max-md:[&_[data-slot=command-input-wrapper]]:pr-3 max-md:[&_[data-slot=command-input-wrapper]]:pl-3 max-md:[&_[data-slot=command-input-wrapper]_textarea]:py-2.5 max-md:[&_[data-slot=command-input-wrapper]_textarea]:text-base max-md:[&_[data-slot=command-input-overlay]]:py-2.5 max-md:[&_[data-slot=command-input-overlay]]:text-base"
      >
        {/* Mobile Language Toggle Button (Visible only on mobile) */}
        <button
          type="button"
          className="flex size-11 shrink-0 items-center justify-center rounded-full border border-border bg-background shadow-lg text-foreground font-semibold text-sm transition-all duration-200 active:scale-90 md:hidden"
          onClick={toggleLanguage}
          onMouseDown={(e) => {
            e.preventDefault()
          }}
          onPointerDown={(e) => {
            e.preventDefault()
          }}
          aria-label={
            searchLanguageMode === "da"
              ? "Switch to English search"
              : "Switch to Danish search"
          }
        >
          {searchLanguageMode === "da" ? "DA" : "EN"}
        </button>

        {/* Main Pill Search Input */}
        <div className="min-w-0 flex-1 md:contents">
          <CommandInput
            placeholder={isTest ? phrases[0] : displayText}
            value={value}
            onValueChange={onValueChange}
            onKeyDown={onKeyDown as KeyboardEventHandler<HTMLInputElement>}
            aria-label="command search"
            overlay={overlay}
            concealValue={Boolean(overlay)}
            icon={responsiveLanguageButton}
            suffix={(
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label="Clear search"
                className={cn("rounded-full", hasValue ? "" : "invisible pointer-events-none")}
                onClick={() => onValueChange("")}
                onMouseDown={(e) => {
                  e.preventDefault()
                }}
                onPointerDown={(e) => {
                  e.preventDefault()
                }}
              >
                <X />
              </Button>
            )}
            multiline
            autoFocus
            maxLength={SENTENCE_VERIFY_MAX_CHARS}
          />
        </div>

        {/* Mobile Close Button (Visible only on mobile) */}
        <button
          type="button"
          aria-label="Close search"
          className="flex size-11 shrink-0 items-center justify-center rounded-full border border-border bg-background shadow-lg text-muted-foreground transition-all duration-200 active:scale-90 md:hidden"
          onClick={onCloseSearch}
        >
          <ChevronDown className="size-5" />
        </button>
      </div>

    </div>
  )
}
