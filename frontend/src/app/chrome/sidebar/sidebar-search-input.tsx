import { Search, X } from "lucide-react"
import { useMemo, useState, useEffect, type KeyboardEventHandler } from "react"

import { SearchFolioControls } from "@/app/chrome/sidebar/sidebar-search-presentation"
import {
  SENTENCE_VERIFY_MAX_CHARS,
  type SentenceSearchPreviewResponse,
} from "@/app/core"
import type { SearchLanguageMode } from "@/app/chrome/sidebar/sidebar-search-types"
import { Button } from "@/components/ui/button"
import { CommandInput } from "@/components/ui/command"
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

  return (
    <div data-search-composer className="flex w-full flex-col">
      <SearchFolioControls
        searchLanguageMode={searchLanguageMode}
        onLanguageModeChange={(mode) => {
          setPhraseIndex(0)
          setDisplayText("")
          setIsDeleting(false)
          onLanguageModeChange(mode)
        }}
        onCloseSearch={onCloseSearch}
      >
        <CommandInput
          placeholder={isTest ? phrases[0] : displayText}
          value={value}
          onValueChange={onValueChange}
          onKeyDown={onKeyDown as KeyboardEventHandler<HTMLInputElement>}
          aria-label="command search"
          icon={<Search aria-hidden data-search-input-icon />}
          overlay={overlay}
          concealValue={Boolean(overlay)}
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
      </SearchFolioControls>
    </div>
  )
}
