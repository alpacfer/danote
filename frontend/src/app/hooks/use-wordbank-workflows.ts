import { type Dispatch, type SetStateAction, useEffect, useMemo, useRef, useState } from "react"

import {
  addLoadingKey,
  buildVerificationErrorDetail,
  hasMultipleWords,
  isPlayableAudioContentType,
  isUnsupportedAudioError,
  normalizePhraseKey,
  normalizeSearchWord,
  type AddSentenceResponse,
  type AddWordResponse,
  type AnalyzedToken,
  type AppSection,
  type ApplyVerificationChangesResponse,
  type GeneratePronunciationResponse,
  type LemmaDetailsResponse,
  type SearchFeedbackContext,
  type SentencebankSentence,
  type TokenFeedbackPayload,
  type VerifyWordResponse,
  type VerificationErrorDetail,
  type WordActionSuggestion,
} from "@/app/core"
import { toast } from "sonner"

type UseWordbankWorkflowsParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
  selectedLemma: string | null
  lemmaDetails: LemmaDetailsResponse | null
  sentences: SentencebankSentence[]
  setAnalysisRefreshTick: Dispatch<SetStateAction<number>>
  setWordbankRefreshTick: Dispatch<SetStateAction<number>>
  setSentencebankRefreshTick: Dispatch<SetStateAction<number>>
  setActiveSection: (value: AppSection) => void
  setSelectedLemma: (value: string | null) => void
  postTokenFeedback: (payload: TokenFeedbackPayload) => Promise<void>
  onSentenceSaved?: () => void
  pushNotification: (message: string) => void
}

export function useWordbankWorkflows({
  backendUrl,
  extractErrorMessage,
  selectedLemma,
  lemmaDetails,
  sentences,
  setAnalysisRefreshTick,
  setWordbankRefreshTick,
  setSentencebankRefreshTick,
  setActiveSection,
  setSelectedLemma,
  postTokenFeedback,
  onSentenceSaved,
  pushNotification,
}: UseWordbankWorkflowsParams) {
  const [addingTokens, setAddingTokens] = useState<Record<string, boolean>>({})
  const [isSavingSentence, setIsSavingSentence] = useState(false)
  const [pronunciationLoadingByForm, setPronunciationLoadingByForm] = useState<Record<string, boolean>>({})
  const [isRegeneratingLemmaPronunciation, setIsRegeneratingLemmaPronunciation] = useState(false)
  const [isApplyingVerificationChanges, setIsApplyingVerificationChanges] = useState(false)
  const [verificationErrorsByLemma, setVerificationErrorsByLemma] = useState<Record<string, VerificationErrorDetail>>({})

  const pronunciationUrlByFormRef = useRef<Map<string, string>>(new Map())
  const activePronunciationAudioRef = useRef<HTMLAudioElement | null>(null)

  const selectedLemmaVerificationError = useMemo(() => {
    const lemmaKey = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? "")
    if (!lemmaKey) {
      return null
    }
    return verificationErrorsByLemma[lemmaKey] ?? null
  }, [lemmaDetails?.lemma, selectedLemma, verificationErrorsByLemma])

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

  function notifyWordVerification(
    storedLemma: string,
    storedSurfaceForm: string | null,
    verification: VerifyWordResponse["verification"],
  ) {
    if (!verification || verification.status === "skipped" || verification.status === "queued") {
      return
    }

    const isOk = verification.status === "verified"
    const lemmaKey = normalizeSearchWord(storedLemma)
    if (isOk) {
      setVerificationErrorsByLemma((current) => {
        if (!Object.hasOwn(current, lemmaKey)) {
          return current
        }
        const next = { ...current }
        delete next[lemmaKey]
        return next
      })
      pushNotification("OK")
      return
    }

    const detail = buildVerificationErrorDetail({
      provider: verification.provider,
      status: verification.status === "flagged" ? "flagged" : "error",
      message: verification.message,
      composedWordCount: verification.composed_word_count,
      storedSurfaceForm,
      problem: verification.problem,
      changeToImplement: verification.change_to_implement,
      suggestedChanges: verification.suggested_changes,
    })
    setVerificationErrorsByLemma((current) => ({ ...current, [lemmaKey]: detail }))
    const displayLemma = lemmaKey || storedLemma || "word"
    pushNotification(`ERROR ${displayLemma}: ${detail.problem} Change: ${detail.changeToImplement}`)
  }

  async function verifyWordInBackground(storedLemma: string, storedSurfaceForm: string | null) {
    try {
      const response = await fetch(`${backendUrl}/api/wordbank/lexemes/verify`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          stored_lemma: storedLemma,
          stored_surface_form: storedSurfaceForm,
        }),
      })
      if (!response.ok) {
        const message = await extractErrorMessage(
          response,
          `Verify word request failed with status ${response.status}`,
        )
        throw new Error(message)
      }
      const payload = (await response.json()) as VerifyWordResponse
      notifyWordVerification(payload.stored_lemma, payload.stored_surface_form, payload.verification)
    } catch (error) {
      const message = error instanceof Error ? error.message : null
      const lemmaKey = normalizeSearchWord(storedLemma)
      const detail = buildVerificationErrorDetail({
        provider: "gemini",
        status: "error",
        message,
        storedSurfaceForm,
      })
      setVerificationErrorsByLemma((current) => ({ ...current, [lemmaKey]: detail }))
      pushNotification(`ERROR ${lemmaKey || storedLemma}: ${detail.problem} Change: ${detail.changeToImplement}`)
    }
  }

  async function addWordToWordbank(
    surfaceToken: string,
    lemmaCandidate: string | null,
    metadata?: {
      posTag?: string | null
      morphology?: string | null
    },
  ): Promise<AddWordResponse> {
    const normalizedSurfaceToken = normalizeSearchWord(surfaceToken)
    const normalizedLemmaCandidate = lemmaCandidate ? normalizeSearchWord(lemmaCandidate) : null
    const normalizedPosTag = metadata?.posTag?.trim() || null
    const normalizedMorphology = metadata?.morphology?.trim() || null
    const response = await fetch(`${backendUrl}/api/wordbank/lexemes`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(
        {
          surface_token: normalizedSurfaceToken,
          lemma_candidate: normalizedLemmaCandidate,
          ...(normalizedPosTag ? { pos_tag: normalizedPosTag } : {}),
          ...(normalizedMorphology ? { morphology: normalizedMorphology } : {}),
        },
      ),
    })

    if (!response.ok) {
      const message = await extractErrorMessage(
        response,
        `Add word request failed with status ${response.status}`,
      )
      throw new Error(message)
    }

    return (await response.json()) as AddWordResponse
  }

  async function addTokenToWordbank(token: AnalyzedToken, action?: WordActionSuggestion) {
    const requestSurface = action?.surface ?? (token.normalized_token || token.surface_token)
    const requestLemma = action?.lemma ?? token.lemma_candidate
    const loadingKey = addLoadingKey(token)

    setAddingTokens((current) => ({ ...current, [loadingKey]: true }))

    try {
      const payload = await addWordToWordbank(requestSurface, requestLemma, {
        posTag: action?.pos_tag,
        morphology: action?.morphology,
      })
      toast.success(payload.message)
      void verifyWordInBackground(payload.stored_lemma, payload.stored_surface_form)
      void generatePronunciationInBackground(payload.stored_lemma, payload.stored_surface_form)
      void postTokenFeedback({
        raw_token: token.surface_token,
        predicted_status: token.classification,
        suggestions_shown: (token.suggestions ?? []).map((item) => item.value),
        user_action: "add_as_new",
        chosen_value: payload.stored_lemma,
        source: "playground",
      })
      setAnalysisRefreshTick((current) => current + 1)
      setWordbankRefreshTick((current) => current + 1)
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not add word to wordbank. Try again."
      toast.error(message)
      void error
    } finally {
      setAddingTokens((current) => {
        const next = { ...current }
        delete next[loadingKey]
        return next
      })
    }
  }

  async function addWordFromSearch(
    surfaceToken: string,
    lemmaCandidate: string | null,
    feedbackContext?: SearchFeedbackContext,
    metadata?: {
      posTag?: string | null
      morphology?: string | null
    },
  ): Promise<string | null> {
    try {
      const payload = await addWordToWordbank(surfaceToken, lemmaCandidate, metadata)
      toast.success(payload.message)
      void verifyWordInBackground(payload.stored_lemma, payload.stored_surface_form)
      void generatePronunciationInBackground(payload.stored_lemma, payload.stored_surface_form)
      void postTokenFeedback({
        raw_token: feedbackContext?.rawToken ?? surfaceToken,
        predicted_status: feedbackContext?.predictedStatus ?? "new",
        suggestions_shown: feedbackContext?.suggestionsShown ?? [],
        user_action: "add_as_new",
        chosen_value: payload.stored_lemma,
        source: "search",
      })
      setAnalysisRefreshTick((current) => current + 1)
      setWordbankRefreshTick((current) => current + 1)
      setActiveSection("wordbank")
      setSelectedLemma(payload.stored_lemma)
      return payload.stored_lemma
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not add word to wordbank. Try again."
      toast.error(message)
      return null
    }
  }

  async function addSentenceToSentencebank(selectedText: string) {
    const normalizedSelection = selectedText.replace(/\s+/gu, " ").trim()
    if (!normalizedSelection || !hasMultipleWords(normalizedSelection)) {
      return
    }
    const selectionKey = normalizePhraseKey(normalizedSelection)
    if (sentences.some((sentence) => normalizePhraseKey(sentence.source_text) === selectionKey)) {
      return
    }

    setIsSavingSentence(true)
    try {
      const response = await fetch(`${backendUrl}/api/sentencebank/sentences`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          source_text: normalizedSelection,
        }),
      })
      if (!response.ok) {
        const message = await extractErrorMessage(
          response,
          `Save sentence request failed with status ${response.status}`,
        )
        throw new Error(message)
      }

      const payload = (await response.json()) as AddSentenceResponse
      toast.success(payload.message)
      setSentencebankRefreshTick((current) => current + 1)
      onSentenceSaved?.()
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not save sentence. Try again."
      toast.error(message)
      void error
    } finally {
      setIsSavingSentence(false)
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

  function hasSuggestedVerificationChanges(detail: VerificationErrorDetail | null): boolean {
    if (!detail?.suggestedChangesPayload) {
      return false
    }
    return Object.values(detail.suggestedChangesPayload).some((value) => typeof value === "string" && value.trim().length > 0)
  }

  async function applySelectedLemmaVerificationChanges() {
    const lemma = normalizeSearchWord(lemmaDetails?.lemma ?? selectedLemma ?? "")
    if (!lemma) {
      return
    }
    const detail = verificationErrorsByLemma[lemma] ?? null
    if (!detail || !hasSuggestedVerificationChanges(detail) || !detail.suggestedChangesPayload) {
      return
    }

    setIsApplyingVerificationChanges(true)
    try {
      const response = await fetch(`${backendUrl}/api/wordbank/lexemes/apply-verification-changes`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          stored_lemma: lemma,
          stored_surface_form: detail.storedSurfaceForm ?? lemma,
          suggested_changes: detail.suggestedChangesPayload,
          provider: detail.provider,
        }),
      })
      if (!response.ok) {
        const message = await extractErrorMessage(
          response,
          `Apply verification changes failed with status ${response.status}`,
        )
        throw new Error(message)
      }

      const payload = (await response.json()) as ApplyVerificationChangesResponse
      if (payload.status === "applied") {
        const count = payload.applied_fields.length
        toast.success(
          count > 0
            ? `Applied ${count} Gemini change${count === 1 ? "" : "s"} for '${lemma}'.`
            : `Applied Gemini changes for '${lemma}'.`,
        )
        setVerificationErrorsByLemma((current) => {
          if (!Object.hasOwn(current, lemma)) {
            return current
          }
          const next = { ...current }
          delete next[lemma]
          return next
        })
        setWordbankRefreshTick((current) => current + 1)
      } else {
        toast.error("No Gemini changes were applied.")
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not apply Gemini changes."
      toast.error(message)
    } finally {
      setIsApplyingVerificationChanges(false)
    }
  }

  function clearVerificationErrors() {
    setVerificationErrorsByLemma({})
  }

  return {
    addingTokens,
    isSavingSentence,
    pronunciationLoadingByForm,
    isRegeneratingLemmaPronunciation,
    isApplyingVerificationChanges,
    selectedLemmaVerificationError,
    hasSuggestedVerificationChanges,
    addTokenToWordbank,
    addWordFromSearch,
    addSentenceToSentencebank,
    playPronunciation,
    regenerateSelectedLemmaPronunciation,
    applySelectedLemmaVerificationChanges,
    clearVerificationErrors,
  }
}
