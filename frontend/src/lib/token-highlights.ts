export type HighlightClassification = "known" | "new" | "variation" | "typo_likely"

export type HighlightSpan = {
  from: number
  to: number
  classification: HighlightClassification
  tokenIndex: number
}

type HighlightableToken = {
  surface_token: string
  normalized_token: string
  classification: "known" | "variation" | "typo_likely" | "uncertain" | "new"
}

type TextTokenSpan = {
  token: string
  from: number
  to: number
}

const WORDLIKE_PATTERN = /[\p{L}\p{N}'’-]+/gu

export function getTokenSpansFromText(text: string): TextTokenSpan[] {
  if (!text) {
    return []
  }

  const spans: TextTokenSpan[] = []
  const matches = text.matchAll(WORDLIKE_PATTERN)

  for (const match of matches) {
    const token = match[0]
    const from = match.index
    if (typeof from !== "number") {
      continue
    }
    spans.push({
      token,
      from,
      to: from + token.length,
    })
  }

  return spans
}

function comparable(value: string): string {
  return value
    .normalize("NFKC")
    .toLocaleLowerCase()
    .replace(/’/gu, "'")
}

function isHighlightClassification(value: HighlightableToken["classification"]): value is HighlightClassification {
  return value === "known" || value === "new" || value === "variation" || value === "typo_likely"
}

function spanMatchesToken(span: TextTokenSpan, token: HighlightableToken): boolean {
  const spanComparable = comparable(span.token)
  return (
    spanComparable === comparable(token.surface_token) ||
    spanComparable === comparable(token.normalized_token)
  )
}

export function mapAnalyzedTokensToHighlights(
  text: string,
  tokens: HighlightableToken[],
): HighlightSpan[] {
  if (!text || tokens.length === 0) {
    return []
  }

  const textSpans = getTokenSpansFromText(text)
  if (textSpans.length === 0) {
    return []
  }

  const highlights: HighlightSpan[] = []
  let cursor = 0

  for (const [tokenIndex, token] of tokens.entries()) {
    let matchedIndex = -1

    for (let index = cursor; index < textSpans.length; index += 1) {
      if (spanMatchesToken(textSpans[index], token)) {
        matchedIndex = index
        break
      }
    }

    if (matchedIndex === -1) {
      continue
    }

    cursor = matchedIndex + 1
    if (!isHighlightClassification(token.classification)) {
      continue
    }

    const matchedSpan = textSpans[matchedIndex]
    highlights.push({
      from: matchedSpan.from,
      to: matchedSpan.to,
      classification: token.classification,
      tokenIndex,
    })
  }

  return highlights
}
