import { type VerificationErrorDetail } from "@/app/core/types-ui"
import { normalizeSearchWord } from "@/app/core/text-utils"

export function isPlayableAudioContentType(contentType: string | null): boolean {
  if (!contentType) {
    return true
  }
  const normalized = contentType.toLocaleLowerCase()
  return (
    normalized.includes("audio/wav") ||
    normalized.includes("audio/x-wav") ||
    normalized.includes("audio/mpeg") ||
    normalized.includes("audio/mp3") ||
    normalized.includes("audio/ogg") ||
    normalized.includes("audio/webm") ||
    normalized.includes("audio/mp4") ||
    normalized.includes("audio/aac") ||
    normalized.includes("audio/flac")
  )
}

export function isUnsupportedAudioError(error: unknown): boolean {
  if (!(error instanceof Error)) {
    return false
  }
  const normalized = error.message.toLocaleLowerCase()
  return (
    normalized.includes("no supported source was found") ||
    normalized.includes("notsupportederror") ||
    normalized.includes("unsupported pronunciation format")
  )
}

export function compactMessage(value: string | null | undefined): string {
  return (value ?? "").replace(/\s+/gu, " ").trim()
}

export function normalizeVerificationMessage(message: string | null | undefined): string {
  const normalized = compactMessage(message)
  if (!normalized) {
    return ""
  }
  return normalized.replace(/^verification task failed:\s*/iu, "")
}

export function buildVerificationErrorDetail(payload: {
  provider: string | null | undefined
  status: "flagged" | "error"
  message: string | null | undefined
  composedWordCount?: number | null
  storedSurfaceForm?: string | null
  meaningId?: number | null
  problem?: string | null
  changeToImplement?: string | null
  suggestedActions?: Array<{
    action_type: "fix_translation" | "fix_gloss" | "fix_variations" | "move_to_meaning_section" | "move_to_lemma"
    reason?: string | null
    english_translation?: string | null
    gloss?: string | null
    singular_definite_form?: string | null
    plural_indefinite_form?: string | null
    plural_definite_form?: string | null
    target_meaning_id?: number | null
    target_lemma?: string | null
    target_meaning_key?: string | null
    target_gloss?: string | null
    target_english_translation?: string | null
    target_pos_tag?: string | null
    target_morphology?: string | null
  }> | null
}): VerificationErrorDetail {
  const providerName = payload.provider?.trim() || "gemini"
  const detail = normalizeVerificationMessage(payload.message)
  const normalizedSurface = normalizeSearchWord(payload.storedSurfaceForm ?? "") || null
  const meaningId = payload.meaningId ?? null
  const explicitProblem = compactMessage(payload.problem)
  const explicitChange = compactMessage(payload.changeToImplement)
  const suggestedActions = payload.suggestedActions ?? []

  if (payload.status === "flagged") {
    const count = payload.composedWordCount ?? 0
    const composedHint = count > 1 ? ` It appears to be treated as a composed word (${count} parts).` : ""
    return {
      provider: providerName,
      status: "flagged",
      problem:
        explicitProblem ||
        (detail
          ? `Gemini flagged this entry as incorrect: ${detail}.`
          : `Gemini flagged this entry as incorrect.${composedHint}`),
      changeToImplement:
        explicitChange ||
        "Review lemma/surface form and translation, then update the entry to a valid Danish word form.",
      rawMessage: detail || explicitProblem || "Gemini flagged the entry as incorrect.",
      storedSurfaceForm: normalizedSurface,
      meaningId,
      suggestedActions,
    }
  }

  if (/missing|required|api key|not configured/iu.test(detail)) {
    return {
      provider: providerName,
      status: "error",
      problem: explicitProblem || detail || "Gemini verification could not run because configuration is missing.",
      changeToImplement:
        explicitChange ||
        "Set the Gemini verification API key in Developer settings or backend env, then retry verification.",
      rawMessage: detail || explicitProblem || "Missing Gemini verification configuration.",
      storedSurfaceForm: normalizedSurface,
      meaningId,
      suggestedActions,
    }
  }

  if (/quota|rate limit|429|too many requests/iu.test(detail)) {
    return {
      provider: providerName,
      status: "error",
      problem: explicitProblem || detail || "Gemini verification request was rate-limited.",
      changeToImplement:
        explicitChange || "Retry verification after a short delay, or use an API key with higher quota.",
      rawMessage: detail || explicitProblem || "Gemini verification request was rate-limited.",
      storedSurfaceForm: normalizedSurface,
      meaningId,
      suggestedActions,
    }
  }

  return {
    provider: providerName,
    status: "error",
    problem: explicitProblem || detail || "Gemini verification failed unexpectedly.",
    changeToImplement:
      explicitChange || "Check verification input and retry. If it persists, inspect backend logs for provider errors.",
    rawMessage: detail || explicitProblem || "Gemini verification failed unexpectedly.",
    storedSurfaceForm: normalizedSurface,
    meaningId,
    suggestedActions,
  }
}
