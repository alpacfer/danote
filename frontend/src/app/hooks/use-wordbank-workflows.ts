import { type Dispatch, type SetStateAction, useMemo, useState } from "react"

import {
  createApiClient,
  hasMultipleWords,
  normalizePhraseKey,
  normalizeSearchWord,
  type AddSentenceResponse,
  type AddWordResponse,
  type AppSection,
  type GenerateExamplePreviewResponse,
  type LemmaDetailsResponse,
  type SearchSaveSeed,
  type SearchFeedbackContext,
  type SentencebankSentence,
  type SentenceTokenCard,
  type SaveSentenceTokenResponse,
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
  openPendingSentence: (text: string, englishTranslation?: string | null) => void
  openSentence: (id: number) => void
  replaceCurrentSentence: (id: number) => void
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
  openPendingSentence,
  openSentence,
  replaceCurrentSentence,
  openWordbankTarget,
  postTokenFeedback,
  onSentenceSaved,
  pushNotification,
  markWordVerificationNotificationsAsRead,
  clearWordVerificationNotification,
}: UseWordbankWorkflowsParams) {
  const [isSavingSentence, setIsSavingSentence] = useState(false)
  const [generatedExamplePreview, setGeneratedExamplePreview] = useState<{
    source_text: string
    english_translation: string
    target:
      | { kind: "wordbank"; stored_lemma: string; meaning_id: number }
      | { kind: "static"; stored_lemma: string }
  } | null>(null)
  const [generatingExampleByMeaningId, setGeneratingExampleByMeaningId] = useState<Record<number, boolean>>({})
  const [generatingStaticExampleByLemma, setGeneratingStaticExampleByLemma] = useState<Record<string, boolean>>({})
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
      openWordbankTarget(lemma, meaningId)
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
      openWordbankTarget(payload.stored_lemma, payload.meaning?.id ?? null)
      return payload.stored_lemma
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not add word to wordbank. Try again."
      toast.error(message)
      return null
    }
  }

  async function addSentenceToSentencebank(
    selectedText: string,
    englishTranslation: string | null = null,
    options?: {
      tokenPersistenceMode?: "auto_save_all" | "link_existing_only"
      target?: { stored_lemma: string; meaning_id: number }
      skipPendingView?: boolean
    },
  ) {
    const normalizedSelection = selectedText.replace(/\s+/gu, " ").trim()
    if (!normalizedSelection || !hasMultipleWords(normalizedSelection)) {
      return
    }
    const selectionKey = normalizePhraseKey(normalizedSelection)
    if (sentences.some((sentence) => normalizePhraseKey(sentence.source_text) === selectionKey)) {
      toast.info("Sentence already saved.")
      return
    }

    if (!options?.skipPendingView) {
      openPendingSentence(normalizedSelection, englishTranslation)
    }
    onSentenceSaved?.()
    setIsSavingSentence(true)
    try {
      const payload = await apiClient.postJson<AddSentenceResponse>(
        "/api/sentencebank/sentences",
        {
          source_text: normalizedSelection,
          ...(englishTranslation ? { english_translation: englishTranslation } : {}),
          ...(options?.tokenPersistenceMode ? { token_persistence_mode: options.tokenPersistenceMode } : {}),
          ...(options?.target ? { target: options.target } : {}),
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
        setGeneratedExamplePreview(null)
        if (options?.skipPendingView) {
          openSentence(payload.id)
        } else {
          replaceCurrentSentence(payload.id)
        }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not save sentence. Try again."
      toast.error(message)
      void error
    } finally {
      setIsSavingSentence(false)
    }
  }

  async function generateExampleForMeaning(storedLemma: string, meaningId: number, tenseLabel?: string) {
    setGeneratingExampleByMeaningId((current) => ({ ...current, [meaningId]: true }))
    try {
      const payload = await apiClient.postJson<GenerateExamplePreviewResponse>(
        "/api/sentencebank/example-preview",
        {
          stored_lemma: storedLemma,
          meaning_id: meaningId,
          ...(tenseLabel ? { tense_label: tenseLabel } : {}),
        },
        "Could not generate example.",
      )
      setGeneratedExamplePreview({
        source_text: payload.source_text,
        english_translation: payload.english_translation,
        target: { kind: "wordbank", stored_lemma: storedLemma, meaning_id: meaningId },
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not generate example. Try again."
      toast.error(message)
    } finally {
      setGeneratingExampleByMeaningId((current) => ({ ...current, [meaningId]: false }))
    }
  }

  async function generateStaticExampleForLemma(storedLemma: string) {
    const normalizedLemma = normalizeSearchWord(storedLemma)
    if (!normalizedLemma) {
      return
    }
    setGeneratingStaticExampleByLemma((current) => ({ ...current, [normalizedLemma]: true }))
    try {
      const payload = await apiClient.postJson<GenerateExamplePreviewResponse>(
        "/api/sentencebank/static-example-preview",
        { stored_lemma: normalizedLemma },
        "Could not generate example.",
      )
      setGeneratedExamplePreview({
        source_text: payload.source_text,
        english_translation: payload.english_translation,
        target: { kind: "static", stored_lemma: normalizedLemma },
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not generate example. Try again."
      toast.error(message)
    } finally {
      setGeneratingStaticExampleByLemma((current) => ({ ...current, [normalizedLemma]: false }))
    }
  }

  async function saveGeneratedExample() {
    if (!generatedExamplePreview) {
      return
    }
    if (generatedExamplePreview.target.kind === "static") {
      await addSentenceToSentencebank(
        generatedExamplePreview.source_text,
        generatedExamplePreview.english_translation,
        { skipPendingView: true },
      )
      return
    }
    await addSentenceToSentencebank(
      generatedExamplePreview.source_text,
      generatedExamplePreview.english_translation,
      {
        tokenPersistenceMode: "link_existing_only",
        target: generatedExamplePreview.target,
        skipPendingView: true,
      },
    )
  }

  function discardGeneratedExample() {
    setGeneratedExamplePreview(null)
  }

  async function regenerateExample() {
    if (!generatedExamplePreview) {
      return
    }
    if (generatedExamplePreview.target.kind === "static") {
      await generateStaticExampleForLemma(generatedExamplePreview.target.stored_lemma)
      return
    }
    await generateExampleForMeaning(generatedExamplePreview.target.stored_lemma, generatedExamplePreview.target.meaning_id)
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

  async function saveSentenceTokenToWordbank(sentenceId: number, token: SentenceTokenCard): Promise<void> {
    try {
      const payload = await apiClient.postJson<SaveSentenceTokenResponse>(
        `/api/sentencebank/sentences/${sentenceId}/tokens/${token.token_index}/save`,
        {},
        "Could not save sentence word.",
      )
      toast.success(payload.message)
      const nextSentence: SentencebankSentence = {
        id: payload.id,
        source_text: payload.source_text,
        english_translation: payload.english_translation,
        created_at: payload.created_at,
        has_pronunciation: payload.has_pronunciation ?? false,
        tokens: payload.tokens ?? [],
      }
      setSentences((current) => current.map((sentence) => (
        sentence.id === payload.id ? nextSentence : sentence
      )))
      setWordbankRefreshTick((current) => current + 1)
      const saved = payload.saved_token
      if (saved.stored_lemma) {
        trackQueuedPronunciationForms(saved.stored_lemma, [
          saved.stored_lemma,
          saved.surface_form,
        ])
        openWordbankTarget(saved.stored_lemma, saved.meaning_id ?? null)
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not save sentence word. Try again."
      toast.error(message)
    }
  }

  return {
    isSavingSentence,
    generatedExamplePreview,
    generatingExampleByMeaningId,
    generatingStaticExampleByLemma,
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
    saveSentenceTokenToWordbank,
    addSentenceToSentencebank,
    generateExampleForMeaning,
    generateStaticExampleForLemma,
    saveGeneratedExample,
    discardGeneratedExample,
    regenerateExample,
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
