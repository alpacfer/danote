import { type AnalyzedToken } from "@/app/core/types-api"

export function previewText(value: string, maxLength = 180): string {
  const normalized = value.replace(/\s+/gu, " ").trim()
  if (!normalized) {
    return "No text saved."
  }
  if (normalized.length <= maxLength) {
    return normalized
  }
  return `${normalized.slice(0, maxLength - 1)}...`
}

export function finalizedAnalysisText(text: string): string {
  if (!text) {
    return ""
  }

  const hadTrailingWhitespace = /\s$/u.test(text)
  const trimmedRight = text.replace(/\s+$/u, "")
  if (!trimmedRight) {
    return ""
  }

  if (hadTrailingWhitespace) {
    return trimmedRight
  }

  if (/[\p{L}\p{N}]$/u.test(trimmedRight)) {
    return trimmedRight.replace(/[\p{L}\p{N}'’-]+$/u, "").trimEnd()
  }

  return trimmedRight
}

export function addLoadingKey(token: AnalyzedToken): string {
  return `${token.normalized_token || token.surface_token}:${token.classification}`
}

export function normalizeWordKey(value: string): string {
  return value.normalize("NFKC").toLocaleLowerCase()
}

export function normalizePhraseKey(value: string): string {
  return normalizeWordKey(value).replace(/\s+/gu, " ").trim()
}

export function normalizeSearchWord(value: string): string {
  return normalizePhraseKey(value)
}

export function normalizeSentenceText(value: string): string {
  return value.replace(/\s+/gu, " ").trim()
}

export function formatSentenceTranslation(value: string | null | undefined): string | null {
  if (typeof value !== "string") {
    return null
  }

  const cleaned = normalizeSentenceText(value).replace(/\.$/u, "").trimEnd()
  if (!cleaned) {
    return null
  }
  return cleaned
}

export function isShortLetterWord(value: string): boolean {
  const cleaned = value.trim()
  if (!cleaned) {
    return false
  }

  const letters = Array.from(cleaned).filter((character) => /\p{L}/u.test(character)).length
  if (letters === 0 || letters >= 3) {
    return false
  }

  return /^[\p{L}\-'’]+$/u.test(cleaned)
}

const ALLOWED_SHORT_SEARCH_WORDS = new Set([
  "er",
  "på",
  "at",
  "og",
  "en",
  "et",
  "i",
  "is",
  "be",
  "on",
  "in",
  "to",
])

export function isBlockedShortSearchWord(value: string): boolean {
  const normalized = normalizeSearchWord(value)
  return isShortLetterWord(normalized) && !ALLOWED_SHORT_SEARCH_WORDS.has(normalized)
}

export function isAtVerbCandidate(value: string): boolean {
  const parts = value.split(/\s+/u).filter(Boolean)
  return parts.length === 2 && parts[0].toLowerCase() === "at"
}

export function hasMultipleWords(value: string): boolean {
  if (isAtVerbCandidate(value)) {
    return false
  }
  return value.split(/\s+/u).filter(Boolean).length >= 2
}

export function translationKeysForToken(token: Pick<AnalyzedToken, "surface_token" | "normalized_token">): string[] {
  const keys = [token.normalized_token, token.surface_token]
    .filter((value): value is string => Boolean(value && value.trim()))
    .map((value) => normalizeWordKey(value))

  return [...new Set(keys)]
}
