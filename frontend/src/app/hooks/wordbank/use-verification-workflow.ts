import { type Dispatch, type SetStateAction, useCallback, useEffect, useMemo, useRef, useState } from "react"

import {
  collectMeaningCardVerificationTargets,
  collectLemmaVerificationOverview,
  collectLemmaVerificationTargets,
  createApiClient,
  findVerificationTarget,
  normalizeSearchWord,
  type AddWordResponse,
  type ApplyVerificationChangesResponse,
  type AppSection,
  type LemmaDetailsResponse,
  type QueueVerificationResponse,
  type VerificationOverview,
  verificationResultSignature,
  verificationTargetKey,
  type VerificationTargetView,
} from "@/app/core"
import { toast } from "sonner"

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

type TrackedQueuedVerification = {
  lemma: string
  meaningId: number | null
  storedSurfaceForm: string | null
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
  const [trackedQueuedVerifications, setTrackedQueuedVerifications] = useState<Record<string, TrackedQueuedVerification>>({})
  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )
  const notifiedVerificationSignaturesRef = useRef<Record<string, string>>({})

  const verificationOverview = useMemo(
    () => collectLemmaVerificationOverview(lemmaDetails),
    [lemmaDetails],
  )

  const notifyVerificationTarget = useCallback((storedLemma: string, target: VerificationTargetView) => {
    const verification = target.verification
    if (!verification) {
      return
    }
    const lemmaKey = normalizeSearchWord(storedLemma)
    const signature = verificationResultSignature(verification, target.meaningId, target.storedSurfaceForm)
    if (signature && notifiedVerificationSignaturesRef.current[target.key] === signature) {
      return
    }
    if (signature) {
      notifiedVerificationSignaturesRef.current[target.key] = signature
    }

    if (verification.status === "queued") {
      clearWordVerificationNotification(target.key)
      return
    }

    if (verification.status === "verified" || verification.status === "skipped") {
      clearWordVerificationNotification(target.key)
      return
    }

    pushNotification(`Review needed for '${target.label}'.`, {
      kind: "word_verification",
      lemma: lemmaKey || storedLemma,
      meaningId: target.meaningId,
      surfaceForm: target.storedSurfaceForm,
      targetKey: target.key,
      status: verification.status,
      signature,
      actionCount: target.errorDetail?.suggestedActions.length ?? 0,
    })
  }, [clearWordVerificationNotification, pushNotification])

  const removeTrackedVerificationKeys = useCallback((keys: string[]) => {
    if (!keys.length) {
      return
    }
    setTrackedQueuedVerifications((current) => {
      const next = { ...current }
      let changed = false
      for (const key of keys) {
        if (key in next) {
          delete next[key]
          changed = true
        }
      }
      return changed ? next : current
    })
  }, [])

  useEffect(() => {
    const lemmaKey = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? "")
    if (!lemmaKey) {
      return
    }
    const completedKeys: string[] = []
    for (const target of verificationOverview.targets) {
      const currentStatus = target.verification?.status ?? null
      const isTrackedTarget = target.key in trackedQueuedVerifications
      const hasExistingNotification = target.key in notifiedVerificationSignaturesRef.current
      if (target.verification && (isTrackedTarget || hasExistingNotification)) {
        notifyVerificationTarget(lemmaKey, target)
      }
      if (currentStatus !== null && currentStatus !== "queued") {
        completedKeys.push(target.key)
      }
    }
    removeTrackedVerificationKeys(completedKeys)
  }, [
    lemmaDetails?.lemma,
    notifyVerificationTarget,
    removeTrackedVerificationKeys,
    selectedLemma,
    trackedQueuedVerifications,
    verificationOverview.targets,
  ])

  useEffect(() => {
    const openLemmaKey = activeSection === "wordbank" ? normalizeSearchWord(selectedLemma ?? "") : ""
    const trackedByLemma = new Map<string, TrackedQueuedVerification[]>()
    for (const tracked of Object.values(trackedQueuedVerifications)) {
      if (tracked.lemma === openLemmaKey) {
        continue
      }
      const items = trackedByLemma.get(tracked.lemma) ?? []
      items.push(tracked)
      trackedByLemma.set(tracked.lemma, items)
    }
    if (trackedByLemma.size === 0) {
      return
    }

    let cancelled = false
    let polling = false
    const pollTrackedLemmas = async () => {
      if (polling) {
        return
      }
      polling = true
      try {
        const responses = await Promise.all(
          [...trackedByLemma.keys()].map(async (lemma) => {
            try {
              const payload = await apiClient.getJson<LemmaDetailsResponse>(
                `/api/wordbank/lemmas/${encodeURIComponent(lemma)}`,
                "Could not load lemma details.",
              )
              return { lemma, payload }
            } catch {
              return { lemma, payload: null }
            }
          }),
        )
        if (cancelled) {
          return
        }
        const completedKeys: string[] = []
        for (const { lemma, payload } of responses) {
          const trackedTargets = trackedByLemma.get(lemma) ?? []
          const targetsByKey = new Map(
            collectLemmaVerificationTargets(payload).map((target) => [target.key, target]),
          )
          for (const tracked of trackedTargets) {
            const key = verificationTargetKey(tracked.lemma, tracked.meaningId, tracked.storedSurfaceForm)
            const target = targetsByKey.get(key) ?? null
            const currentStatus = target?.verification?.status ?? null
            if (target?.verification) {
              notifyVerificationTarget(lemma, target)
            }
            if (target === null || (currentStatus !== null && currentStatus !== "queued")) {
              completedKeys.push(key)
            }
          }
        }
        removeTrackedVerificationKeys(completedKeys)
      } finally {
        polling = false
      }
    }

    void pollTrackedLemmas()
    const intervalId = window.setInterval(() => {
      void pollTrackedLemmas()
    }, 1_500)
    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [
    activeSection,
    apiClient,
    notifyVerificationTarget,
    removeTrackedVerificationKeys,
    selectedLemma,
    trackedQueuedVerifications,
  ])

  const trackQueuedVerifications = useCallback((storedLemma: string, response: AddWordResponse) => {
    const lemmaKey = normalizeSearchWord(storedLemma)
    if (!lemmaKey) {
      return
    }
    const queuedTargets = response.queued_verification_targets ?? []
    if (!queuedTargets.length) {
      return
    }
    setTrackedQueuedVerifications((current) => {
      const next = { ...current }
      for (const target of queuedTargets) {
        const key = verificationTargetKey(lemmaKey, target.meaning_id ?? null, target.stored_surface_form ?? null)
        next[key] = {
          lemma: lemmaKey,
          meaningId: target.meaning_id ?? null,
          storedSurfaceForm: normalizeSearchWord(target.stored_surface_form ?? "") || null,
        }
      }
      return next
    })
  }, [])

  const trackQueuedVerificationTarget = useCallback((storedLemma: string, meaningId: number | null, storedSurfaceForm: string | null) => {
    const lemmaKey = normalizeSearchWord(storedLemma)
    if (!lemmaKey) {
      return
    }
    const normalizedSurface = normalizeSearchWord(storedSurfaceForm ?? "") || null
    const key = verificationTargetKey(lemmaKey, meaningId, normalizedSurface)
    setTrackedQueuedVerifications((current) => ({
      ...current,
      [key]: {
        lemma: lemmaKey,
        meaningId,
        storedSurfaceForm: normalizedSurface,
      },
    }))
  }, [])

  const trackQueuedVerificationTargets = useCallback((
    storedLemma: string,
    queuedTargets: Array<{ meaning_id: number | null; stored_surface_form: string | null }>,
  ) => {
    const lemmaKey = normalizeSearchWord(storedLemma)
    if (!lemmaKey || queuedTargets.length === 0) {
      return
    }
    setTrackedQueuedVerifications((current) => {
      const next = { ...current }
      for (const target of queuedTargets) {
        const normalizedSurface = normalizeSearchWord(target.stored_surface_form ?? "") || null
        const key = verificationTargetKey(lemmaKey, target.meaning_id ?? null, normalizedSurface)
        next[key] = {
          lemma: lemmaKey,
          meaningId: target.meaning_id ?? null,
          storedSurfaceForm: normalizedSurface,
        }
      }
      return next
    })
  }, [])

  const markVisibleVerificationNotificationsAsRead = useCallback(() => {
    markWordVerificationNotificationsAsRead(verificationOverview.targets.map((target) => target.key))
  }, [markWordVerificationNotificationsAsRead, verificationOverview.targets])

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

  function clearVerificationErrors() {
    notifiedVerificationSignaturesRef.current = {}
    setTrackedQueuedVerifications({})
  }

  return {
    isApplyingVerificationChanges,
    isRetryingVerification,
    rerunningMeaningVerificationById,
    isVerifyingWords: Object.keys(trackedQueuedVerifications).length > 0 || verificationOverview.queuedCount > 0,
    verificationOverview: verificationOverview as VerificationOverview,
    trackQueuedVerifications,
    trackQueuedVerificationTargets,
    applyVerificationAction,
    retryVerificationTarget,
    rerunMeaningVerification,
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
