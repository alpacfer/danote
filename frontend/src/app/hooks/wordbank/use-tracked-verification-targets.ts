import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import {
  collectLemmaVerificationTargets,
  createApiClient,
  normalizeSearchWord,
  type AddWordResponse,
  type AppSection,
  type LemmaDetailsResponse,
  type VerificationOverview,
  type VerificationAction,
  verificationResultSignature,
  verificationTargetKey,
  type VerificationTargetView,
} from "@/app/core"

import { usePostVerificationDetailRefresh } from "./use-post-verification-detail-refresh"

const TRACKED_VERIFICATION_POLL_INTERVAL_MS = 500
const AUTO_APPLY_SETTLE_WINDOW_MS = 5_000
const AUTO_APPLY_ACTION_TYPES = new Set<VerificationAction["action_type"]>(["fix_translation", "fix_variations"])

type UseTrackedVerificationTargetsParams = {
  activeSection: AppSection
  apiClient: ReturnType<typeof createApiClient>
  clearWordVerificationNotification: (targetKey: string) => void
  lemmaDetails: LemmaDetailsResponse | null
  markWordVerificationNotificationsAsRead: (targetKeys: string[]) => void
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
  onOpenLemmaVerificationCompleted?: (payload: LemmaDetailsResponse) => void
  onAnyVerificationCompleted?: () => void
  selectedLemma: string | null
  verificationOverview: VerificationOverview
}

type TrackedQueuedVerification = {
  lemma: string
  meaningId: number | null
  storedSurfaceForm: string | null
}

export function useTrackedVerificationTargets({
  activeSection,
  apiClient,
  clearWordVerificationNotification,
  lemmaDetails,
  markWordVerificationNotificationsAsRead,
  pushNotification,
  onOpenLemmaVerificationCompleted,
  onAnyVerificationCompleted,
  selectedLemma,
  verificationOverview,
}: UseTrackedVerificationTargetsParams) {
  const [trackedQueuedVerifications, setTrackedQueuedVerifications] = useState<Record<string, TrackedQueuedVerification>>({})
  const notifiedVerificationSignaturesRef = useRef<Record<string, string>>({})
  const scheduleOpenLemmaCompletionRefresh = usePostVerificationDetailRefresh({
    activeSection,
    apiClient,
    onOpenLemmaVerificationCompleted,
    selectedLemma,
  })

  const notifyVerificationTarget = useCallback((storedLemma: string, target: VerificationTargetView) => {
    const verification = target.verification
    if (!verification) {
      return
    }
    if (isAutoApplySettling(target)) {
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
      const isSettlingAutoApply = isAutoApplySettling(target)
      if (target.verification && (isTrackedTarget || hasExistingNotification)) {
        notifyVerificationTarget(lemmaKey, target)
      }
      if (currentStatus !== null && currentStatus !== "queued" && !isSettlingAutoApply) {
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
        let refreshedOpenLemmaPayload: LemmaDetailsResponse | null = null
        for (const { lemma, payload } of responses) {
          const trackedTargets = trackedByLemma.get(lemma) ?? []
          const targetsByKey = new Map(
            collectLemmaVerificationTargets(payload).map((target) => [target.key, target]),
          )
          let shouldRefreshTrackedLemma = false
          for (const tracked of trackedTargets) {
            const key = verificationTargetKey(tracked.lemma, tracked.meaningId, tracked.storedSurfaceForm)
            const target = targetsByKey.get(key) ?? null
            const currentStatus = target?.verification?.status ?? null
            const isSettlingAutoApply = target ? isAutoApplySettling(target) : false
            if (target?.verification) {
              notifyVerificationTarget(lemma, target)
            }
            if (target === null || (currentStatus !== null && currentStatus !== "queued" && !isSettlingAutoApply)) {
              completedKeys.push(key)
              shouldRefreshTrackedLemma = true
            }
          }
          if (lemma === openLemmaKey && payload !== null && shouldRefreshTrackedLemma) {
            refreshedOpenLemmaPayload = payload
          }
        }
        removeTrackedVerificationKeys(completedKeys)
        if (refreshedOpenLemmaPayload) {
          onOpenLemmaVerificationCompleted?.(refreshedOpenLemmaPayload)
          scheduleOpenLemmaCompletionRefresh(openLemmaKey)
        }
        if (completedKeys.length > 0) {
          onAnyVerificationCompleted?.()
        }
      } finally {
        polling = false
      }
    }

    void pollTrackedLemmas()
    const intervalId = window.setInterval(() => {
      void pollTrackedLemmas()
    }, TRACKED_VERIFICATION_POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [
    activeSection,
    apiClient,
    notifyVerificationTarget,
    onAnyVerificationCompleted,
    onOpenLemmaVerificationCompleted,
    removeTrackedVerificationKeys,
    scheduleOpenLemmaCompletionRefresh,
    selectedLemma,
    trackedQueuedVerifications,
  ])

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

  const trackQueuedVerifications = useCallback((storedLemma: string, response: AddWordResponse) => {
    trackQueuedVerificationTargets(storedLemma, response.queued_verification_targets ?? [])
  }, [trackQueuedVerificationTargets])

  const markVisibleVerificationNotificationsAsRead = useMemo(
    () => () => markWordVerificationNotificationsAsRead(verificationOverview.targets.map((target) => target.key)),
    [markWordVerificationNotificationsAsRead, verificationOverview.targets],
  )

  const clearVerificationErrors = useCallback(() => {
    notifiedVerificationSignaturesRef.current = {}
    setTrackedQueuedVerifications({})
  }, [])

  return {
    clearVerificationErrors,
    isVerifyingWords: Object.keys(trackedQueuedVerifications).length > 0 || verificationOverview.queuedCount > 0,
    markVisibleVerificationNotificationsAsRead,
    trackQueuedVerificationTarget,
    trackQueuedVerificationTargets,
    trackQueuedVerifications,
  }
}

function isAutoApplySettling(target: VerificationTargetView): boolean {
  const verification = target.verification
  const suggestedActions = verification?.suggested_actions ?? []
  if (!verification || (verification.status !== "flagged" && verification.status !== "error")) {
    return false
  }
  if (suggestedActions.length === 0 || suggestedActions.some((action) => !AUTO_APPLY_ACTION_TYPES.has(action.action_type))) {
    return false
  }
  const completedAt = verification.completed_at ?? verification.requested_at
  if (!completedAt) {
    return false
  }
  const completedAtMillis = Date.parse(completedAt)
  if (Number.isNaN(completedAtMillis)) {
    return false
  }
  return Date.now() - completedAtMillis <= AUTO_APPLY_SETTLE_WINDOW_MS
}
