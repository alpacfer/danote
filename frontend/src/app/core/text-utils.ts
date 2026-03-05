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

export function hasMultipleWords(value: string): boolean {
  return value.split(/\s+/u).filter(Boolean).length >= 2
}

export function translationKeysForToken(token: Pick<AnalyzedToken, "surface_token" | "normalized_token">): string[] {
  const keys = [token.normalized_token, token.surface_token]
    .filter((value): value is string => Boolean(value && value.trim()))
    .map((value) => normalizeWordKey(value))

  return [...new Set(keys)]
}
