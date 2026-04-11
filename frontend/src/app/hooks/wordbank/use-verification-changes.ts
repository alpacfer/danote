import { useCallback, useEffect, useMemo, useState } from "react"

import {
  createApiClient,
  normalizeSearchWord,
  type GetVerificationChangesResponse,
  type RevertVerificationChangeResponse,
  type VerificationChangeEntry,
} from "@/app/core"
import { toast } from "sonner"

type UseVerificationChangesParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
  selectedLemma: string | null
  setWordbankRefreshTick: (updater: (prev: number) => number) => void
}

export function useVerificationChanges({
  backendUrl,
  extractErrorMessage,
  selectedLemma,
  setWordbankRefreshTick,
}: UseVerificationChangesParams) {
  const [changes, setChanges] = useState<VerificationChangeEntry[]>([])
  const [isLoadingChanges, setIsLoadingChanges] = useState(false)
  const [isRevertingChange, setIsRevertingChange] = useState(false)

  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )
  const lemmaKey = normalizeSearchWord(selectedLemma ?? "")

  const refreshChanges = useCallback(async () => {
    if (!lemmaKey) {
      setChanges([])
      return
    }

    setIsLoadingChanges(true)
    try {
      const payload = await apiClient.getJson<GetVerificationChangesResponse>(
        `/api/wordbank/lexemes/verification-changes?stored_lemma=${encodeURIComponent(lemmaKey)}`,
        "Could not load verification changes.",
      )
      setChanges(payload.items)
    } catch {
      setChanges([])
    } finally {
      setIsLoadingChanges(false)
    }
  }, [apiClient, lemmaKey])

  useEffect(() => {
    void refreshChanges()
  }, [refreshChanges])

  const revertChange = useCallback(async (changeId: number) => {
    if (!lemmaKey) {
      return
    }

    setIsRevertingChange(true)
    try {
      const payload = await apiClient.postJson<RevertVerificationChangeResponse>(
        "/api/wordbank/lexemes/revert-verification-change",
        {
          change_id: changeId,
          stored_lemma: lemmaKey,
        },
        "Could not revert change.",
      )
      if (payload.status === "reverted") {
        toast.success("Change reverted.")
        setWordbankRefreshTick((current) => current + 1)
        await refreshChanges()
        return
      }
      if (payload.status === "already_reverted") {
        toast.error("This change has already been reverted.")
        await refreshChanges()
        return
      }
      toast.error("Change not found.")
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not revert change."
      toast.error(message)
    } finally {
      setIsRevertingChange(false)
    }
  }, [apiClient, lemmaKey, refreshChanges, setWordbankRefreshTick])

  return {
    changes,
    isLoadingChanges,
    isRevertingChange,
    revertChange,
    refreshChanges,
  }
}
