import { type Dispatch, type SetStateAction, useEffect, useMemo, useRef, useState } from "react"

import {
  ApiRequestError,
  createApiClient,
  isPlayableAudioContentType,
  isUnsupportedAudioError,
  normalizeSearchWord,
  type GeneratePronunciationResponse,
  type LemmaDetailsResponse,
} from "@/app/core"
import {
  fetchNumbersPronunciationBlob,
  fetchPresavedWordPronunciationBlob,
} from "@/app/core/audio-api"
import { toast } from "sonner"

type UsePronunciationWorkflowParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
  selectedLemma: string | null
  lemmaDetails: LemmaDetailsResponse | null
  setWordbankRefreshTick: Dispatch<SetStateAction<number>>
}

export function usePronunciationWorkflow({
  backendUrl,
  extractErrorMessage,
  selectedLemma,
  lemmaDetails,
  setWordbankRefreshTick,
}: UsePronunciationWorkflowParams) {
  const [pronunciationLoadingByForm, setPronunciationLoadingByForm] = useState<Record<string, boolean>>({})
  const [regeneratingPronunciationByForm, setRegeneratingPronunciationByForm] = useState<Record<string, boolean>>({})
  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )

  const pronunciationUrlByFormRef = useRef<Map<string, string>>(new Map())
  const activePronunciationAudioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    const pronunciationUrlByForm = pronunciationUrlByFormRef.current
    return () => {
      for (const url of pronunciationUrlByForm.values()) {
        URL.revokeObjectURL(url)
      }
      pronunciationUrlByForm.clear()
      const activeAudio = activePronunciationAudioRef.current
      if (activeAudio) {
        activeAudio.pause()
        activePronunciationAudioRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    setPronunciationLoadingByForm({})
    setRegeneratingPronunciationByForm({})
  }, [selectedLemma])

  function clearPronunciationCache(form: string | null | undefined) {
    const normalizedForm = normalizeSearchWord(form ?? "")
    if (!normalizedForm) {
      return
    }
    const objectUrl = pronunciationUrlByFormRef.current.get(normalizedForm)
    if (!objectUrl) {
      return
    }
    const activeAudio = activePronunciationAudioRef.current
    if (activeAudio?.src === objectUrl) {
      activeAudio.pause()
      activePronunciationAudioRef.current = null
    }
    URL.revokeObjectURL(objectUrl)
    pronunciationUrlByFormRef.current.delete(normalizedForm)
  }

  async function generatePronunciationInBackground(
    storedLemma: string,
    storedSurfaceForm: string | null,
    options?: { force?: boolean; notify?: boolean },
  ) {
    try {
      const payload = await apiClient.postJson<GeneratePronunciationResponse>(
        "/api/wordbank/lexemes/pronunciation",
        {
          stored_lemma: storedLemma,
          stored_surface_form: storedSurfaceForm,
          force: Boolean(options?.force),
        },
        "Could not regenerate pronunciation.",
      )
      clearPronunciationCache(payload.pronunciation_form)
      if (payload.status === "generated") {
        setWordbankRefreshTick((current) => current + 1)
        if (options?.notify) {
          toast.success(`Regenerated pronunciation for '${payload.pronunciation_form ?? storedLemma}'.`)
        }
      } else if (options?.notify) {
        toast.error(`Could not regenerate pronunciation for '${payload.pronunciation_form ?? storedLemma}'.`)
      }
    } catch {
      if (options?.notify) {
        toast.error("Could not regenerate pronunciation.")
      }
      // Keep add flow instant; pronunciation generation is best effort.
    }
  }

  async function playPronunciation(form: string) {
    const normalizedForm = normalizeSearchWord(form)
    if (!normalizedForm) {
      return
    }

    setPronunciationLoadingByForm((current) => ({ ...current, [normalizedForm]: true }))
    try {
      let didRepair = false
      while (true) {
        let objectUrl = pronunciationUrlByFormRef.current.get(normalizedForm)
        if (!objectUrl) {
          let audioBlob: Blob | null = null
          try {
            const response = await apiClient.getBlob(
              `/api/wordbank/pronunciation?form=${encodeURIComponent(normalizedForm)}`,
              "Could not load pronunciation.",
            )
            const contentType = typeof response.headers?.get === "function"
              ? response.headers.get("content-type")
              : null
            if (!isPlayableAudioContentType(contentType)) {
              throw new Error(`Unsupported pronunciation format: ${contentType}`)
            }
            audioBlob = await response.blob()
          } catch (error) {
            if (error instanceof ApiRequestError && error.status === 404) {
              audioBlob = await fetchPresavedWordPronunciationBlob(normalizedForm)
              if (!audioBlob) {
                audioBlob = await fetchNumbersPronunciationBlob(normalizedForm)
              }
              if (!audioBlob) {
                toast.error(`No pronunciation is available yet for '${normalizedForm}'.`)
                return
              }
            } else {
              throw error
            }
          }
          objectUrl = URL.createObjectURL(audioBlob)
          pronunciationUrlByFormRef.current.set(normalizedForm, objectUrl)
        }

        if (activePronunciationAudioRef.current) {
          activePronunciationAudioRef.current.pause()
        }
        const audio = new Audio(objectUrl)
        activePronunciationAudioRef.current = audio
        try {
          await audio.play()
          break
        } catch (error) {
          if (!didRepair && isUnsupportedAudioError(error)) {
            didRepair = true
            clearPronunciationCache(normalizedForm)
            const selectedLemmaKey = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? normalizedForm)
            const storedSurface = normalizedForm === selectedLemmaKey ? selectedLemmaKey : normalizedForm
            await generatePronunciationInBackground(selectedLemmaKey, storedSurface, { force: true, notify: false })
            continue
          }
          throw error
        }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not play pronunciation."
      toast.error(message)
      void error
    } finally {
      setPronunciationLoadingByForm((current) => {
        const next = { ...current }
        delete next[normalizedForm]
        return next
      })
    }
  }

  async function regeneratePronunciation(form: string) {
    const storedLemma = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? "")
    const storedSurfaceForm = normalizeSearchWord(form)
    if (!storedLemma || !storedSurfaceForm) {
      return
    }
    setRegeneratingPronunciationByForm((current) => ({ ...current, [storedSurfaceForm]: true }))
    try {
      await generatePronunciationInBackground(storedLemma, storedSurfaceForm, { force: true, notify: true })
    } finally {
      setRegeneratingPronunciationByForm((current) => {
        const next = { ...current }
        delete next[storedSurfaceForm]
        return next
      })
    }
  }

  return {
    pronunciationLoadingByForm,
    regeneratingPronunciationByForm,
    generatePronunciationInBackground,
    playPronunciation,
    regeneratePronunciation,
  }
}
