import { type Dispatch, type SetStateAction, useState } from "react"

import {
  createApiClient,
  hasMultipleWords,
  normalizePhraseKey,
  normalizeSearchWord,
  type AddSentenceResponse,
  type DeleteSentenceResponse,
  type GenerateExamplePreviewResponse,
  type SentencebankSentence,
  type SentenceTokenCard,
  type SaveSentenceTokenResponse,
} from "@/app/core"
import { toast } from "sonner"

type ApiClient = ReturnType<typeof createApiClient>

type GeneratedExamplePreview = {
  source_text: string
  english_translation: string
  target:
    | { kind: "wordbank"; stored_lemma: string; meaning_id: number }
    | { kind: "static"; stored_lemma: string }
}

type UseSentencebankSaveWorkflowParams = {
  apiClient: ApiClient
  sentences: SentencebankSentence[]
  setSentences: Dispatch<SetStateAction<SentencebankSentence[]>>
  setWordbankRefreshTick: Dispatch<SetStateAction<number>>
  setSentencebankRefreshTick: Dispatch<SetStateAction<number>>
  openPendingSentence: (text: string, englishTranslation?: string | null) => void
  openSentence: (id: number) => void
  replaceCurrentSentence: (id: number) => void
  openWordbankTarget: (lemma: string, meaningId: number | null) => void
  trackQueuedPronunciationForms: (lemma: string, forms: string[]) => void
  trackQueuedVerificationTargets: (
    storedLemma: string,
    queuedTargets: Array<{ meaning_id: number | null; stored_surface_form: string | null }>,
  ) => void
  onSentenceSaved?: () => void
}

export function useSentencebankSaveWorkflow({
  apiClient,
  sentences,
  setSentences,
  setWordbankRefreshTick,
  setSentencebankRefreshTick,
  openPendingSentence,
  openSentence,
  replaceCurrentSentence,
  openWordbankTarget,
  trackQueuedPronunciationForms,
  trackQueuedVerificationTargets,
  onSentenceSaved,
}: UseSentencebankSaveWorkflowParams) {
  const [isSavingSentence, setIsSavingSentence] = useState(false)
  const [generatedExamplePreview, setGeneratedExamplePreview] = useState<GeneratedExamplePreview | null>(null)
  const [generatingExampleByMeaningId, setGeneratingExampleByMeaningId] = useState<Record<number, boolean>>({})
  const [generatingStaticExampleByLemma, setGeneratingStaticExampleByLemma] = useState<Record<string, boolean>>({})

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
      trackQueuedSentenceVerificationTargets(payload.queued_verification_targets ?? [], trackQueuedVerificationTargets)
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

  async function saveSentenceTokenToWordbank(sentenceId: number, token: SentenceTokenCard): Promise<void> {
    try {
      const payload = await apiClient.postJson<SaveSentenceTokenResponse>(
        `/api/sentencebank/sentences/${sentenceId}/tokens/${token.token_index}/save`,
        {},
        "Could not save sentence word.",
      )
      toast.success(payload.message)
      trackQueuedSentenceVerificationTargets(payload.queued_verification_targets ?? [], trackQueuedVerificationTargets)
      setSentences((current) => current.map((sentence) => (
        sentence.id === payload.id
          ? {
            id: payload.id,
            source_text: payload.source_text,
            english_translation: payload.english_translation,
            created_at: payload.created_at,
            has_pronunciation: payload.has_pronunciation ?? false,
            tokens: payload.tokens ?? [],
          }
          : sentence
      )))
      setWordbankRefreshTick((current) => current + 1)
      const saved = payload.saved_token
      if (saved.stored_lemma) {
        trackQueuedPronunciationForms(saved.stored_lemma, [saved.stored_lemma, saved.surface_form])
        openWordbankTarget(saved.stored_lemma, saved.meaning_id ?? null)
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not save sentence word. Try again."
      toast.error(message)
    }
  }

  async function deleteSentenceFromSentencebank(sentenceId: number, deleteMeanings: boolean): Promise<void> {
    try {
      const payload = await apiClient.deleteJson<DeleteSentenceResponse>(
        `/api/sentencebank/sentences/${sentenceId}?delete_meanings=${deleteMeanings ? "true" : "false"}`,
        "Could not delete sentence.",
      )
      toast.success(payload.message)
      setSentences((current) => current.filter((sentence) => sentence.id !== sentenceId))
      setSentencebankRefreshTick((current) => current + 1)
      if (deleteMeanings) {
        setWordbankRefreshTick((current) => current + 1)
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not delete sentence. Try again."
      toast.error(message)
    }
  }

  return {
    isSavingSentence,
    generatedExamplePreview,
    generatingExampleByMeaningId,
    generatingStaticExampleByLemma,
    addSentenceToSentencebank,
    generateExampleForMeaning,
    generateStaticExampleForLemma,
    saveGeneratedExample,
    discardGeneratedExample,
    regenerateExample,
    saveSentenceTokenToWordbank,
    deleteSentenceFromSentencebank,
  }
}

function trackQueuedSentenceVerificationTargets(
  targets: NonNullable<AddSentenceResponse["queued_verification_targets"]>,
  trackQueuedVerificationTargets: (
    storedLemma: string,
    queuedTargets: Array<{ meaning_id: number | null; stored_surface_form: string | null }>,
  ) => void,
) {
  const byLemma = new Map<string, Array<{ meaning_id: number | null; stored_surface_form: string | null }>>()
  for (const target of targets) {
    const lemma = normalizeSearchWord(target.stored_lemma)
    if (!lemma) {
      continue
    }
    const items = byLemma.get(lemma) ?? []
    items.push({
      meaning_id: target.meaning_id ?? null,
      stored_surface_form: target.stored_surface_form ?? null,
    })
    byLemma.set(lemma, items)
  }
  for (const [lemma, queuedTargets] of byLemma) {
    trackQueuedVerificationTargets(lemma, queuedTargets)
  }
}
