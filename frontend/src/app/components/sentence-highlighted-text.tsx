import type { ReactNode } from "react"

import type { SentenceTokenCard } from "@/app/core"

type SentenceHighlightedTextProps = {
  sourceText: string
  tokens?: SentenceTokenCard[]
  highlightedTokenIndexes?: number[]
  highlightClassName?: string
}

export function SentenceHighlightedText({
  sourceText,
  tokens = [],
  highlightedTokenIndexes = [],
  highlightClassName = "underline decoration-2 underline-offset-2",
}: SentenceHighlightedTextProps) {
  if (highlightedTokenIndexes.length === 0 || tokens.length === 0) {
    return <>{sourceText}</>
  }

  // Extract all word tokens and their character positions in sourceText using regex
  const wordRegex = /[\p{L}\p{N}_]+(?:['’.-][\p{L}\p{N}_]+)*/gu
  const sourceWords: { text: string; start: number; end: number; matched: boolean }[] = []
  let match
  while ((match = wordRegex.exec(sourceText)) !== null) {
    sourceWords.push({
      text: match[0],
      start: match.index,
      end: match.index + match[0].length,
      matched: false,
    })
  }

  // Map token index to list of character ranges
  const tokenRangesMap = new Map<number, { start: number; end: number }[]>()

  for (const token of tokens) {
    const tokenText = token.surface_form
    if (!tokenText) continue

    // Split space-separated MWEs into individual subwords
    const tokenSubWords = tokenText.split(/\s+/).filter(Boolean)
    const ranges: { start: number; end: number }[] = []

    for (const subWord of tokenSubWords) {
      const normalizedSub = subWord.toLowerCase()
      // Find the first unmatched word that matches subWord
      const foundWord = sourceWords.find(sw => !sw.matched && sw.text.toLowerCase() === normalizedSub)
      if (foundWord) {
        foundWord.matched = true
        ranges.push({ start: foundWord.start, end: foundWord.end })
      } else {
        // Fallback: search anywhere in sourceText using indexOf
        const idx = sourceText.toLowerCase().indexOf(normalizedSub)
        if (idx >= 0) {
          ranges.push({ start: idx, end: idx + subWord.length })
        }
      }
    }

    if (ranges.length > 0) {
      tokenRangesMap.set(token.token_index, ranges)
    }
  }

  // Collect all ranges to highlight
  const highlightRanges: { start: number; end: number }[] = []
  for (const idx of highlightedTokenIndexes) {
    const ranges = tokenRangesMap.get(idx)
    if (ranges) {
      highlightRanges.push(...ranges)
    }
  }

  if (highlightRanges.length === 0) {
    return <>{sourceText}</>
  }

  // Sort and merge highlight ranges
  highlightRanges.sort((a, b) => a.start - b.start)
  const mergedRanges: { start: number; end: number }[] = []
  for (const r of highlightRanges) {
    if (mergedRanges.length === 0) {
      mergedRanges.push(r)
    } else {
      const last = mergedRanges[mergedRanges.length - 1]
      if (r.start <= last.end) {
        last.end = Math.max(last.end, r.end)
      } else {
        mergedRanges.push(r)
      }
    }
  }

  // Reassemble final segments wrapping highlighted parts in spans
  const segments: ReactNode[] = []
  let cursor = 0
  for (let i = 0; i < mergedRanges.length; i++) {
    const r = mergedRanges[i]
    if (r.start > cursor) {
      segments.push(sourceText.slice(cursor, r.start))
    }
    segments.push(
      <span key={`highlight-${i}`} className={highlightClassName}>
        {sourceText.slice(r.start, r.end)}
      </span>,
    )
    cursor = r.end
  }
  if (cursor < sourceText.length) {
    segments.push(sourceText.slice(cursor))
  }

  return <>{segments}</>
}
