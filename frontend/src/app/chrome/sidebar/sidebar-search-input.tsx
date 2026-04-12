import { useMemo, type KeyboardEventHandler } from "react"

import {
  SENTENCE_VERIFY_MAX_CHARS,
  hasMultipleWords,
  type SentenceVerificationErrorItem,
  type VerifySentenceResponse,
} from "@/app/core"
import { CommandInput } from "@/components/ui/command"
import { cn } from "@/lib/utils"

type TextSegment = {
  text: string
  message: string | null
}

function isWhitespace(char: string) {
  return /\s/u.test(char)
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
    return [{
      start,
      end: lastCharacterIndex + 1,
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
  sentenceVerification: VerifySentenceResponse | null
  onValueChange: (value: string) => void
  onKeyDown?: KeyboardEventHandler<HTMLInputElement>
}

export function SidebarSearchInput({
  value,
  sentenceVerification,
  onValueChange,
  onKeyDown,
}: SidebarSearchInputProps) {
  const trimmedValue = value.trim()
  const rawErrors = useMemo(
    () => mapVerificationErrorsToRawInput(value, sentenceVerification?.errors ?? []),
    [sentenceVerification?.errors, value],
  )
  const segments = useMemo(() => buildSegments(value, rawErrors), [rawErrors, value])
  const charactersRemaining = SENTENCE_VERIFY_MAX_CHARS - trimmedValue.length
  const shouldShowCounter = Boolean(trimmedValue) && (hasMultipleWords(trimmedValue) || trimmedValue.length >= 35)
  const usedCharacters = trimmedValue.length
  const counterText = `${usedCharacters}/${SENTENCE_VERIFY_MAX_CHARS}`
  const overlay = rawErrors.length > 0 ? (
    <div data-testid="sentence-search-input-overlay">
      {segments.map((segment, index) => (
        segment.message ? (
          <span
            key={`${segment.text}-${index}`}
            className="underline decoration-red-500 decoration-wavy"
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

  return (
    <CommandInput
      placeholder="Search words and notes..."
      value={value}
      onValueChange={onValueChange}
      onKeyDown={onKeyDown}
      aria-label="command search"
      overlay={overlay}
      concealValue={Boolean(overlay)}
      suffix={shouldShowCounter ? (
        <span
          className={cn(
            "text-muted-foreground inline-flex h-4 items-center justify-end text-[10px] leading-none font-medium tracking-tight tabular-nums",
            charactersRemaining < 0 ? "text-red-500" : "",
          )}
          data-testid="sentence-search-character-counter"
          title={
            charactersRemaining >= 0
              ? `${charactersRemaining} characters remaining`
              : `${Math.abs(charactersRemaining)} characters over`
          }
        >
          {counterText}
        </span>
      ) : null}
    />
  )
}
