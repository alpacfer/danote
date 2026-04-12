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

  const highlightedTokenIndexSet = new Set(highlightedTokenIndexes)
  const segments: ReactNode[] = []
  let cursor = 0

  for (const token of tokens) {
    const tokenText = token.surface_form
    if (!tokenText) {
      continue
    }

    const tokenStart = sourceText.indexOf(tokenText, cursor)
    if (tokenStart < 0) {
      return <>{sourceText}</>
    }

    if (tokenStart > cursor) {
      segments.push(sourceText.slice(cursor, tokenStart))
    }

    const renderedToken = sourceText.slice(tokenStart, tokenStart + tokenText.length)
    if (highlightedTokenIndexSet.has(token.token_index)) {
      segments.push(
        <span
          key={`sentence-highlight-${token.token_index}`}
          className={highlightClassName}
        >
          {renderedToken}
        </span>,
      )
    } else {
      segments.push(renderedToken)
    }

    cursor = tokenStart + tokenText.length
  }

  if (cursor < sourceText.length) {
    segments.push(sourceText.slice(cursor))
  }

  return <>{segments}</>
}
