import { buildVerificationErrorDetail, compactMessage } from "@/app/core/audio-verification"
import { normalizeSearchWord } from "@/app/core/text-utils"
import type { LemmaDetailsResponse, VerificationResult } from "@/app/core/types-api"
import type { VerificationErrorDetail, VerificationQueuedDetail, VerificationSuccessDetail } from "@/app/core/types-ui"

export function getSelectedLemmaVerificationResult(args: {
  lemmaDetails: LemmaDetailsResponse | null
  selectedMeaningId: number | null
}): VerificationResult | null {
  return getSelectedLemmaVerificationSelection(args).verification
}

export function getSelectedLemmaVerificationSelection(args: {
  lemmaDetails: LemmaDetailsResponse | null
  selectedMeaningId: number | null
}): {
  meaningId: number | null
  verification: VerificationResult | null
} {
  const { lemmaDetails, selectedMeaningId } = args
  if (!lemmaDetails) {
    return { meaningId: selectedMeaningId, verification: null }
  }
  const directMatch = lemmaDetails.meaning_sections?.find((section) => section.id === selectedMeaningId)?.verification ?? null
  if (directMatch) {
    return { meaningId: selectedMeaningId, verification: directMatch }
  }
  if (selectedMeaningId === null && (lemmaDetails.meaning_sections?.length ?? 0) === 1) {
    return {
      meaningId: lemmaDetails.meaning_sections?.[0]?.id ?? null,
      verification: lemmaDetails.meaning_sections?.[0]?.verification ?? null,
    }
  }
  return { meaningId: selectedMeaningId, verification: lemmaDetails.verification ?? null }
}

export function mapVerificationResultToErrorDetail(
  verification: VerificationResult | null,
  meaningId: number | null,
): VerificationErrorDetail | null {
  if (!verification || (verification.status !== "flagged" && verification.status !== "error")) {
    return null
  }
  return buildVerificationErrorDetail({
    provider: verification.provider,
    status: verification.status,
    message: verification.message,
    composedWordCount: verification.composed_word_count,
    storedSurfaceForm: verification.stored_surface_form,
    meaningId,
    problem: verification.problem,
    changeToImplement: verification.change_to_implement,
    suggestedActions: verification.suggested_actions,
  })
}

export function mapVerificationResultToSuccessDetail(
  verification: VerificationResult | null,
  meaningId: number | null,
): VerificationSuccessDetail | null {
  if (!verification || verification.status !== "verified") {
    return null
  }
  return {
    provider: verification.provider?.trim() || "gemini",
    rawMessage: compactMessage(verification.message) || "Gemini verified this word.",
    storedSurfaceForm: normalizeSearchWord(verification.stored_surface_form ?? "") || null,
    meaningId,
    verifiedAt: verification.completed_at || verification.requested_at || new Date().toISOString(),
  }
}

export function mapVerificationResultToQueuedDetail(
  verification: VerificationResult | null,
  meaningId: number | null,
): VerificationQueuedDetail | null {
  if (!verification || verification.status !== "queued") {
    return null
  }
  return {
    provider: verification.provider?.trim() || "gemini",
    storedSurfaceForm: normalizeSearchWord(verification.stored_surface_form ?? "") || null,
    meaningId,
    requestedAt: verification.requested_at || new Date().toISOString(),
  }
}

export function verificationResultSignature(
  verification: VerificationResult | null,
  meaningId: number | null,
): string | null {
  if (!verification) {
    return null
  }
  const timestamp = verification.completed_at || verification.requested_at || ""
  return JSON.stringify({
    meaningId,
    status: verification.status,
    provider: verification.provider,
    message: verification.message,
    requestedAt: verification.requested_at,
    completedAt: verification.completed_at,
    storedSurfaceForm: verification.stored_surface_form,
    timestamp,
    suggestedActions: verification.suggested_actions ?? [],
  })
}
