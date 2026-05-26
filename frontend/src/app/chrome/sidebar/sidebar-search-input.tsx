import { X, ChevronDown } from "lucide-react"
import { useMemo, useState, useEffect, type KeyboardEventHandler } from "react"

import {
  SENTENCE_VERIFY_MAX_CHARS,
  type SentenceSearchPreviewResponse,
  type SentenceVerificationErrorItem,
} from "@/app/core"
import type { SearchLanguageMode } from "@/app/chrome/sidebar/sidebar-search-types"
import { Button } from "@/components/ui/button"
import { CommandInput } from "@/components/ui/command"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

type TextSegment = {
  text: string
  message: string | null
}

function isWhitespace(char: string) {
  return /\s/u.test(char)
}

function isWordCharacter(char: string) {
  return /[\p{L}\p{N}'’-]/u.test(char)
}

function buildNormalizedToRawIndexMap(rawText: string): number[] {
  const map: number[] = []
  let index = 0
  while (index < rawText.length) {
    if (isWhitespace(rawText[index])) {
      const whitespaceStart = index
      while (index < rawText.length && isWhitespace(rawText[index])) {
        index += 1
      }
      if (map.length === 0 || index >= rawText.length) {
        continue
      }
      map.push(whitespaceStart)
      continue
    }
    map.push(index)
    index += 1
  }
  return map
}

function mapVerificationErrorsToRawInput(
  rawText: string,
  errors: SentenceVerificationErrorItem[],
): SentenceVerificationErrorItem[] {
  if (!rawText || errors.length === 0) {
    return []
  }

  const rawIndexMap = buildNormalizedToRawIndexMap(rawText)
  return errors.flatMap((error) => {
    const start = rawIndexMap[error.start]
    const lastCharacterIndex = rawIndexMap[error.end - 1]
    if (
      start == null
      || lastCharacterIndex == null
      || lastCharacterIndex < start
    ) {
      return []
    }
    let expandedStart = start
    let expandedEnd = lastCharacterIndex + 1
    if (isWordCharacter(rawText[start])) {
      while (expandedStart > 0 && isWordCharacter(rawText[expandedStart - 1])) {
        expandedStart -= 1
      }
    }
    if (isWordCharacter(rawText[lastCharacterIndex])) {
      while (expandedEnd < rawText.length && isWordCharacter(rawText[expandedEnd])) {
        expandedEnd += 1
      }
    }
    return [{
      start: expandedStart,
      end: expandedEnd,
      message: error.message,
    }]
  })
}

function buildSegments(text: string, errors: SentenceVerificationErrorItem[]): TextSegment[] {
  if (errors.length === 0) {
    return [{ text, message: null }]
  }

  const sorted = [...errors].sort((left, right) => left.start - right.start)
  const segments: TextSegment[] = []
  let cursor = 0
  for (const error of sorted) {
    const start = Math.max(cursor, Math.min(error.start, text.length))
    const end = Math.max(start, Math.min(error.end, text.length))
    if (start > cursor) {
      segments.push({ text: text.slice(cursor, start), message: null })
    }
    if (end > start) {
      segments.push({
        text: text.slice(start, end),
        message: error.message,
      })
    }
    cursor = end
  }
  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), message: null })
  }
  return segments
}

type SidebarSearchInputProps = {
  value: string
  searchLanguageMode: SearchLanguageMode
  onLanguageModeChange: (mode: SearchLanguageMode) => void
  sentenceSearchPreview: SentenceSearchPreviewResponse | null
  onValueChange: (value: string) => void
  onCloseSearch: () => void
  onKeyDown?: KeyboardEventHandler<HTMLElement>
}

const SEARCH_PHRASES = [
  // --- Original & Funny English Queries ---
  'Search English words (e.g. "pastry")...',
  'Search English verbs (e.g. "to stumble")...',
  'Search English adjectives (e.g. "quirky")...',
  'Search English sentences (e.g. "my dog ate my homework")...',
  'Search English sentences (e.g. "is the bread talking to you?")...',
  'Search English sentences (e.g. "I love learning Danish")...',
  'Search English sentences (e.g. "where is the bakery?")...',
  'Search English idioms (e.g. "when pigs fly")...',
  'Search English idioms (e.g. "spill the beans")...',
  'Search English idioms (e.g. "under the weather")...',

  // --- New Funny English Sentences ---
  'Search English sentences (e.g. "my cat owns the house, I just pay rent")...',
  'Search English sentences (e.g. "why is there a penguin in the kitchen?")...',
  'Search English sentences (e.g. "I came, I saw, I forgot what I was doing")...',
  'Search English sentences (e.g. "aliens stole my homework")...',
  'Search English sentences (e.g. "can I pay you in cookies?")...',
  'Search English sentences (e.g. "I am not lazy, I am in energy-saving mode")...',
  'Search English sentences (e.g. "do you have any gluten-free air?")...',
  'Search English sentences (e.g. "the internet is down, let us talk to each other")...',
  'Search English sentences (e.g. "who let the dogs out?")...',
  'Search English sentences (e.g. "I need coffee to wake up my coffee")...',
  'Search English sentences (e.g. "why do round pizzas come in square boxes?")...',
  'Search English sentences (e.g. "sleeping is my favorite hobby")...',
  'Search English sentences (e.g. "I only speak Danish when I am asleep")...',
  'Search English sentences (e.g. "do not trust a smiling potato")...',
  'Search English sentences (e.g. "the potato in my throat has its own potato")...',
  'Search English sentences (e.g. "who stole my last slice of smørrebrød?")...',
  'Search English sentences (e.g. "my hovercraft is full of eels")...',
  'Search English sentences (e.g. "I am not arguing, I am just explaining why I am right")...',
  'Search English sentences (e.g. "hold my coffee, I am going to try Danish grammar")...',
  'Search English sentences (e.g. "why does the letter Ø look like a forbidden donut?")...',
  'Search English sentences (e.g. "my pronunciation sounds like a wet sponge")...',
  'Search English sentences (e.g. "I am fluent in Danish until someone speaks back to me")...',

  // --- New English Idioms ---
  'Search English idioms (e.g. "kick the bucket")...',
  'Search English idioms (e.g. "cool as a cucumber")...',
  'Search English idioms (e.g. "cry over spilled milk")...',
  'Search English idioms (e.g. "burn the midnight oil")...',
  'Search English idioms (e.g. "elephant in the room")...',
  'Search English idioms (e.g. "barking up the wrong tree")...',
  'Search English idioms (e.g. "it takes two to tango")...',
  'Search English idioms (e.g. "piece of cake")...',

  // --- Original & Funny Danish Queries ---
  'Search words (e.g. "wienerbrød")...',
  'Search inflected forms (e.g. "kameler")...',
  'Search verbs (e.g. "at snuble")...',
  'Search Danish sentences (e.g. "jeg har en fugl i min hat")...',
  'Search Danish sentences (e.g. "jeg taler ikke dansk, jeg spiser bare wienerbrød")...',
  'Search Danish sentences (e.g. "jeg spiser et æble")...',
  'Search Danish idioms (e.g. "håret i postkassen")...',
  'Search Danish idioms (e.g. "det blæser en halv pelikan")...',
  'Search Danish idioms (e.g. "træde i spinaten")...',
  'Search Danish idioms (e.g. "have en ræv bag øret")...',
  'Search Danish idioms (e.g. "ingen ko på isen")...',
  'Search phrasal verbs (e.g. "skrue ned for")...',

  // --- New Funny Danish Sentences ---
  'Search Danish sentences (e.g. "min kat planlægger at overtage verden")...',
  'Search Danish sentences (e.g. "hvorfor kigger du på min tallerken?")...',
  'Search Danish sentences (e.g. "kaffen er varmere end solen")...',
  'Search Danish sentences (e.g. "jeg har glemt mine bukser")...',
  'Search Danish sentences (e.g. "ugler synger ikke i badet")...',
  'Search Danish sentences (e.g. "der er en gorilla i mit klædeskab")...',
  'Search Danish sentences (e.g. "kan du tale langsommere, tak?")...',
  'Search Danish sentences (e.g. "min cykel er punkteret igen")...',
  'Search Danish sentences (e.g. "hvem spiste den sidste kage?")...',
  'Search Danish sentences (e.g. "jeg drikker mælk direkte fra kartonen")...',
  'Search Danish sentences (e.g. "computeren sagde nej")...',
  'Search Danish sentences (e.g. "der er altid plads til wienerbrød")...',
  'Search Danish sentences (e.g. "hvor kan jeg købe en enhjørning?")...',
  'Search Danish sentences (e.g. "jeg forstår intet, men jeg smiler bare")...',
  'Search Danish sentences (e.g. "er det her vejen til månen?")...',
  'Search Danish sentences (e.g. "kartoflen i min hals taler flydende spansk")...',
  'Search Danish sentences (e.g. "der er ugler i mosen og kameler i baghaven")...',
  'Search Danish sentences (e.g. "min hund tror, at den er statsminister")...',
  'Search Danish sentences (e.g. "hvorfor koster denne cykel en hel bondegård?")...',
  'Search Danish sentences (e.g. "jeg spiste to spandauere til morgenmad, hjælp")...',
  'Search Danish sentences (e.g. "skal vi danse med en rød pølse?")...',
  'Search Danish sentences (e.g. "jeg taler flydende jysk efter tre øl")...',
  'Search Danish sentences (e.g. "hvor er mit yndlings-rugbrød henne?")...',
  'Search Danish sentences (e.g. "regnen i Danmark falder mest på cyklisterne")...',
  'Search Danish sentences (e.g. "katten sidder på computeren og koder i Python")...',

  // --- New Funny Danish Idioms ---
  'Search Danish idioms (e.g. "have en skrue løs")...',
  'Search Danish idioms (e.g. "skyde papegøjen")...',
  'Search Danish idioms (e.g. "tage benene på nakken")...',
  'Search Danish idioms (e.g. "slå koldt vand i blodet")...',
  'Search Danish idioms (e.g. "sælge elastik i metermål")...',
  'Search Danish idioms (e.g. "stå med skægget i postkassen")...',
  'Search Danish idioms (e.g. "bide i det sure æble")...',
  'Search Danish idioms (e.g. "have sommerfugle i maven")...',
  'Search Danish idioms (e.g. "tale med store bogstaver")...',
  'Search Danish idioms (e.g. "trække på samme hammel")...',
  'Search Danish idioms (e.g. "få en tudse i halsen")...',
  'Search Danish idioms (e.g. "at gå agurk")...',
  'Search Danish idioms (e.g. "købe katten i sækken")...',
  'Search Danish idioms (e.g. "stå som sild i en tønde")...',
  'Search Danish idioms (e.g. "ikke have en rød reje")...',

  // --- Diverse Danish/English words & pages ---
  'Search words (e.g. "pølsevogn")...',
  'Search words (e.g. "hygge")...',
  'Search verbs (e.g. "at hygge sig")...',
  'Search phrasal verbs (e.g. "finde ud af")...',
  'Search app pages (e.g. "Sentences")...',
  'Search app pages (e.g. "Developer")...',
]
const ENGLISH_SEARCH_PHRASES = SEARCH_PHRASES.filter((phrase) => phrase.includes("English"))
const DANISH_SEARCH_PHRASES = SEARCH_PHRASES.filter((phrase) => !phrase.includes("English"))

function shuffleArray<T>(array: T[]): T[] {
  const shuffled = [...array]
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
  }
  return shuffled
}

export function SidebarSearchInput({
  value,
  searchLanguageMode,
  onLanguageModeChange,
  sentenceSearchPreview,
  onValueChange,
  onCloseSearch,
  onKeyDown,
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

  const isTest = typeof import.meta !== "undefined" && import.meta.env?.MODE === "test"

  useEffect(() => {
    if (isTest || shuffledPhrases.length === 0) return

    const currentPhrase = shuffledPhrases[phraseIndex]
    let timer: ReturnType<typeof setTimeout>

    const tick = () => {
      if (!isDeleting) {
        // Typing phase
        if (displayText.length < currentPhrase.length) {
          setDisplayText(currentPhrase.substring(0, displayText.length + 1))
          timer = setTimeout(tick, 90) // 90ms typing speed
        } else {
          // Pause when fully typed
          timer = setTimeout(() => {
            setIsDeleting(true)
          }, 4500) // 4.5s pause
        }
      } else {
        // Deleting phase
        if (displayText.length > 0) {
          setDisplayText(currentPhrase.substring(0, displayText.length - 1))
          timer = setTimeout(tick, 35) // 35ms deleting speed
        } else {
          // Pause when fully deleted, then move to next
          setIsDeleting(false)
          setPhraseIndex((prev) => (prev + 1) % shuffledPhrases.length)
          timer = setTimeout(() => {}, 500) // 500ms switch pause
        }
      }
    }

    // Set initial timer or active character timer
    if (!isDeleting && displayText.length === 0) {
      timer = setTimeout(tick, 500)
    } else {
      timer = setTimeout(tick, isDeleting ? 35 : 90)
    }

    return () => clearTimeout(timer)
  }, [displayText, isDeleting, phraseIndex, shuffledPhrases, isTest])


  const rawErrors = useMemo(
    () => {
      const previewErrors = sentenceSearchPreview?.query_language === "en"
        ? []
        : sentenceSearchPreview?.errors ?? []
      return mapVerificationErrorsToRawInput(value, previewErrors)
    },
    [sentenceSearchPreview, value],
  )
  const segments = useMemo(() => buildSegments(value, rawErrors), [rawErrors, value])
  const overlay = rawErrors.length > 0 ? (
    <div data-testid="sentence-search-input-overlay">
      {segments.map((segment, index) => (
        segment.message ? (
          <span
            key={`${segment.text}-${index}`}
            className="underline decoration-[var(--danote-typo-underline)] decoration-[1.5px] underline-offset-[3px]"
            title={segment.message}
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

  const toggleLanguageButton = (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          type="button"
          variant="outline"
          className="h-7 w-7 max-md:h-10 max-md:w-10 rounded-sm text-[10px] max-md:text-sm font-bold tracking-wider transition-all duration-200 select-none shadow-none border-border bg-background hover:bg-accent hover:text-accent-foreground text-foreground shrink-0 p-0 flex items-center justify-center self-center"
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
          ? "Searching in Danish. Click to switch to English."
          : "Searching in English. Click to switch to Danish."}
      </TooltipContent>
    </Tooltip>
  )

  return (
    <div data-slot="sidebar-search-input-row" className="flex items-center">
      <div className="min-w-0 flex-1">
        <CommandInput
          placeholder={isTest ? "Search words..." : displayText}
          value={value}
          onValueChange={onValueChange}
          onKeyDown={onKeyDown as KeyboardEventHandler<HTMLInputElement>}
          aria-label="command search"
          overlay={overlay}
          concealValue={Boolean(overlay)}
          icon={toggleLanguageButton}
          suffix={(
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              aria-label="Clear search"
              className={cn("rounded-full", hasValue ? "" : "invisible pointer-events-none")}
              onClick={() => onValueChange("")}
            >
              <X />
            </Button>
          )}
          multiline
          autoFocus
          maxLength={SENTENCE_VERIFY_MAX_CHARS}
        />
      </div>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label="Close search"
        className="hidden max-md:flex max-md:size-9 max-md:shrink-0 max-md:rounded-full max-md:mr-2"
        onClick={onCloseSearch}
      >
        <ChevronDown className="size-5" />
      </Button>
    </div>
  )
}
