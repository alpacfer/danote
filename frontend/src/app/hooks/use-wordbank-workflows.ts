import { type Dispatch, type SetStateAction, useMemo, useState } from "react"

import {
  createApiClient,
  hasMultipleWords,
  normalizePhraseKey,
  normalizeSearchWord,
  type AddSentenceResponse,
  type AddWordResponse,
  type AppSection,
  type LemmaDetailsResponse,
  type SearchSaveSeed,
  type SearchFeedbackContext,
  type SentencebankSentence,
  type TokenFeedbackPayload,
} from "@/app/core"
import { toast } from "sonner"

import { useSentencePronunciationWorkflow } from "./sentencebank/use-sentence-pronunciation-workflow"
import { useAlternativeTranslationsWorkflow } from "./wordbank/use-alternative-translations-workflow"
import { useCategoryRethinkingWorkflow } from "./wordbank/use-category-rethinking-workflow"
import { useCompleteVariationsWorkflow } from "./wordbank/use-complete-variations-workflow"
import { usePronunciationWorkflow } from "./wordbank/use-pronunciation-workflow"
import { useVerificationWorkflow } from "./wordbank/use-verification-workflow"

type UseWordbankWorkflowsParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
  activeSection: AppSection
  selectedLemma: string | null
  lemmaDetails: LemmaDetailsResponse | null
  setLemmaDetails: Dispatch<SetStateAction<LemmaDetailsResponse | null>>
  setLemmaDetailsError: Dispatch<SetStateAction<string | null>>
  setIsLemmaDetailsLoading: Dispatch<SetStateAction<boolean>>
  setShowLemmaDetailsLoadingSkeleton: Dispatch<SetStateAction<boolean>>
  trackQueuedPronunciationForms: (lemma: string, forms: string[]) => void
  sentences: SentencebankSentence[]
  setSentences: Dispatch<SetStateAction<SentencebankSentence[]>>
  setAnalysisRefreshTick: Dispatch<SetStateAction<number>>
  setWordbankRefreshTick: Dispatch<SetStateAction<number>>
  setSentencebankRefreshTick: Dispatch<SetStateAction<number>>
  setActiveSection: (value: AppSection) => void
  setSelectedLemma: (value: string | null) => void
  setSelectedMeaningId: (value: number | null) => void
  openPendingSentence: (text: string, englishTranslation?: string | null) => void
  openSentence: (id: number) => void
  openWordbankTarget: (lemma: string, meaningId: number | null) => void
  postTokenFeedback: (payload: TokenFeedbackPayload) => Promise<void>
  onSentenceSaved?: () => void
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
}

export function useWordbankWorkflows({
  backendUrl,
  extractErrorMessage,
  activeSection,
  selectedLemma,
  lemmaDetails,
  setLemmaDetails,
  setLemmaDetailsError,
  setIsLemmaDetailsLoading,
  setShowLemmaDetailsLoadingSkeleton,
  trackQueuedPronunciationForms,
  sentences,
  setSentences,
  setAnalysisRefreshTick,
  setWordbankRefreshTick,
  setSentencebankRefreshTick,
  setActiveSection,
  setSelectedLemma,
  setSelectedMeaningId,
  openPendingSentence,
  openSentence,
  openWordbankTarget,
  postTokenFeedback,
  onSentenceSaved,
  pushNotification,
  markWordVerificationNotificationsAsRead,
  clearWordVerificationNotification,
}: UseWordbankWorkflowsParams) {
  const [isSavingSentence, setIsSavingSentence] = useState(false)
  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )

  const {
    pronunciationLoadingByForm,
    regeneratingPronunciationByForm,
    playPronunciation,
    regeneratePronunciation,
  } = usePronunciationWorkflow({
    backendUrl,
    extractErrorMessage,
    selectedLemma,
    lemmaDetails,
    setWordbankRefreshTick,
  })
  const {
    pronunciationLoadingBySentenceId,
    regeneratingPronunciationBySentenceId,
    playPronunciation: playSentencePronunciation,
    playPronunciationSlowly: playSentencePronunciationSlowly,
    regeneratePronunciation: regenerateSentencePronunciation,
  } = useSentencePronunciationWorkflow({
    backendUrl,
    extractErrorMessage,
    setSentencebankRefreshTick,
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
    isFindingAlternativeTranslations,
    findAlternativeTranslations,
  } = useAlternativeTranslationsWorkflow({
    backendUrl,
    extractErrorMessage,
    selectedLemma,
    setWordbankRefreshTick,
  })

  const {
    isApplyingVerificationChanges,
    isRetryingVerification,
    rerunningMeaningVerificationById,
    isVerifyingWords,
    verificationOverview,
    changes,
    isLoadingChanges,
    isRevertingChange,
    trackQueuedVerifications,
    trackQueuedVerificationTargets,
    applyVerificationAction,
    retryVerificationTarget,
    rerunMeaningVerification,
    revertChange,
    markVisibleVerificationNotificationsAsRead,
    clearVerificationErrors,
  } = useVerificationWorkflow({
    backendUrl,
    extractErrorMessage,
    activeSection,
    selectedLemma,
    lemmaDetails,
    setLemmaDetails,
    setWordbankRefreshTick,
    pushNotification,
    markWordVerificationNotificationsAsRead,
    clearWordVerificationNotification,
    onOpenWordbankTarget: (lemma, meaningId) => {
      setActiveSection("wordbank")
      setSelectedLemma(lemma)
      setSelectedMeaningId(meaningId)
    },
  })

  const {
    isCompletingMeaningVariations,
    completeMeaningVariations,
  } = useCompleteVariationsWorkflow({
    backendUrl,
    extractErrorMessage,
    selectedLemma,
    setWordbankRefreshTick,
    trackQueuedPronunciationForms,
    trackQueuedVerificationTargets,
  })

  function upsertSentence(payload: AddSentenceResponse) {
    if (payload.id == null) {
      return
    }
    const nextSentence: SentencebankSentence = {
      id: payload.id,
      source_text: payload.source_text,
      english_translation: payload.english_translation,
      created_at: payload.created_at ?? new Date().toISOString(),
      has_pronunciation: payload.has_pronunciation ?? false,
      tokens: payload.tokens ?? [],
    }
    setSentences((current) => {
      const existingIndex = current.findIndex((sentence) => sentence.id === nextSentence.id)
      if (existingIndex === -1) {
        return [nextSentence, ...current]
      }
      const next = [...current]
      next[existingIndex] = nextSentence
      return next
    })
  }

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
      trackQueuedPronunciationForms(payload.stored_lemma, payload.queued_pronunciation_forms ?? [])
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

  async function addSentenceToSentencebank(selectedText: string, englishTranslation: string | null = null) {
    const normalizedSelection = selectedText.replace(/\s+/gu, " ").trim()
    if (!normalizedSelection || !hasMultipleWords(normalizedSelection)) {
      return
    }
    const selectionKey = normalizePhraseKey(normalizedSelection)
    if (sentences.some((sentence) => normalizePhraseKey(sentence.source_text) === selectionKey)) {
      toast.info("Sentence already saved.")
      return
    }

    openPendingSentence(normalizedSelection, englishTranslation)
    onSentenceSaved?.()
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
      upsertSentence(payload)
      setSentencebankRefreshTick((current) => current + 1)
      if (payload.status === "inserted") {
        setWordbankRefreshTick((current) => current + 1)
      }
      if (payload.id != null) {
        openSentence(payload.id)
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not save sentence. Try again."
      toast.error(message)
      void error
    } finally {
      setIsSavingSentence(false)
    }
  }

  async function saveRelatedWordFromSearchSeed(
    surfaceToken: string,
    lemmaCandidate: string | null,
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
      trackQueuedPronunciationForms(payload.stored_lemma, payload.queued_pronunciation_forms ?? [])
      setWordbankRefreshTick((current) => current + 1)
      return payload.stored_lemma
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not add related word to wordbank. Try again."
      toast.error(message)
      return null
    }
  }

  return {
    isSavingSentence,
    pronunciationLoadingByForm,
    regeneratingPronunciationByForm,
    pronunciationLoadingBySentenceId,
    regeneratingPronunciationBySentenceId,
    isFindingAlternativeTranslations,
    isRethinkingCategories,
    isCompletingMeaningVariations,
    isApplyingVerificationChanges,
    isRetryingVerification,
    rerunningMeaningVerificationById,
    isVerifyingWords,
    verificationOverview,
    verificationChanges: changes,
    isLoadingVerificationChanges: isLoadingChanges,
    isRevertingVerificationChange: isRevertingChange,
    markVisibleVerificationNotificationsAsRead,
    addWordFromSearch,
    saveRelatedWordFromSearchSeed,
    addSentenceToSentencebank,
    playPronunciation,
    regeneratePronunciation,
    playSentencePronunciation,
    playSentencePronunciationSlowly,
    regenerateSentencePronunciation,
    findAlternativeTranslations,
    rethinkCategories,
    completeMeaningVariations,
    applyVerificationAction,
    retryVerificationTarget,
    rerunMeaningVerification,
    revertVerificationChange: revertChange,
    clearVerificationErrors,
    openRelatedWordTarget: openWordbankTarget,
  }
}
