import { type Dispatch, type SetStateAction, useMemo, useState } from "react"

import {
  buildVerificationErrorDetail,
  compactMessage,
  createApiClient,
  normalizeSearchWord,
  type ApplyVerificationChangesResponse,
  type LemmaDetailsResponse,
  type VerificationAction,
  type VerifyWordResponse,
  type VerificationErrorDetail,
  type VerificationSuccessDetail,
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
  const [verificationErrorsByKey, setVerificationErrorsByKey] = useState<Record<string, VerificationErrorDetail>>({})
  const [verificationSuccessByKey, setVerificationSuccessByKey] = useState<Record<string, VerificationSuccessDetail>>({})
  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )

  const selectedLemmaVerificationError = useMemo(() => {
    const lemmaKey = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? "")
    if (!lemmaKey) {
      return null
    }
    return getSelectedVerificationDetail({
      verificationDetailsByKey: verificationErrorsByKey,
      lemma: lemmaKey,
      selectedMeaningId,
      meaningSections: lemmaDetails?.meaning_sections ?? [],
    })
  }, [lemmaDetails?.lemma, lemmaDetails?.meaning_sections, selectedLemma, selectedMeaningId, verificationErrorsByKey])

  const selectedLemmaVerificationSuccess = useMemo(() => {
    const lemmaKey = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? "")
    if (!lemmaKey) {
      return null
    }
    return getSelectedVerificationDetail({
      verificationDetailsByKey: verificationSuccessByKey,
      lemma: lemmaKey,
      selectedMeaningId,
      meaningSections: lemmaDetails?.meaning_sections ?? [],
    })
  }, [lemmaDetails?.lemma, lemmaDetails?.meaning_sections, selectedLemma, selectedMeaningId, verificationSuccessByKey])

  function hasSuggestedVerificationActions(detail: VerificationErrorDetail | null): boolean {
    return (detail?.suggestedActions.length ?? 0) > 0
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

    const lemmaKey = normalizeSearchWord(storedLemma)
    const key = verificationKey(lemmaKey, meaningId)
    if (verification.status === "verified") {
      setVerificationErrorsByKey((current) => {
        if (!Object.hasOwn(current, key)) {
          return current
        }
        const next = { ...current }
        delete next[key]
        return next
      })
      setVerificationSuccessByKey((current) => ({
        ...current,
        [key]: {
          provider: verification.provider?.trim() || "gemini",
          rawMessage: compactMessage(verification.message) || "Gemini verified this word.",
          storedSurfaceForm,
          meaningId,
          verifiedAt: new Date().toISOString(),
        },
      }))
      pushNotification(`Verification passed for '${lemmaKey || storedLemma}'.`)
      return
    }

    setVerificationSuccessByKey((current) => {
      if (!Object.hasOwn(current, key)) {
        return current
      }
      const next = { ...current }
      delete next[key]
      return next
    })
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
    setVerificationErrorsByKey((current) => ({ ...current, [key]: detail }))
    const displayLemma = lemmaKey || storedLemma || "word"
    pushNotification(`Review needed for '${displayLemma}'.`, {
      kind: "word_verification",
      lemma: displayLemma,
      meaningId,
      surfaceForm: storedSurfaceForm,
      actionCount: detail.suggestedActions.length,
    })
  }

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
      setVerificationSuccessByKey((current) => {
        if (!Object.hasOwn(current, key)) {
          return current
        }
        const next = { ...current }
        delete next[key]
        return next
      })
      setVerificationErrorsByKey((current) => ({ ...current, [key]: detail }))
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
    if (!lemma) {
      return
    }
    const detail = getSelectedVerificationDetail({
      verificationDetailsByKey: verificationErrorsByKey,
      lemma,
      selectedMeaningId,
      meaningSections: lemmaDetails?.meaning_sections ?? [],
    })
    const action = detail?.suggestedActions[actionIndex]
    if (!detail || !action) {
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
      setVerificationErrorsByKey((current) => {
        const currentDetail = current[detailKey]
        if (!currentDetail) {
          return current
        }
        const shouldRemoveDetail = isMoveAction(payload.applied_action_type) || movedToDifferentTarget(payload, lemma, detail.meaningId)
        const remainingActions = shouldRemoveDetail
          ? []
          : currentDetail.suggestedActions.filter((candidate) => actionKey(candidate) !== actionKey(action))
        if (remainingActions.length === 0) {
          const next = { ...current }
          delete next[detailKey]
          return next
        }
        return {
          ...current,
          [detailKey]: {
            ...currentDetail,
            suggestedActions: remainingActions,
          },
        }
      })
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
    setVerificationErrorsByKey({})
    setVerificationSuccessByKey({})
  }

  return {
    isApplyingVerificationChanges,
    isVerifyingWords: pendingVerificationCount > 0,
    selectedLemmaVerificationError,
    selectedLemmaVerificationSuccess,
    hasSuggestedVerificationActions,
    verifyWordInBackground,
    applySelectedLemmaVerificationAction,
    clearVerificationErrors,
  }
}

function getSelectedVerificationDetail<T>(args: {
  verificationDetailsByKey: Record<string, T>
  lemma: string
  selectedMeaningId: number | null
  meaningSections: Array<{ id: number }>
}): T | null {
  const directMatch = args.verificationDetailsByKey[verificationKey(args.lemma, args.selectedMeaningId)] ?? null
  if (directMatch) {
    return directMatch
  }
  if (args.selectedMeaningId === null && args.meaningSections.length === 1) {
    return args.verificationDetailsByKey[verificationKey(args.lemma, args.meaningSections[0]?.id ?? null)] ?? null
  }
  return null
}

function verificationKey(lemma: string, meaningId: number | null): string {
  return `${lemma}::${meaningId ?? "root"}`
}

function actionKey(action: VerificationAction): string {
  return JSON.stringify(action)
}

function isMoveAction(actionType: string | null): boolean {
  return actionType === "move_to_meaning_section" || actionType === "move_to_lemma"
}

function movedToDifferentTarget(
  payload: ApplyVerificationChangesResponse,
  lemma: string,
  meaningId: number | null,
): boolean {
  if ((payload.target_lemma ?? lemma) !== lemma) {
    return true
  }
  return (payload.target_meaning_id ?? null) !== (meaningId ?? null)
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
