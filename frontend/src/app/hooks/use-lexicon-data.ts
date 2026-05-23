import { useEffect, useMemo, useRef, useState } from "react"

import {
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

import {
  hasQueuedRelatedWords,
  lemmaDetailsHasPronunciation,
  mergeQueuedPronunciationTracking,
  normalizeQueuedPronunciationForms,
  type PendingPronunciationFormsByLemma,
  shouldPollPronunciations,
  type UseLexiconDataParams,
} from "./use-lexicon-data-helpers"

const PRONUNCIATION_POLL_WINDOW_MS = 15_000

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
  const [wordbankAutoRefreshTick, setWordbankAutoRefreshTick] = useState(0)
  const [pendingPronunciationFormsByLemma, setPendingPronunciationFormsByLemma] =
    useState<PendingPronunciationFormsByLemma>({})

  const lemmaDetailsLoadingDelayTimeoutRef = useRef<number | null>(null)
  const lastLoadedWordbankTickRef = useRef<string | null>(null)
  const lemmaDetailsRef = useRef<LemmaDetailsResponse | null>(null)
  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )
  const normalizedSelectedLemma = normalizeSearchWord(selectedLemma ?? "")
  const normalizedLoadedLemma = normalizeSearchWord(lemmaDetails?.lemma ?? "")
  const selectedBuiltInReference = isPinnedPageSentinel(selectedLemma)
  const wordbankLoadKey = `${wordbankRefreshTick}:${wordbankAutoRefreshTick}`

  useEffect(() => {
    lemmaDetailsRef.current = lemmaDetails
  }, [lemmaDetails])

  useEffect(() => {
    const shouldLoadWordbank = activeSection === "wordbank" || Boolean(selectedLemma) || hasLoadedWordbank
    const alreadyLoadedCurrentTick =
      hasLoadedWordbank && lastLoadedWordbankTickRef.current === wordbankLoadKey
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
          lastLoadedWordbankTickRef.current = wordbankLoadKey
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
  }, [activeSection, apiClient, hasLoadedWordbank, selectedLemma, wordbankLoadKey])

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
        const previousDetails = lemmaDetailsRef.current
        const hadQueuedVerification = hasQueuedVerificationTargets(previousDetails)
        const payload = await apiClient.getJson<LemmaDetailsResponse>(
          `/api/wordbank/lemmas/${encodeURIComponent(selectedLemma)}`,
          "Could not load lemma details.",
        )
        if (!cancelled) {
          if (hadQueuedVerification && !hasQueuedVerificationTargets(payload)) {
            setWordbankAutoRefreshTick((current) => current + 1)
          }
          lemmaDetailsRef.current = payload
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
    const pollPronunciations = shouldPollPronunciations({
      lemmaDetails,
      normalizedSelectedLemma,
      pendingPronunciationFormsByLemma,
    })
    if (!hasQueuedVerificationTargets(lemmaDetails) && !pollPronunciations && !hasQueuedRelatedWords(lemmaDetails)) {
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
      return mergeQueuedPronunciationTracking(
        current,
        normalizedLemma,
        normalizedForms,
        Date.now() + PRONUNCIATION_POLL_WINDOW_MS,
      )
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
