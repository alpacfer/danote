import type { SentenceVerificationErrorItem } from "@/app/core"

export type TextSegment = {
  text: string
  message: string | null
}

export function isWhitespace(char: string) {
  return /\s/u.test(char)
}

export function isWordCharacter(char: string) {
  return /[\p{L}\p{N}'’-]/u.test(char)
}

export function buildNormalizedToRawIndexMap(rawText: string): number[] {
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

export function mapVerificationErrorsToRawInput(
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

export function buildSegments(text: string, errors: SentenceVerificationErrorItem[]): TextSegment[] {
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
