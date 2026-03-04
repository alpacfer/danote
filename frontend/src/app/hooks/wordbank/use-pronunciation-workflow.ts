import { type Dispatch, type SetStateAction, useEffect, useRef, useState } from "react"

import {
  isPlayableAudioContentType,
  isUnsupportedAudioError,
  normalizeSearchWord,
  type GeneratePronunciationResponse,
  type LemmaDetailsResponse,
} from "@/app/core"
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
  const [isRegeneratingLemmaPronunciation, setIsRegeneratingLemmaPronunciation] = useState(false)

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
    setIsRegeneratingLemmaPronunciation(false)
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
      const response = await fetch(`${backendUrl}/api/wordbank/lexemes/pronunciation`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          stored_lemma: storedLemma,
          stored_surface_form: storedSurfaceForm,
          force: Boolean(options?.force),
        }),
      })
      if (!response.ok) {
        if (options?.notify) {
          const message = await extractErrorMessage(
            response,
            `Pronunciation request failed with status ${response.status}`,
          )
          toast.error(message)
        }
        return
      }
      const payload = (await response.json()) as GeneratePronunciationResponse
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
          const response = await fetch(
            `${backendUrl}/api/wordbank/pronunciation?form=${encodeURIComponent(normalizedForm)}`,
          )
          if (!response.ok) {
            if (response.status === 404) {
              toast.error(`No pronunciation is available yet for '${normalizedForm}'.`)
              return
            }
            const message = await extractErrorMessage(
              response,
              `Pronunciation request failed with status ${response.status}`,
            )
            throw new Error(message)
          }

          const contentType = typeof response.headers?.get === "function"
            ? response.headers.get("content-type")
            : null
          if (!isPlayableAudioContentType(contentType)) {
            throw new Error(`Unsupported pronunciation format: ${contentType}`)
          }
          const audioBlob = await response.blob()
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

  async function regenerateSelectedLemmaPronunciation() {
    const lemma = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? "")
    if (!lemma) {
      return
    }
    setIsRegeneratingLemmaPronunciation(true)
    try {
      await generatePronunciationInBackground(lemma, lemma, { force: true, notify: true })
    } finally {
      setIsRegeneratingLemmaPronunciation(false)
    }
  }

  return {
    pronunciationLoadingByForm,
    isRegeneratingLemmaPronunciation,
    generatePronunciationInBackground,
    playPronunciation,
    regenerateSelectedLemmaPronunciation,
  }
}
