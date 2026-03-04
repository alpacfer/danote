import { type Dispatch, type SetStateAction, useMemo, useState } from "react"

import {
  buildVerificationErrorDetail,
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
  lemmaDetails: LemmaDetailsResponse | null
  setWordbankRefreshTick: Dispatch<SetStateAction<number>>
  pushNotification: (message: string) => void
}

export function useVerificationWorkflow({
  backendUrl,
  extractErrorMessage,
  selectedLemma,
  lemmaDetails,
  setWordbankRefreshTick,
  pushNotification,
}: UseVerificationWorkflowParams) {
  const [isApplyingVerificationChanges, setIsApplyingVerificationChanges] = useState(false)
  const [verificationErrorsByLemma, setVerificationErrorsByLemma] = useState<Record<string, VerificationErrorDetail>>({})

  const selectedLemmaVerificationError = useMemo(() => {
    const lemmaKey = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? "")
    if (!lemmaKey) {
      return null
    }
    return verificationErrorsByLemma[lemmaKey] ?? null
  }, [lemmaDetails?.lemma, selectedLemma, verificationErrorsByLemma])

  function hasSuggestedVerificationChanges(detail: VerificationErrorDetail | null): boolean {
    if (!detail?.suggestedChangesPayload) {
      return false
    }
    return Object.values(detail.suggestedChangesPayload).some((value) => typeof value === "string" && value.trim().length > 0)
  }

  function notifyWordVerification(
    storedLemma: string,
    storedSurfaceForm: string | null,
    verification: VerifyWordResponse["verification"],
  ) {
    if (!verification || verification.status === "skipped" || verification.status === "queued") {
      return
    }

    const isOk = verification.status === "verified"
    const lemmaKey = normalizeSearchWord(storedLemma)
    if (isOk) {
      setVerificationErrorsByLemma((current) => {
        if (!Object.hasOwn(current, lemmaKey)) {
          return current
        }
        const next = { ...current }
        delete next[lemmaKey]
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
      problem: verification.problem,
      changeToImplement: verification.change_to_implement,
      suggestedChanges: verification.suggested_changes,
    })
    setVerificationErrorsByLemma((current) => ({ ...current, [lemmaKey]: detail }))
    const displayLemma = lemmaKey || storedLemma || "word"
    pushNotification(`ERROR ${displayLemma}: ${detail.problem} Change: ${detail.changeToImplement}`)
  }

  async function verifyWordInBackground(storedLemma: string, storedSurfaceForm: string | null) {
    try {
      const response = await fetch(`${backendUrl}/api/wordbank/lexemes/verify`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          stored_lemma: storedLemma,
          stored_surface_form: storedSurfaceForm,
        }),
      })
      if (!response.ok) {
        const message = await extractErrorMessage(
          response,
          `Verify word request failed with status ${response.status}`,
        )
        throw new Error(message)
      }
      const payload = (await response.json()) as VerifyWordResponse
      notifyWordVerification(payload.stored_lemma, payload.stored_surface_form, payload.verification)
    } catch (error) {
      const message = error instanceof Error ? error.message : null
      const lemmaKey = normalizeSearchWord(storedLemma)
      const detail = buildVerificationErrorDetail({
        provider: "gemini",
        status: "error",
        message,
        storedSurfaceForm,
      })
      setVerificationErrorsByLemma((current) => ({ ...current, [lemmaKey]: detail }))
      pushNotification(`ERROR ${lemmaKey || storedLemma}: ${detail.problem} Change: ${detail.changeToImplement}`)
    }
  }

  async function applySelectedLemmaVerificationChanges() {
    const lemma = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? "")
    if (!lemma) {
      return
    }
    const detail = verificationErrorsByLemma[lemma] ?? null
    if (!detail || !hasSuggestedVerificationChanges(detail) || !detail.suggestedChangesPayload) {
      return
    }

    setIsApplyingVerificationChanges(true)
    try {
      const response = await fetch(`${backendUrl}/api/wordbank/lexemes/apply-verification-changes`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          stored_lemma: lemma,
          stored_surface_form: detail.storedSurfaceForm ?? lemma,
          suggested_changes: detail.suggestedChangesPayload,
          provider: detail.provider,
        }),
      })
      if (!response.ok) {
        const message = await extractErrorMessage(
          response,
          `Apply verification changes failed with status ${response.status}`,
        )
        throw new Error(message)
      }

      const payload = (await response.json()) as ApplyVerificationChangesResponse
      if (payload.status === "applied") {
        const count = payload.applied_fields.length
        toast.success(
          count > 0
            ? `Applied ${count} Gemini change${count === 1 ? "" : "s"} for '${lemma}'.`
            : `Applied Gemini changes for '${lemma}'.`,
        )
        setVerificationErrorsByLemma((current) => {
          if (!Object.hasOwn(current, lemma)) {
            return current
          }
          const next = { ...current }
          delete next[lemma]
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
    setVerificationErrorsByLemma({})
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
