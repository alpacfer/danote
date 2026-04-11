import { type Dispatch, type SetStateAction, useCallback, useMemo, useState } from "react"

import {
  collectMeaningCardVerificationTargets,
  collectLemmaVerificationOverview,
  createApiClient,
  findVerificationTarget,
  normalizeSearchWord,
  type ApplyVerificationChangesResponse,
  type AppSection,
  type LemmaDetailsResponse,
  type QueueVerificationResponse,
  type VerificationOverview,
} from "@/app/core"
import { toast } from "sonner"

import { useTrackedVerificationTargets } from "./use-tracked-verification-targets"
import { useVerificationChanges } from "./use-verification-changes"

type UseVerificationWorkflowParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
  activeSection: AppSection
  selectedLemma: string | null
  lemmaDetails: LemmaDetailsResponse | null
  setWordbankRefreshTick: Dispatch<SetStateAction<number>>
  pushNotification: (
    message: string,
    options?: {
      kind?: "info" | "word_verification"
      lemma?: string
      meaningId?: number | null
      surfaceForm?: string | null
      targetKey?: string
      status?: "queued" | "verified" | "flagged" | "error"
      signature?: string | null
      actionCount?: number
    },
  ) => void
  markWordVerificationNotificationsAsRead: (targetKeys: string[]) => void
  clearWordVerificationNotification: (targetKey: string) => void
  onOpenWordbankTarget: (lemma: string, meaningId: number | null) => void
}

export function useVerificationWorkflow({
  backendUrl,
  extractErrorMessage,
  activeSection,
  selectedLemma,
  lemmaDetails,
  setWordbankRefreshTick,
  pushNotification,
  markWordVerificationNotificationsAsRead,
  clearWordVerificationNotification,
  onOpenWordbankTarget,
}: UseVerificationWorkflowParams) {
  const [isApplyingVerificationChanges, setIsApplyingVerificationChanges] = useState(false)
  const [isRetryingVerification, setIsRetryingVerification] = useState(false)
  const [rerunningMeaningVerificationById, setRerunningMeaningVerificationById] = useState<Record<number, boolean>>({})
  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )
  const {
    changes,
    isLoadingChanges,
    isRevertingChange,
    revertChange,
    refreshChanges,
  } = useVerificationChanges({
    backendUrl,
    extractErrorMessage,
    selectedLemma,
    setWordbankRefreshTick,
  })

  const verificationOverview = useMemo(
    () => collectLemmaVerificationOverview(lemmaDetails),
    [lemmaDetails],
  )
  const {
    clearVerificationErrors,
    isVerifyingWords,
    markVisibleVerificationNotificationsAsRead,
    trackQueuedVerificationTarget,
    trackQueuedVerificationTargets,
    trackQueuedVerifications,
  } = useTrackedVerificationTargets({
    activeSection,
    apiClient,
    clearWordVerificationNotification,
    lemmaDetails,
    markWordVerificationNotificationsAsRead,
    onOpenLemmaVerificationCompleted: () => {
      setWordbankRefreshTick((current) => current + 1)
      void refreshChanges()
    },
    pushNotification,
    selectedLemma,
    verificationOverview,
  })

  async function applyVerificationAction(targetKey: string, actionIndex: number) {
    const lemma = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? "")
    const target = findVerificationTarget(lemmaDetails, targetKey)
    const action = target?.errorDetail?.suggestedActions[actionIndex]
    if (!lemma || !target || !action) {
      return
    }

    setIsApplyingVerificationChanges(true)
    try {
      const payload = await apiClient.postJson<ApplyVerificationChangesResponse>(
        "/api/wordbank/lexemes/apply-verification-changes",
        {
          stored_lemma: lemma,
          stored_surface_form: target.storedSurfaceForm,
          meaning_id: target.meaningId,
          action,
          provider: target.errorDetail?.provider,
        },
        "Could not apply Gemini action.",
      )
      if (payload.status !== "applied") {
        toast.error("No Gemini action was applied.")
        return
      }

      toast.success(buildActionToastMessage(action.action_type, target.label))
      setWordbankRefreshTick((current) => current + 1)
      await refreshChanges()
      onOpenWordbankTarget(payload.target_lemma ?? lemma, payload.target_meaning_id ?? target.meaningId ?? null)
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not apply Gemini action."
      toast.error(message)
    } finally {
      setIsApplyingVerificationChanges(false)
    }
  }

  async function retryVerificationTarget(targetKey: string) {
    const lemma = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? "")
    const target = findVerificationTarget(lemmaDetails, targetKey)
    if (!lemma || !target) {
      return
    }

    setIsRetryingVerification(true)
    try {
      const payload = await apiClient.postJson<QueueVerificationResponse>(
        "/api/wordbank/lexemes/queue-verification",
        {
          stored_lemma: lemma,
          stored_surface_form: target.storedSurfaceForm,
          meaning_id: target.meaningId,
          review_intent: target.verification?.review_intent ?? "general",
        },
        "Could not retry verification.",
      )
      if (payload.verification.status !== "queued") {
        toast.error(payload.verification.message || "Could not retry verification.")
        return
      }
      trackQueuedVerificationTarget(lemma, target.meaningId, target.storedSurfaceForm)
      toast.success(`Requeued verification for '${target.label}'.`)
      setWordbankRefreshTick((current) => current + 1)
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not retry verification."
      toast.error(message)
    } finally {
      setIsRetryingVerification(false)
    }
  }

  async function rerunMeaningVerification(meaningId: number) {
    const lemma = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? "")
    const section = (lemmaDetails?.meaning_sections ?? []).find((item) => item.id === meaningId) ?? null
    const targets = collectMeaningCardVerificationTargets(lemmaDetails, meaningId)
    if (!lemma || !section || targets.length === 0) {
      return
    }

    const sectionLabel = section.english_translation?.trim() || section.gloss?.trim() || section.meaning_key
    setRerunningMeaningVerificationById((current) => ({ ...current, [meaningId]: true }))
    try {
      const results = await Promise.allSettled(
        targets.map(async (target) => apiClient.postJson<QueueVerificationResponse>(
          "/api/wordbank/lexemes/queue-verification",
          {
            stored_lemma: lemma,
            stored_surface_form: target.storedSurfaceForm,
            meaning_id: target.meaningId,
            review_intent: "general",
          },
          "Could not rerun verification.",
        )),
      )

      const queuedTargets: Array<{ meaning_id: number | null; stored_surface_form: string | null }> = []
      const errors: string[] = []
      for (const result of results) {
        if (result.status === "rejected") {
          errors.push(result.reason instanceof Error ? result.reason.message : "Could not rerun verification.")
          continue
        }
        if (result.value.verification.status !== "queued") {
          errors.push(result.value.verification.message || "Could not rerun verification.")
          continue
        }
        queuedTargets.push({
          meaning_id: result.value.meaning_id ?? null,
          stored_surface_form: result.value.stored_surface_form ?? null,
        })
      }

      if (queuedTargets.length > 0) {
        trackQueuedVerificationTargets(lemma, queuedTargets)
        setWordbankRefreshTick((current) => current + 1)
      }

      if (errors.length === 0 && queuedTargets.length === targets.length) {
        toast.success(`Requeued verification for '${sectionLabel}'.`)
        return
      }
      if (queuedTargets.length > 0) {
        toast.error(`Only requeued ${queuedTargets.length} of ${targets.length} verification targets for '${sectionLabel}'.`)
        return
      }
      toast.error(errors[0] ?? "Could not rerun verification.")
    } finally {
      setRerunningMeaningVerificationById((current) => {
        const next = { ...current }
        delete next[meaningId]
        return next
      })
    }
  }

  return {
    isApplyingVerificationChanges,
    isRetryingVerification,
    rerunningMeaningVerificationById,
    isVerifyingWords,
    verificationOverview: verificationOverview as VerificationOverview,
    changes,
    isLoadingChanges,
    isRevertingChange,
    trackQueuedVerifications,
    trackQueuedVerificationTargets,
    applyVerificationAction,
    retryVerificationTarget,
    rerunMeaningVerification,
    revertChange,
    refreshChanges,
    markVisibleVerificationNotificationsAsRead,
    clearVerificationErrors,
  }
}

function buildActionToastMessage(actionType: string, label: string): string {
  if (actionType === "fix_translation") {
    return `Updated translation for '${label}'.`
  }
  if (actionType === "fix_variations") {
    return `Updated variations for '${label}'.`
  }
  if (actionType === "move_to_meaning_section") {
    return `Moved '${label}' to a different meaning section.`
  }
  if (actionType === "move_to_lemma") {
    return `Moved '${label}' to a different lemma.`
  }
  return `Applied Gemini action for '${label}'.`
}
