import { type Dispatch, type SetStateAction, useCallback, useEffect, useMemo, useRef, useState } from "react"

import {
  buildVerificationErrorDetail,
  createApiClient,
  getSelectedLemmaVerificationSelection,
  mapVerificationResultToErrorDetail,
  mapVerificationResultToQueuedDetail,
  mapVerificationResultToSuccessDetail,
  normalizeSearchWord,
  type ApplyVerificationChangesResponse,
  type LemmaDetailsResponse,
  type VerificationAction,
  type VerificationErrorDetail,
  type VerificationResult,
  type VerifyWordResponse,
  verificationResultSignature,
} from "@/app/core"
import { toast } from "sonner"

type UseVerificationWorkflowParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
  selectedLemma: string | null
  selectedMeaningId: number | null
  lemmaDetails: LemmaDetailsResponse | null
  setWordbankRefreshTick: Dispatch<SetStateAction<number>>
  pushNotification: (
    message: string,
    options?: {
      kind?: "info" | "word_verification"
      lemma?: string
      meaningId?: number | null
      surfaceForm?: string | null
      actionCount?: number
    },
  ) => void
  onOpenWordbankTarget: (lemma: string, meaningId: number | null) => void
}

export function useVerificationWorkflow({
  backendUrl,
  extractErrorMessage,
  selectedLemma,
  selectedMeaningId,
  lemmaDetails,
  setWordbankRefreshTick,
  pushNotification,
  onOpenWordbankTarget,
}: UseVerificationWorkflowParams) {
  const [isApplyingVerificationChanges, setIsApplyingVerificationChanges] = useState(false)
  const [pendingVerificationCount, setPendingVerificationCount] = useState(0)
  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )
  const notifiedVerificationSignaturesRef = useRef<Record<string, string>>({})
  const previousVerificationStatusesRef = useRef<Record<string, VerificationResult["status"] | null>>({})

  const selectedVerificationSelection = useMemo(
    () => getSelectedLemmaVerificationSelection({ lemmaDetails, selectedMeaningId }),
    [lemmaDetails, selectedMeaningId],
  )
  const selectedVerification = selectedVerificationSelection.verification
  const selectedVerificationMeaningId = selectedVerificationSelection.meaningId

  const selectedLemmaVerificationError = useMemo(
    () => mapVerificationResultToErrorDetail(selectedVerification, selectedVerificationMeaningId),
    [selectedVerification, selectedVerificationMeaningId],
  )
  const selectedLemmaVerificationSuccess = useMemo(
    () => mapVerificationResultToSuccessDetail(selectedVerification, selectedVerificationMeaningId),
    [selectedVerification, selectedVerificationMeaningId],
  )
  const selectedLemmaVerificationQueued = useMemo(
    () => mapVerificationResultToQueuedDetail(selectedVerification, selectedVerificationMeaningId),
    [selectedVerification, selectedVerificationMeaningId],
  )

  function hasSuggestedVerificationActions(detail: VerificationErrorDetail | null): boolean {
    return (detail?.suggestedActions.length ?? 0) > 0
  }

  const notifyWordVerification = useCallback((args: {
    storedLemma: string
    storedSurfaceForm: string | null
    meaningId: number | null
    verification: VerificationResult | null
  }) => {
    const { storedLemma, storedSurfaceForm, meaningId, verification } = args
    if (!verification || verification.status === "skipped" || verification.status === "queued") {
      return
    }
    const lemmaKey = normalizeSearchWord(storedLemma)
    const signature = verificationResultSignature(verification, meaningId)
    const key = verificationKey(lemmaKey || storedLemma, meaningId)
    if (signature && notifiedVerificationSignaturesRef.current[key] === signature) {
      return
    }
    if (signature) {
      notifiedVerificationSignaturesRef.current[key] = signature
    }

    if (verification.status === "verified") {
      pushNotification(`Verification passed for '${lemmaKey || storedLemma}'.`)
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
      suggestedActions: verification.suggested_actions,
    })
    pushNotification(`Review needed for '${lemmaKey || storedLemma || "word"}'.`, {
      kind: "word_verification",
      lemma: lemmaKey || storedLemma,
      meaningId,
      surfaceForm: storedSurfaceForm,
      actionCount: detail.suggestedActions.length,
    })
  }, [pushNotification])

  useEffect(() => {
    const lemmaKey = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? "")
    if (!lemmaKey || !selectedVerification) {
      return
    }
    const verificationKeyValue = verificationKey(lemmaKey, selectedVerificationMeaningId)
    const previousStatus = previousVerificationStatusesRef.current[verificationKeyValue] ?? null
    previousVerificationStatusesRef.current[verificationKeyValue] = selectedVerification.status
    if (previousStatus !== "queued" || selectedVerification.status === "queued" || selectedVerification.status === "skipped") {
      return
    }
    notifyWordVerification({
      storedLemma: lemmaKey,
      storedSurfaceForm: selectedVerification.stored_surface_form ?? null,
      meaningId: selectedVerificationMeaningId,
      verification: selectedVerification,
    })
  }, [
    lemmaDetails?.lemma,
    notifyWordVerification,
    selectedLemma,
    selectedVerification,
    selectedVerificationMeaningId,
  ])

  async function verifyWordInBackground(
    storedLemma: string,
    storedSurfaceForm: string | null,
    meaningId: number | null,
  ) {
    setPendingVerificationCount((current) => current + 1)
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
      notifyWordVerification({
        storedLemma: payload.stored_lemma,
        storedSurfaceForm: payload.stored_surface_form,
        meaningId,
        verification: payload.verification,
      })
      setWordbankRefreshTick((current) => current + 1)
    } catch (error) {
      const message = error instanceof Error ? error.message : null
      const lemmaKey = normalizeSearchWord(storedLemma)
      const detail = buildVerificationErrorDetail({
        provider: "gemini",
        status: "error",
        message,
        storedSurfaceForm,
        meaningId,
      })
      pushNotification(`Review needed for '${lemmaKey || storedLemma}'.`, {
        kind: "word_verification",
        lemma: lemmaKey || storedLemma,
        meaningId,
        surfaceForm: storedSurfaceForm,
        actionCount: detail.suggestedActions.length,
      })
    } finally {
      setPendingVerificationCount((current) => Math.max(0, current - 1))
    }
  }

  async function applySelectedLemmaVerificationAction(actionIndex: number) {
    const lemma = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? "")
    const detail = selectedLemmaVerificationError
    const action = detail?.suggestedActions[actionIndex]
    if (!lemma || !detail || !action) {
      return
    }

    setIsApplyingVerificationChanges(true)
    try {
      const payload = await apiClient.postJson<ApplyVerificationChangesResponse>(
        "/api/wordbank/lexemes/apply-verification-changes",
        {
          stored_lemma: lemma,
          stored_surface_form: detail.storedSurfaceForm ?? lemma,
          meaning_id: detail.meaningId ?? selectedVerificationMeaningId ?? null,
          action,
          provider: detail.provider,
        },
        "Could not apply Gemini action.",
      )
      if (payload.status !== "applied") {
        toast.error("No Gemini action was applied.")
        return
      }

      toast.success(buildActionToastMessage(action, lemma))
      setWordbankRefreshTick((current) => current + 1)
      onOpenWordbankTarget(payload.target_lemma ?? lemma, payload.target_meaning_id ?? null)
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not apply Gemini action."
      toast.error(message)
    } finally {
      setIsApplyingVerificationChanges(false)
    }
  }

  function clearVerificationErrors() {
    notifiedVerificationSignaturesRef.current = {}
    previousVerificationStatusesRef.current = {}
  }

  return {
    isApplyingVerificationChanges,
    isVerifyingWords: pendingVerificationCount > 0 || selectedLemmaVerificationQueued !== null,
    selectedLemmaVerificationError,
    selectedLemmaVerificationSuccess,
    selectedLemmaVerificationQueued,
    hasSuggestedVerificationActions,
    verifyWordInBackground,
    applySelectedLemmaVerificationAction,
    clearVerificationErrors,
  }
}

function verificationKey(lemma: string, meaningId: number | null): string {
  return `${lemma}::${meaningId ?? "root"}`
}

function buildActionToastMessage(action: VerificationAction, lemma: string): string {
  if (action.action_type === "fix_translation") {
    return `Updated translation for '${lemma}'.`
  }
  if (action.action_type === "fix_gloss") {
    return `Updated gloss for '${lemma}'.`
  }
  if (action.action_type === "move_to_meaning_section") {
    return `Moved entry to a different meaning section for '${lemma}'.`
  }
  if (action.action_type === "move_to_lemma") {
    return `Moved entry from '${lemma}' to '${action.target_lemma ?? "new lemma"}'.`
  }
  return `Applied Gemini action for '${lemma}'.`
}
