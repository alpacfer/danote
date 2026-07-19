import { buildVerificationErrorDetail, compactMessage } from "@/app/core/audio-verification"
import { normalizeSearchWord } from "@/app/core/text-utils"
import type { LemmaDetailsResponse, VerificationResult } from "@/app/core/types-api"
import type {
  VerificationErrorDetail,
  VerificationOverview,
  VerificationQueuedDetail,
  VerificationSuccessDetail,
  VerificationTargetView,
} from "@/app/core/types-ui"

export type MeaningVerificationGate = {
  isLocked: boolean
  label: string
}

export type VerificationTargetRefView = {
  meaningId: number | null
  storedSurfaceForm: string | null
}

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
    rawMessage: genericSuccessMessage(compactMessage(verification.message)),
    storedSurfaceForm: normalizeSearchWord(verification.stored_surface_form ?? "") || null,
    meaningId,
    verifiedAt: verification.completed_at || verification.requested_at || null,
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

function genericSuccessMessage(message: string): string {
  const normalized = message.trim().toLocaleLowerCase()
  if (!normalized || normalized === "ok" || normalized === "verified") {
    return "Verification passed."
  }
  return message
}

export function verificationResultSignature(
  verification: VerificationResult | null,
  meaningId: number | null,
  storedSurfaceForm: string | null = null,
): string | null {
  if (!verification) {
    return null
  }
  const timestamp = verification.completed_at || verification.requested_at || ""
  return JSON.stringify({
    meaningId,
    storedSurfaceForm,
    status: verification.status,
    provider: verification.provider,
    reviewIntent: verification.review_intent,
    message: verification.message,
    requestedAt: verification.requested_at,
    completedAt: verification.completed_at,
    verificationStoredSurfaceForm: verification.stored_surface_form,
    timestamp,
    suggestedActions: verification.suggested_actions ?? [],
  })
}

export function verificationTargetKey(
  lemma: string,
  meaningId: number | null,
  storedSurfaceForm: string | null,
): string {
  const normalizedLemma = normalizeSearchWord(lemma) || lemma
  const normalizedSurface = normalizeSearchWord(storedSurfaceForm ?? "") || null
  return `${normalizedLemma}::${meaningId ?? "root"}::${normalizedSurface ?? "root"}`
}

export function collectLemmaVerificationOverview(
  lemmaDetails: LemmaDetailsResponse | null,
): VerificationOverview {
  const targets = collectLemmaVerificationTargets(lemmaDetails)
  let queuedCount = 0
  let verifiedCount = 0
  let reviewCount = 0
  let totalSuggestedActions = 0

  for (const target of targets) {
    if (target.queuedDetail) {
      queuedCount += 1
    } else if (target.errorDetail) {
      reviewCount += 1
      totalSuggestedActions += target.errorDetail.suggestedActions.length
    } else if (target.successDetail) {
      verifiedCount += 1
    }
  }

  return {
    targets,
    queuedCount,
    verifiedCount,
    reviewCount,
    totalSuggestedActions,
  }
}

export function hasQueuedVerificationTargets(lemmaDetails: LemmaDetailsResponse | null): boolean {
  return collectLemmaVerificationOverview(lemmaDetails).queuedCount > 0
}

export function collectLemmaVerificationTargets(
  lemmaDetails: LemmaDetailsResponse | null,
): VerificationTargetView[] {
  if (!lemmaDetails) {
    return []
  }

  const targets: VerificationTargetView[] = []
  const pushTarget = (
    label: string,
    scopeLabel: string,
    meaningId: number | null,
    storedSurfaceForm: string | null,
    verification: VerificationResult | null | undefined,
  ) => {
    const normalizedSurface = normalizeSearchWord(storedSurfaceForm ?? "") || null
    targets.push({
      key: verificationTargetKey(lemmaDetails.lemma, meaningId, normalizedSurface),
      label,
      scopeLabel,
      meaningId,
      storedSurfaceForm: normalizedSurface,
      verification: verification ?? null,
      errorDetail: mapVerificationResultToErrorDetail(verification ?? null, meaningId),
      successDetail: mapVerificationResultToSuccessDetail(verification ?? null, meaningId),
      queuedDetail: mapVerificationResultToQueuedDetail(verification ?? null, meaningId),
    })
  }

  if (lemmaDetails.verification) {
    pushTarget(lemmaDetails.lemma, "Lemma", null, null, lemmaDetails.verification)
  }

  for (const section of lemmaDetails.meaning_sections ?? []) {
    pushTarget(
      section.english_translation?.trim() || section.gloss?.trim() || section.meaning_key,
      `Meaning #${section.id}`,
      section.id,
      null,
      section.verification,
    )
    for (const form of section.surface_forms) {
      if (!form.verification) {
        continue
      }
      pushTarget(form.form, `Variation in meaning #${section.id}`, section.id, form.form, form.verification)
    }
  }

  if (!(lemmaDetails.meaning_sections?.length ?? 0)) {
    for (const form of lemmaDetails.surface_forms) {
      if (!form.verification) {
        continue
      }
      const normalizedForm = normalizeSearchWord(form.form)
      if (normalizedForm === normalizeSearchWord(lemmaDetails.lemma)) {
        continue
      }
      pushTarget(form.form, "Variation", null, form.form, form.verification)
    }
  }

  return targets
}

export function findVerificationTarget(
  lemmaDetails: LemmaDetailsResponse | null,
  targetKey: string,
): VerificationTargetView | null {
  return collectLemmaVerificationTargets(lemmaDetails).find((target) => target.key === targetKey) ?? null
}

export function collectMeaningCardVerificationTargets(
  lemmaDetails: LemmaDetailsResponse | null,
  meaningId: number | null,
): VerificationTargetRefView[] {
  if (!lemmaDetails || meaningId === null) {
    return []
  }
  const section = (lemmaDetails.meaning_sections ?? []).find((item) => item.id === meaningId) ?? null
  if (!section) {
    return []
  }

  const normalizedLemma = normalizeSearchWord(lemmaDetails.lemma)
  const targets: VerificationTargetRefView[] = []
  const seen = new Set<string>()
  const pushTarget = (storedSurfaceForm: string | null) => {
    const normalizedSurface = normalizeSearchWord(storedSurfaceForm ?? "") || null
    const key = `${meaningId}::${normalizedSurface ?? "root"}`
    if (seen.has(key)) {
      return
    }
    seen.add(key)
    targets.push({
      meaningId,
      storedSurfaceForm: normalizedSurface,
    })
  }

  pushTarget(null)
  for (const form of section.surface_forms) {
    const normalizedSurface = normalizeSearchWord(form.form)
    if (!normalizedSurface || normalizedSurface === normalizedLemma) {
      continue
    }
    pushTarget(form.form)
  }
  return targets
}

export function getMeaningVerificationGate(
  lemmaDetails: LemmaDetailsResponse | null,
  meaningId: number | null,
): MeaningVerificationGate {
  if (!lemmaDetails) {
    return { isLocked: true, label: "Complete variations unavailable" }
  }
  const sections = lemmaDetails.meaning_sections ?? []
  const section = meaningId === null
    ? (sections.length === 1 ? sections[0] : null)
    : sections.find((item) => item.id === meaningId) ?? null
  if (!section) {
    return { isLocked: true, label: "Complete variations unavailable" }
  }

  const normalizedLemma = normalizeSearchWord(lemmaDetails.lemma)
  const statuses: Array<string | null> = [section.verification?.status ?? null]
  for (const form of section.surface_forms) {
    const normalizedSurface = normalizeSearchWord(form.form)
    if (!normalizedSurface || normalizedSurface === normalizedLemma) {
      continue
    }
    statuses.push(form.verification?.status ?? null)
  }

  if (statuses.some((status) => status === "queued")) {
    return { isLocked: true, label: "Waiting for verification..." }
  }
  if (statuses.some((status) => status === "error")) {
    return { isLocked: true, label: "Retry verification first" }
  }
  if (statuses.some((status) => status === "flagged")) {
    return { isLocked: true, label: "Resolve verification review first" }
  }
  if (statuses.some((status) => status !== "verified")) {
    return { isLocked: true, label: "Complete variations unavailable" }
  }
  return { isLocked: false, label: "Complete variations" }
}
