import { useEffect, useMemo, useRef, useState } from "react"

import {
  type AppSection,
  createApiClient,
  hasQueuedVerificationTargets,
  normalizeSearchWord,
  type LemmaDetailsResponse,
  type LemmaListResponse,
  type SentenceListResponse,
  type SentencebankSentence,
  type WordbankLemma,
} from "@/app/core"
import { isPinnedPageSentinel } from "@/app/sections/wordbank/_shared/pinned-pages-registry"

const PRONUNCIATION_POLL_WINDOW_MS = 15_000

type UseLexiconDataParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
  activeSection: AppSection
  selectedLemma: string | null
  selectedMeaningId: number | null
  wordbankRefreshTick: number
  sentencebankRefreshTick: number
}

export function useLexiconData({
  backendUrl,
  extractErrorMessage,
  activeSection,
  selectedLemma,
  selectedMeaningId,
  wordbankRefreshTick,
  sentencebankRefreshTick,
}: UseLexiconDataParams) {
  const [lemmas, setLemmas] = useState<WordbankLemma[]>([])
  const [sentences, setSentences] = useState<SentencebankSentence[]>([])
  const [wordbankError, setWordbankError] = useState<string | null>(null)
  const [sentencebankError, setSentencebankError] = useState<string | null>(null)
  const [isWordbankLoading, setIsWordbankLoading] = useState(false)
  const [isSentencebankLoading, setIsSentencebankLoading] = useState(false)
  const [lemmaDetails, setLemmaDetails] = useState<LemmaDetailsResponse | null>(null)
  const [lemmaDetailsError, setLemmaDetailsError] = useState<string | null>(null)
  const [isLemmaDetailsLoading, setIsLemmaDetailsLoading] = useState(false)
  const [showLemmaDetailsLoadingSkeleton, setShowLemmaDetailsLoadingSkeleton] = useState(false)
  const [hasLoadedWordbank, setHasLoadedWordbank] = useState(false)
  const [lemmaDetailsPollTick, setLemmaDetailsPollTick] = useState(0)
  const [pendingPronunciationFormsByLemma, setPendingPronunciationFormsByLemma] = useState<
    Record<string, { forms: string[]; expiresAt: number }>
  >({})

  const lemmaDetailsLoadingDelayTimeoutRef = useRef<number | null>(null)
  const lastLoadedWordbankTickRef = useRef<number | null>(null)
  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )
  const normalizedSelectedLemma = normalizeSearchWord(selectedLemma ?? "")
  const normalizedLoadedLemma = normalizeSearchWord(lemmaDetails?.lemma ?? "")
  const selectedBuiltInReference = isPinnedPageSentinel(selectedLemma)

  useEffect(() => {
    const shouldLoadWordbank = activeSection === "wordbank" || Boolean(selectedLemma) || hasLoadedWordbank
    const alreadyLoadedCurrentTick =
      hasLoadedWordbank && lastLoadedWordbankTickRef.current === wordbankRefreshTick
    if (!shouldLoadWordbank || alreadyLoadedCurrentTick) {
      setIsWordbankLoading(false)
      return
    }

    let cancelled = false
    setIsWordbankLoading(true)
    setWordbankError(null)

    void (async () => {
      try {
        const payload = await apiClient.getJson<LemmaListResponse>(
          "/api/wordbank/lemmas",
          "Could not load wordbank.",
        )
        if (!cancelled) {
          setLemmas(payload.items ?? [])
          setHasLoadedWordbank(true)
          lastLoadedWordbankTickRef.current = wordbankRefreshTick
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Could not load wordbank."
          setWordbankError(message)
          setLemmas([])
        }
      } finally {
        if (!cancelled) {
          setIsWordbankLoading(false)
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [activeSection, apiClient, hasLoadedWordbank, selectedLemma, wordbankRefreshTick])

  useEffect(() => {
    let cancelled = false
    setIsSentencebankLoading(true)
    setSentencebankError(null)

    void (async () => {
      try {
        const payload = await apiClient.getJson<SentenceListResponse>(
          "/api/sentencebank/sentences",
          "Could not load sentencebank.",
        )
        if (!cancelled) {
          setSentences(payload.items ?? [])
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Could not load sentencebank."
          setSentencebankError(message)
          setSentences([])
        }
      } finally {
        if (!cancelled) {
          setIsSentencebankLoading(false)
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [apiClient, sentencebankRefreshTick])

  useEffect(() => {
    if (activeSection !== "wordbank" || !selectedLemma || selectedBuiltInReference) {
      if (lemmaDetailsLoadingDelayTimeoutRef.current !== null) {
        window.clearTimeout(lemmaDetailsLoadingDelayTimeoutRef.current)
        lemmaDetailsLoadingDelayTimeoutRef.current = null
      }
      setLemmaDetails(null)
      setLemmaDetailsError(null)
      setIsLemmaDetailsLoading(false)
      setShowLemmaDetailsLoadingSkeleton(false)
      return
    }

    if (normalizedLoadedLemma && normalizedLoadedLemma !== normalizedSelectedLemma) {
      setLemmaDetails(null)
    }

    let cancelled = false
    setIsLemmaDetailsLoading(true)
    setLemmaDetailsError(null)
    setShowLemmaDetailsLoadingSkeleton(false)
    lemmaDetailsLoadingDelayTimeoutRef.current = window.setTimeout(() => {
      if (!cancelled) {
        setShowLemmaDetailsLoadingSkeleton(true)
      }
    }, 180)

    void (async () => {
      try {
        const payload = await apiClient.getJson<LemmaDetailsResponse>(
          `/api/wordbank/lemmas/${encodeURIComponent(selectedLemma)}`,
          "Could not load lemma details.",
        )
        if (!cancelled) {
          setLemmaDetails(payload)
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Could not load lemma details."
          setLemmaDetailsError(message)
        }
      } finally {
        if (lemmaDetailsLoadingDelayTimeoutRef.current !== null) {
          window.clearTimeout(lemmaDetailsLoadingDelayTimeoutRef.current)
          lemmaDetailsLoadingDelayTimeoutRef.current = null
        }
        if (!cancelled) {
          setIsLemmaDetailsLoading(false)
          setShowLemmaDetailsLoadingSkeleton(false)
        }
      }
    })()

    return () => {
      cancelled = true
      if (lemmaDetailsLoadingDelayTimeoutRef.current !== null) {
        window.clearTimeout(lemmaDetailsLoadingDelayTimeoutRef.current)
        lemmaDetailsLoadingDelayTimeoutRef.current = null
      }
    }
  }, [
    activeSection,
    apiClient,
    lemmaDetailsPollTick,
    normalizedLoadedLemma,
    normalizedSelectedLemma,
    selectedLemma,
    selectedBuiltInReference,
    wordbankRefreshTick,
  ])

  useEffect(() => {
    if (!normalizedSelectedLemma) {
      return
    }
    const tracking = pendingPronunciationFormsByLemma[normalizedSelectedLemma]
    if (!tracking) {
      return
    }
    const hasExpired = tracking.expiresAt <= Date.now()
    const isSatisfied = lemmaDetails !== null && tracking.forms.every((form) => lemmaDetailsHasPronunciation(lemmaDetails, form))
    if (!hasExpired && !isSatisfied) {
      return
    }
    setPendingPronunciationFormsByLemma((current) => {
      if (!(normalizedSelectedLemma in current)) {
        return current
      }
      const next = { ...current }
      delete next[normalizedSelectedLemma]
      return next
    })
  }, [lemmaDetails, normalizedSelectedLemma, pendingPronunciationFormsByLemma])

  useEffect(() => {
    if (activeSection !== "wordbank" || !selectedLemma) {
      return
    }
    const activePronunciationTracking = normalizedSelectedLemma
      ? pendingPronunciationFormsByLemma[normalizedSelectedLemma]
      : undefined
    const shouldPollPronunciations = Boolean(
      activePronunciationTracking
      && activePronunciationTracking.expiresAt > Date.now()
      && (
        lemmaDetails === null
        || activePronunciationTracking.forms.some((form) => !lemmaDetailsHasPronunciation(lemmaDetails, form))
      ),
    )
    if (!hasQueuedVerificationTargets(lemmaDetails) && !shouldPollPronunciations && !hasQueuedRelatedWords(lemmaDetails)) {
      return
    }
    const timeoutId = window.setTimeout(() => {
      setLemmaDetailsPollTick((current) => current + 1)
    }, 1_500)
    return () => {
      window.clearTimeout(timeoutId)
    }
  }, [activeSection, lemmaDetails, normalizedSelectedLemma, pendingPronunciationFormsByLemma, selectedLemma, selectedMeaningId])

  function trackQueuedPronunciationForms(lemma: string, forms: string[]) {
    const normalizedLemma = normalizeSearchWord(lemma)
    const normalizedForms = normalizeQueuedPronunciationForms(forms)
    if (!normalizedLemma || normalizedForms.length === 0) {
      return
    }
    setPendingPronunciationFormsByLemma((current) => {
      const existing = current[normalizedLemma]
      return {
        ...current,
        [normalizedLemma]: {
          forms: normalizeQueuedPronunciationForms([
            ...(existing?.forms ?? []),
            ...normalizedForms,
          ]),
          expiresAt: Date.now() + PRONUNCIATION_POLL_WINDOW_MS,
        },
      }
    })
  }

  return {
    lemmas,
    setLemmas,
    sentences,
    setSentences,
    wordbankError,
    setWordbankError,
    sentencebankError,
    setSentencebankError,
    isWordbankLoading,
    isSentencebankLoading,
    lemmaDetails,
    setLemmaDetails,
    lemmaDetailsError,
    setLemmaDetailsError,
    isLemmaDetailsLoading,
    setIsLemmaDetailsLoading,
    showLemmaDetailsLoadingSkeleton,
    setShowLemmaDetailsLoadingSkeleton,
    trackQueuedPronunciationForms,
  }
}

function hasQueuedRelatedWords(lemmaDetails: LemmaDetailsResponse | null): boolean {
  return lemmaDetails?.related_words?.status === "queued"
}

function normalizeQueuedPronunciationForms(forms: string[]): string[] {
  const ordered: string[] = []
  const seen = new Set<string>()
  for (const form of forms) {
    const normalizedForm = normalizeSearchWord(form)
    if (!normalizedForm || seen.has(normalizedForm)) {
      continue
    }
    seen.add(normalizedForm)
    ordered.push(normalizedForm)
  }
  return ordered
}

function lemmaDetailsHasPronunciation(lemmaDetails: LemmaDetailsResponse, form: string): boolean {
  const normalizedTarget = normalizeSearchWord(form)
  if (!normalizedTarget) {
    return false
  }
  const candidates = [
    ...(lemmaDetails.surface_forms ?? []),
    ...((lemmaDetails.meaning_sections ?? []).flatMap((section) => section.surface_forms ?? [])),
  ]
  return candidates.some((candidate) => {
    const normalizedForm = normalizeSearchWord(candidate.form)
    return normalizedForm === normalizedTarget && Boolean(candidate.has_pronunciation)
  })
}
