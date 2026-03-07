import { useEffect, useMemo, useRef, useState } from "react"

import {
  type AppSection,
  createApiClient,
  type LemmaDetailsResponse,
  type LemmaListResponse,
  type SentenceListResponse,
  type SentencebankSentence,
  type WordbankLemma,
} from "@/app/core"

type UseLexiconDataParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
  activeSection: AppSection
  selectedLemma: string | null
  wordbankRefreshTick: number
  sentencebankRefreshTick: number
}

export function useLexiconData({
  backendUrl,
  extractErrorMessage,
  activeSection,
  selectedLemma,
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

  const lemmaDetailsLoadingDelayTimeoutRef = useRef<number | null>(null)
  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )

  useEffect(() => {
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
  }, [apiClient, wordbankRefreshTick])

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
    if (activeSection !== "wordbank" || !selectedLemma) {
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
          setLemmaDetails(null)
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
  }, [activeSection, apiClient, selectedLemma, wordbankRefreshTick])

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
  }
}
