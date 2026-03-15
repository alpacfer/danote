import { type Dispatch, type SetStateAction, useMemo, useState } from "react"

import {
  addLoadingKey,
  createApiClient,
  hasMultipleWords,
  normalizePhraseKey,
  normalizeSearchWord,
  type AddSentenceResponse,
  type AddWordResponse,
  type AnalyzedToken,
  type AppSection,
  type LemmaDetailsResponse,
  type SearchSaveSeed,
  type SearchFeedbackContext,
  type SentencebankSentence,
  type TokenFeedbackPayload,
  type WordActionSuggestion,
} from "@/app/core"
import { toast } from "sonner"

import { useCategoryRethinkingWorkflow } from "./wordbank/use-category-rethinking-workflow"
import { useCompleteVariationsWorkflow } from "./wordbank/use-complete-variations-workflow"
import { usePronunciationWorkflow } from "./wordbank/use-pronunciation-workflow"
import { useVerificationWorkflow } from "./wordbank/use-verification-workflow"

type UseWordbankWorkflowsParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
  selectedLemma: string | null
  selectedMeaningId: number | null
  lemmaDetails: LemmaDetailsResponse | null
  setLemmaDetails: Dispatch<SetStateAction<LemmaDetailsResponse | null>>
  setLemmaDetailsError: Dispatch<SetStateAction<string | null>>
  setIsLemmaDetailsLoading: Dispatch<SetStateAction<boolean>>
  setShowLemmaDetailsLoadingSkeleton: Dispatch<SetStateAction<boolean>>
  sentences: SentencebankSentence[]
  setAnalysisRefreshTick: Dispatch<SetStateAction<number>>
  setWordbankRefreshTick: Dispatch<SetStateAction<number>>
  setSentencebankRefreshTick: Dispatch<SetStateAction<number>>
  setActiveSection: (value: AppSection) => void
  setSelectedLemma: (value: string | null) => void
  setSelectedMeaningId: (value: number | null) => void
  postTokenFeedback: (payload: TokenFeedbackPayload) => Promise<void>
  onSentenceSaved?: () => void
  pushNotification: (message: string) => void
}

export function useWordbankWorkflows({
  backendUrl,
  extractErrorMessage,
  selectedLemma,
  selectedMeaningId,
  lemmaDetails,
  setLemmaDetails,
  setLemmaDetailsError,
  setIsLemmaDetailsLoading,
  setShowLemmaDetailsLoadingSkeleton,
  sentences,
  setAnalysisRefreshTick,
  setWordbankRefreshTick,
  setSentencebankRefreshTick,
  setActiveSection,
  setSelectedLemma,
  setSelectedMeaningId,
  postTokenFeedback,
  onSentenceSaved,
  pushNotification,
}: UseWordbankWorkflowsParams) {
  const [addingTokens, setAddingTokens] = useState<Record<string, boolean>>({})
  const [isSavingSentence, setIsSavingSentence] = useState(false)
  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )

  const {
    pronunciationLoadingByForm,
    isRegeneratingLemmaPronunciation,
    generatePronunciationInBackground,
    playPronunciation,
    regenerateSelectedLemmaPronunciation,
  } = usePronunciationWorkflow({
    backendUrl,
    extractErrorMessage,
    selectedLemma,
    selectedMeaningId,
    lemmaDetails,
    setWordbankRefreshTick,
  })

  const {
    isRethinkingCategories,
    rethinkCategories,
  } = useCategoryRethinkingWorkflow({
    backendUrl,
    extractErrorMessage,
    selectedLemma,
    setWordbankRefreshTick,
  })

  const {
    isCompletingMeaningVariations,
    completeMeaningVariations,
  } = useCompleteVariationsWorkflow({
    backendUrl,
    extractErrorMessage,
    selectedLemma,
    setWordbankRefreshTick,
  })

  const {
    isApplyingVerificationChanges,
    isVerifyingWords,
    verificationOverview,
    trackQueuedVerifications,
    applyVerificationAction,
    clearVerificationErrors,
  } = useVerificationWorkflow({
    backendUrl,
    extractErrorMessage,
    selectedLemma,
    lemmaDetails,
    setWordbankRefreshTick,
    pushNotification,
    onOpenWordbankTarget: (lemma, meaningId) => {
      setActiveSection("wordbank")
      setSelectedLemma(lemma)
      setSelectedMeaningId(meaningId)
    },
  })

  async function addWordToWordbank(
    surfaceToken: string,
    lemmaCandidate: string | null,
    metadata?: {
      posTag?: string | null
      morphology?: string | null
      corId?: string | null
    },
    searchSeed?: SearchSaveSeed | null,
  ): Promise<AddWordResponse> {
    const normalizedSurfaceToken = normalizeSearchWord(surfaceToken)
    const normalizedLemmaCandidate = lemmaCandidate ? normalizeSearchWord(lemmaCandidate) : null
    const normalizedPosTag = metadata?.posTag?.trim() || null
    const normalizedMorphology = metadata?.morphology?.trim() || null
    const normalizedCorId = metadata?.corId?.trim() || null
    return apiClient.postJson<AddWordResponse>(
      "/api/wordbank/lexemes",
      {
        surface_token: normalizedSurfaceToken,
        lemma_candidate: normalizedLemmaCandidate,
        ...(normalizedCorId ? { cor_id: normalizedCorId } : {}),
        ...(normalizedPosTag ? { pos_tag: normalizedPosTag } : {}),
        ...(normalizedMorphology ? { morphology: normalizedMorphology } : {}),
        ...(searchSeed ? { search_seed: searchSeed } : {}),
      },
      "Could not add word to wordbank.",
    )
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
        corId: action?.cor_id ?? null,
      })
      toast.success(payload.message)
      trackQueuedVerifications(payload.stored_lemma, payload)
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
      corId?: string | null
    },
    searchSeed?: SearchSaveSeed | null,
  ): Promise<string | null> {
    try {
      const payload = await addWordToWordbank(surfaceToken, lemmaCandidate, metadata, searchSeed)
      toast.success(payload.message)
      trackQueuedVerifications(payload.stored_lemma, payload)
      if (!searchSeed) {
        void generatePronunciationInBackground(payload.stored_lemma, payload.stored_surface_form)
      }
      void postTokenFeedback({
        raw_token: feedbackContext?.rawToken ?? surfaceToken,
        predicted_status: feedbackContext?.predictedStatus ?? "new",
        suggestions_shown: feedbackContext?.suggestionsShown ?? [],
        user_action: "add_as_new",
        chosen_value: payload.stored_lemma,
        source: "search",
      })
      if (payload.saved_snapshot) {
        setLemmaDetails(payload.saved_snapshot)
        setLemmaDetailsError(null)
        setIsLemmaDetailsLoading(false)
        setShowLemmaDetailsLoadingSkeleton(false)
      }
      setAnalysisRefreshTick((current) => current + 1)
      setWordbankRefreshTick((current) => current + 1)
      setActiveSection("wordbank")
      setSelectedLemma(payload.stored_lemma)
      setSelectedMeaningId(payload.meaning?.id ?? null)
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
      const payload = await apiClient.postJson<AddSentenceResponse>(
        "/api/sentencebank/sentences",
        {
          source_text: normalizedSelection,
        },
        "Could not save sentence.",
      )
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

  return {
    addingTokens,
    isSavingSentence,
    pronunciationLoadingByForm,
    isRegeneratingLemmaPronunciation,
    isRethinkingCategories,
    isCompletingMeaningVariations,
    isApplyingVerificationChanges,
    isVerifyingWords,
    verificationOverview,
    addTokenToWordbank,
    addWordFromSearch,
    addSentenceToSentencebank,
    playPronunciation,
    regenerateSelectedLemmaPronunciation,
    rethinkCategories,
    completeMeaningVariations,
    applyVerificationAction,
    clearVerificationErrors,
  }
}
