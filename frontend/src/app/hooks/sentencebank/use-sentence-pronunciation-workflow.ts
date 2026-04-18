import { type Dispatch, type SetStateAction, useEffect, useMemo, useRef, useState } from "react"

import {
  ApiRequestError,
  createApiClient,
  isPlayableAudioContentType,
  type GenerateSentencePronunciationResponse,
} from "@/app/core"
import { toast } from "sonner"

type UseSentencePronunciationWorkflowParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
  setSentencebankRefreshTick: Dispatch<SetStateAction<number>>
}

export function useSentencePronunciationWorkflow({
  backendUrl,
  extractErrorMessage,
  setSentencebankRefreshTick,
}: UseSentencePronunciationWorkflowParams) {
  const [pronunciationLoadingBySentenceId, setPronunciationLoadingBySentenceId] = useState<Record<string, boolean>>({})
  const [regeneratingPronunciationBySentenceId, setRegeneratingPronunciationBySentenceId] = useState<Record<string, boolean>>({})
  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )

  const pronunciationUrlBySentenceIdRef = useRef<Map<number, string>>(new Map())
  const activePronunciationAudioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    const pronunciationUrlBySentenceId = pronunciationUrlBySentenceIdRef.current
    return () => {
      for (const url of pronunciationUrlBySentenceId.values()) {
        URL.revokeObjectURL(url)
      }
      pronunciationUrlBySentenceId.clear()
      const activeAudio = activePronunciationAudioRef.current
      if (activeAudio) {
        activeAudio.pause()
        activePronunciationAudioRef.current = null
      }
    }
  }, [])

  function clearPronunciationCache(sentenceId: number) {
    const objectUrl = pronunciationUrlBySentenceIdRef.current.get(sentenceId)
    if (!objectUrl) {
      return
    }
    const activeAudio = activePronunciationAudioRef.current
    if (activeAudio?.src === objectUrl) {
      activeAudio.pause()
      activePronunciationAudioRef.current = null
    }
    URL.revokeObjectURL(objectUrl)
    pronunciationUrlBySentenceIdRef.current.delete(sentenceId)
  }

  async function playPronunciation(sentenceId: number, options?: { playbackRate?: number }) {
    if (sentenceId < 1) {
      return
    }

    setPronunciationLoadingBySentenceId((current) => ({ ...current, [sentenceId]: true }))
    try {
      let objectUrl = pronunciationUrlBySentenceIdRef.current.get(sentenceId)
      if (!objectUrl) {
        let response: Response
        try {
          response = await apiClient.getBlob(
            `/api/sentencebank/pronunciation?sentence_id=${sentenceId}`,
            "Could not load sentence pronunciation.",
          )
        } catch (error) {
          if (error instanceof ApiRequestError && error.status === 404) {
            toast.error("No pronunciation is available yet for this sentence.")
            return
          }
          throw error
        }

        const contentType = typeof response.headers?.get === "function"
          ? response.headers.get("content-type")
          : null
        if (!isPlayableAudioContentType(contentType)) {
          throw new Error(`Unsupported pronunciation format: ${contentType}`)
        }
        objectUrl = URL.createObjectURL(await response.blob())
        pronunciationUrlBySentenceIdRef.current.set(sentenceId, objectUrl)
      }

      if (activePronunciationAudioRef.current) {
        activePronunciationAudioRef.current.pause()
      }
      const audio = new Audio(objectUrl)
      audio.playbackRate = options?.playbackRate ?? 1
      activePronunciationAudioRef.current = audio
      await audio.play()
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not play sentence pronunciation."
      toast.error(message)
    } finally {
      setPronunciationLoadingBySentenceId((current) => {
        const next = { ...current }
        delete next[sentenceId]
        return next
      })
    }
  }

  async function regeneratePronunciation(sentenceId: number) {
    if (sentenceId < 1) {
      return
    }
    setRegeneratingPronunciationBySentenceId((current) => ({ ...current, [sentenceId]: true }))
    try {
      const payload = await apiClient.postJson<GenerateSentencePronunciationResponse>(
        "/api/sentencebank/sentences/pronunciation",
        { sentence_id: sentenceId, force: true },
        "Could not regenerate sentence pronunciation.",
      )
      clearPronunciationCache(sentenceId)
      if (payload.status === "generated") {
        setSentencebankRefreshTick((current) => current + 1)
        toast.success(`Regenerated pronunciation for "${payload.source_text}".`)
      } else {
        toast.error(`Could not regenerate pronunciation for "${payload.source_text}".`)
      }
    } catch {
      toast.error("Could not regenerate sentence pronunciation.")
    } finally {
      setRegeneratingPronunciationBySentenceId((current) => {
        const next = { ...current }
        delete next[sentenceId]
        return next
      })
    }
  }

  return {
    pronunciationLoadingBySentenceId,
    regeneratingPronunciationBySentenceId,
    playPronunciation: (sentenceId: number) => playPronunciation(sentenceId),
    playPronunciationSlowly: (sentenceId: number) => playPronunciation(sentenceId, { playbackRate: 0.7 }),
    regeneratePronunciation,
  }
}
