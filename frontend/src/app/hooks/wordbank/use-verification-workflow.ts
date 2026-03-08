import { type Dispatch, type SetStateAction, useMemo, useState } from "react"

import {
  buildVerificationErrorDetail,
  createApiClient,
  normalizeSearchWord,
  type ApplyVerificationChangesResponse,
  type LemmaDetailsResponse,
  type VerifyWordResponse,
  type VerificationErrorDetail,
} from "@/app/core"
import { toast } from "sonner"

type UseVerificationWorkflowParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
  selectedLemma: string | null
  selectedMeaningId: number | null
  lemmaDetails: LemmaDetailsResponse | null
  setWordbankRefreshTick: Dispatch<SetStateAction<number>>
  pushNotification: (message: string) => void
}

export function useVerificationWorkflow({
  backendUrl,
  extractErrorMessage,
  selectedLemma,
  selectedMeaningId,
  lemmaDetails,
  setWordbankRefreshTick,
  pushNotification,
}: UseVerificationWorkflowParams) {
  const [isApplyingVerificationChanges, setIsApplyingVerificationChanges] = useState(false)
  const [verificationErrorsByKey, setVerificationErrorsByKey] = useState<Record<string, VerificationErrorDetail>>({})
  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )

  const selectedLemmaVerificationError = useMemo(() => {
    const lemmaKey = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? "")
    if (!lemmaKey) {
      return null
    }
    const directMatch = verificationErrorsByKey[verificationKey(lemmaKey, selectedMeaningId)] ?? null
    if (directMatch) {
      return directMatch
    }
    if (selectedMeaningId === null && (lemmaDetails?.meaning_sections?.length ?? 0) === 1) {
      return verificationErrorsByKey[verificationKey(lemmaKey, lemmaDetails?.meaning_sections?.[0]?.id ?? null)] ?? null
    }
    return null
  }, [lemmaDetails?.lemma, lemmaDetails?.meaning_sections, selectedLemma, selectedMeaningId, verificationErrorsByKey])

  function hasSuggestedVerificationChanges(detail: VerificationErrorDetail | null): boolean {
    if (!detail?.suggestedChangesPayload) {
      return false
    }
    return Object.values(detail.suggestedChangesPayload).some((value) => typeof value === "string" && value.trim().length > 0)
  }

  function notifyWordVerification(
    storedLemma: string,
    storedSurfaceForm: string | null,
    meaningId: number | null,
    verification: VerifyWordResponse["verification"],
  ) {
    if (!verification || verification.status === "skipped" || verification.status === "queued") {
      return
    }

    const isOk = verification.status === "verified"
    const lemmaKey = normalizeSearchWord(storedLemma)
    const key = verificationKey(lemmaKey, meaningId)
    if (isOk) {
      setVerificationErrorsByKey((current) => {
        if (!Object.hasOwn(current, key)) {
          return current
        }
        const next = { ...current }
        delete next[key]
        return next
      })
      pushNotification("OK")
      return
    }

    const detail = buildVerificationErrorDetail({
      provider: verification.provider,
      status: verification.status === "flagged" ? "flagged" : "error",
      message: verification.message,
      composedWordCount: verification.composed_word_count,
      storedSurfaceForm,
      meaningId,
      problem: verification.problem,
      changeToImplement: verification.change_to_implement,
      suggestedChanges: verification.suggested_changes,
    })
    setVerificationErrorsByKey((current) => ({ ...current, [key]: detail }))
    const displayLemma = lemmaKey || storedLemma || "word"
    pushNotification(`ERROR ${displayLemma}: ${detail.problem} Change: ${detail.changeToImplement}`)
  }

  async function verifyWordInBackground(
    storedLemma: string,
    storedSurfaceForm: string | null,
    meaningId: number | null,
  ) {
    try {
      const payload = await apiClient.postJson<VerifyWordResponse>(
        "/api/wordbank/lexemes/verify",
        {
          stored_lemma: storedLemma,
          stored_surface_form: storedSurfaceForm,
          meaning_id: meaningId,
        },
        "Could not verify word.",
      )
      notifyWordVerification(payload.stored_lemma, payload.stored_surface_form, meaningId, payload.verification)
    } catch (error) {
      const message = error instanceof Error ? error.message : null
      const lemmaKey = normalizeSearchWord(storedLemma)
      const key = verificationKey(lemmaKey, meaningId)
      const detail = buildVerificationErrorDetail({
        provider: "gemini",
        status: "error",
        message,
        storedSurfaceForm,
        meaningId,
      })
      setVerificationErrorsByKey((current) => ({ ...current, [key]: detail }))
      pushNotification(`ERROR ${lemmaKey || storedLemma}: ${detail.problem} Change: ${detail.changeToImplement}`)
    }
  }

  async function applySelectedLemmaVerificationChanges() {
    const lemma = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? "")
    if (!lemma) {
      return
    }
    const key = verificationKey(lemma, selectedMeaningId)
    const detail = verificationErrorsByKey[key]
      ?? (
        selectedMeaningId === null && (lemmaDetails?.meaning_sections?.length ?? 0) === 1
          ? verificationErrorsByKey[verificationKey(lemma, lemmaDetails?.meaning_sections?.[0]?.id ?? null)] ?? null
          : null
      )
    if (!detail || !hasSuggestedVerificationChanges(detail) || !detail.suggestedChangesPayload) {
      return
    }

    setIsApplyingVerificationChanges(true)
    const detailKey = verificationKey(lemma, detail.meaningId ?? selectedMeaningId ?? null)
    try {
      const payload = await apiClient.postJson<ApplyVerificationChangesResponse>(
        "/api/wordbank/lexemes/apply-verification-changes",
        {
          stored_lemma: lemma,
          stored_surface_form: detail.storedSurfaceForm ?? lemma,
          meaning_id: detail.meaningId ?? selectedMeaningId ?? null,
          suggested_changes: detail.suggestedChangesPayload,
          provider: detail.provider,
        },
        "Could not apply Gemini changes.",
      )
      if (payload.status === "applied") {
        const count = payload.applied_fields.length
        toast.success(
          count > 0
            ? `Applied ${count} Gemini change${count === 1 ? "" : "s"} for '${lemma}'.`
            : `Applied Gemini changes for '${lemma}'.`,
        )
        setVerificationErrorsByKey((current) => {
          if (!Object.hasOwn(current, detailKey)) {
            return current
          }
          const next = { ...current }
          delete next[detailKey]
          return next
        })
        setWordbankRefreshTick((current) => current + 1)
      } else {
        toast.error("No Gemini changes were applied.")
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not apply Gemini changes."
      toast.error(message)
    } finally {
      setIsApplyingVerificationChanges(false)
    }
  }

  function clearVerificationErrors() {
    setVerificationErrorsByKey({})
  }

  return {
    isApplyingVerificationChanges,
    selectedLemmaVerificationError,
    hasSuggestedVerificationChanges,
    verifyWordInBackground,
    applySelectedLemmaVerificationChanges,
    clearVerificationErrors,
  }
}

function verificationKey(lemma: string, meaningId: number | null): string {
  return `${lemma}::${meaningId ?? "root"}`
}
