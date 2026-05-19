import { X } from "lucide-react"
import { useMemo, type KeyboardEventHandler } from "react"

import {
  SENTENCE_VERIFY_MAX_CHARS,
  type SentenceSearchPreviewResponse,
  type SentenceVerificationErrorItem,
} from "@/app/core"
import { Button } from "@/components/ui/button"
import { CommandInput } from "@/components/ui/command"

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
  sentenceSearchPreview: SentenceSearchPreviewResponse | null
  onValueChange: (value: string) => void
  onCancelSearch: () => void
  onKeyDown?: KeyboardEventHandler<HTMLElement>
}

export function SidebarSearchInput({
  value,
  sentenceSearchPreview,
  onValueChange,
  onCancelSearch,
  onKeyDown,
}: SidebarSearchInputProps) {
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

  return (
    <CommandInput
      placeholder="Search words..."
      value={value}
      onValueChange={onValueChange}
      onKeyDown={onKeyDown as KeyboardEventHandler<HTMLInputElement>}
      aria-label="command search"
      overlay={overlay}
      concealValue={Boolean(overlay)}
      suffix={(
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label="Cancel search"
          className="rounded-full"
          onClick={onCancelSearch}
        >
          <X />
        </Button>
      )}
      multiline
      autoFocus
      maxLength={SENTENCE_VERIFY_MAX_CHARS}
    />
  )
}
