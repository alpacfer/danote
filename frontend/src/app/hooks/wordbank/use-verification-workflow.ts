import { type Dispatch, type SetStateAction, useCallback, useEffect, useMemo, useRef, useState } from "react"

import {
  collectLemmaVerificationOverview,
  collectLemmaVerificationTargets,
  createApiClient,
  findVerificationTarget,
  normalizeSearchWord,
  type AddWordResponse,
  type ApplyVerificationChangesResponse,
  type LemmaDetailsResponse,
  type VerificationOverview,
  verificationResultSignature,
  verificationTargetKey,
  type VerificationTargetView,
} from "@/app/core"
import { toast } from "sonner"

type UseVerificationWorkflowParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
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
      actionCount?: number
    },
  ) => void
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
  selectedLemma,
  lemmaDetails,
  setWordbankRefreshTick,
  pushNotification,
  onOpenWordbankTarget,
}: UseVerificationWorkflowParams) {
  const [isApplyingVerificationChanges, setIsApplyingVerificationChanges] = useState(false)
  const [trackedQueuedVerifications, setTrackedQueuedVerifications] = useState<Record<string, TrackedQueuedVerification>>({})
  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )
  const notifiedVerificationSignaturesRef = useRef<Record<string, string>>({})
  const previousVerificationStatusesRef = useRef<Record<string, string | null>>({})

  const verificationOverview = useMemo(
    () => collectLemmaVerificationOverview(lemmaDetails),
    [lemmaDetails],
  )

  const notifyVerificationTarget = useCallback((storedLemma: string, target: VerificationTargetView) => {
    const verification = target.verification
    if (!verification || verification.status === "skipped" || verification.status === "queued") {
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

    if (verification.status === "verified") {
      pushNotification(`Verification passed for '${target.label}'.`, {
        kind: "word_verification",
        lemma: lemmaKey || storedLemma,
        meaningId: target.meaningId,
        surfaceForm: target.storedSurfaceForm,
        actionCount: 0,
      })
      return
    }

    pushNotification(`Review needed for '${target.label}'.`, {
      kind: "word_verification",
      lemma: lemmaKey || storedLemma,
      meaningId: target.meaningId,
      surfaceForm: target.storedSurfaceForm,
      actionCount: target.errorDetail?.suggestedActions.length ?? 0,
    })
  }, [pushNotification])

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
      const previousStatus = previousVerificationStatusesRef.current[target.key] ?? null
      previousVerificationStatusesRef.current[target.key] = currentStatus
      if (previousStatus === "queued" && currentStatus !== "queued" && currentStatus !== "skipped" && target.verification) {
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
    verificationOverview.targets,
  ])

  useEffect(() => {
    const openLemmaKey = normalizeSearchWord(selectedLemma ?? "")
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
            const previousStatus = previousVerificationStatusesRef.current[key] ?? "queued"
            if (currentStatus) {
              previousVerificationStatusesRef.current[key] = currentStatus
            }
            if (previousStatus === "queued" && currentStatus !== "queued" && currentStatus !== "skipped" && target?.verification) {
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
        previousVerificationStatusesRef.current[key] = "queued"
      }
      return next
    })
  }, [])

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

  function clearVerificationErrors() {
    notifiedVerificationSignaturesRef.current = {}
    previousVerificationStatusesRef.current = {}
    setTrackedQueuedVerifications({})
  }

  return {
    isApplyingVerificationChanges,
    isVerifyingWords: Object.keys(trackedQueuedVerifications).length > 0 || verificationOverview.queuedCount > 0,
    verificationOverview: verificationOverview as VerificationOverview,
    trackQueuedVerifications,
    applyVerificationAction,
    clearVerificationErrors,
  }
}

function buildActionToastMessage(actionType: string, label: string): string {
  if (actionType === "fix_translation") {
    return `Updated translation for '${label}'.`
  }
  if (actionType === "fix_gloss") {
    return `Updated gloss for '${label}'.`
  }
  if (actionType === "move_to_meaning_section") {
    return `Moved '${label}' to a different meaning section.`
  }
  if (actionType === "move_to_lemma") {
    return `Moved '${label}' to a different lemma.`
  }
  return `Applied Gemini action for '${label}'.`
}
