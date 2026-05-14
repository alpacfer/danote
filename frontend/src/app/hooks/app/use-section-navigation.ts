import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react"

import { type AppSection } from "@/app/core"
import { CONJUNCTION_LEMMAS, CONJUNCTIONS_SENTINEL } from "@/app/sections/wordbank/conjunctions/conjunctions-data"
import { CALENDAR_LEMMAS, DAYS_MONTHS_SEASONS_SENTINEL } from "@/app/sections/wordbank/days-months-seasons/days-months-seasons-data"
import { PREPOSITION_LEMMAS, PREPOSITIONS_SENTINEL } from "@/app/sections/wordbank/prepositions/prepositions-data"
import { getPronounCategory, PRONOUN_SENTINELS } from "@/app/sections/wordbank/pronouns/pronouns-data"
import { getQuestionWordEntry, QUESTION_WORDS_SENTINEL } from "@/app/sections/wordbank/question-words/question-words-data"

export type PendingSentence = {
  source_text: string
  english_translation: string | null
}

export type NavEntry = {
  section: AppSection
  selectedLemma: string | null
  selectedMeaningId: number | null
  selectedSentenceId: number | null
  pendingSentence: PendingSentence | null
}

const ROOT_ENTRY: NavEntry = {
  section: "wordbank",
  selectedLemma: null,
  selectedMeaningId: null,
  selectedSentenceId: null,
  pendingSentence: null,
}

const APP_HISTORY_KEY = "danote.nav"

function entriesEqual(a: NavEntry, b: NavEntry): boolean {
  return (
    a.section === b.section
    && a.selectedLemma === b.selectedLemma
    && a.selectedMeaningId === b.selectedMeaningId
    && a.selectedSentenceId === b.selectedSentenceId
    && a.pendingSentence?.source_text === b.pendingSentence?.source_text
    && a.pendingSentence?.english_translation === b.pendingSentence?.english_translation
  )
}

function builtinAwareLemma(lemma: string | null): string | null {
  if (!lemma) return null
  const normalized = lemma.toLowerCase()
  if (getQuestionWordEntry(normalized)) return QUESTION_WORDS_SENTINEL
  const category = getPronounCategory(normalized)
  if (category) return PRONOUN_SENTINELS[category]
  if (PREPOSITION_LEMMAS.has(normalized)) return PREPOSITIONS_SENTINEL
  if (CONJUNCTION_LEMMAS.has(normalized)) return CONJUNCTIONS_SENTINEL
  if (CALENDAR_LEMMAS.has(normalized)) return DAYS_MONTHS_SEASONS_SENTINEL
  return lemma
}

type HistoryState = { entries: NavEntry[]; index: number }

function readBrowserNavIndex(): number | null {
  if (typeof window === "undefined") return null
  const raw = window.history.state as Record<string, unknown> | null
  const navState = raw && typeof raw === "object" ? (raw as Record<string, unknown>)[APP_HISTORY_KEY] : null
  if (!navState || typeof navState !== "object") return null
  const index = (navState as { index?: unknown }).index
  return typeof index === "number" ? index : null
}

function writeBrowserNavIndex(method: "push" | "replace", index: number) {
  if (typeof window === "undefined") return
  const existing = (window.history.state as Record<string, unknown> | null) ?? {}
  const next = { ...existing, [APP_HISTORY_KEY]: { index } }
  if (method === "push") window.history.pushState(next, "")
  else window.history.replaceState(next, "")
}

export function useSectionNavigation() {
  const [history, setHistory] = useState<HistoryState>(() => ({ entries: [ROOT_ENTRY], index: 0 }))
  const historyRef = useRef(history)

  useLayoutEffect(() => {
    historyRef.current = history
  }, [history])

  useEffect(() => {
    writeBrowserNavIndex("replace", 0)
  }, [])

  useEffect(() => {
    function onPopState() {
      const navIndex = readBrowserNavIndex()
      if (navIndex == null) return
      const cur = historyRef.current
      if (cur.index === navIndex) return
      if (navIndex < 0 || navIndex >= cur.entries.length) return
      const next = { ...cur, index: navIndex }
      historyRef.current = next
      setHistory(next)
    }
    window.addEventListener("popstate", onPopState)
    return () => window.removeEventListener("popstate", onPopState)
  }, [])

  const applyPush = useCallback((entry: NavEntry) => {
    const cur = historyRef.current
    const currentEntry = cur.entries[cur.index] ?? ROOT_ENTRY
    if (entriesEqual(currentEntry, entry)) return
    const truncated = cur.entries.slice(0, cur.index + 1)
    const newIndex = truncated.length
    const next: HistoryState = { entries: [...truncated, entry], index: newIndex }
    historyRef.current = next
    setHistory(next)
    writeBrowserNavIndex("push", newIndex)
  }, [])

  const current = history.entries[history.index] ?? ROOT_ENTRY
  const previousEntry = history.index > 0 ? history.entries[history.index - 1] : null
  const nextEntry = history.index < history.entries.length - 1 ? history.entries[history.index + 1] : null

  const goBack = useCallback(() => {
    const cur = historyRef.current
    if (cur.index <= 0) return
    const newIndex = cur.index - 1
    const next: HistoryState = { ...cur, index: newIndex }
    historyRef.current = next
    setHistory(next)
    if (typeof window !== "undefined") window.history.back()
  }, [])

  const goForward = useCallback(() => {
    const cur = historyRef.current
    if (cur.index >= cur.entries.length - 1) return
    const newIndex = cur.index + 1
    const next: HistoryState = { ...cur, index: newIndex }
    historyRef.current = next
    setHistory(next)
    if (typeof window !== "undefined") window.history.forward()
  }, [])

  const setActiveSection = useCallback((section: AppSection) => {
    applyPush({ ...ROOT_ENTRY, section })
  }, [applyPush])

  const setSelectedLemma = useCallback((lemma: string | null) => {
    applyPush({
      section: "wordbank",
      selectedLemma: builtinAwareLemma(lemma),
      selectedMeaningId: null,
      selectedSentenceId: null,
      pendingSentence: null,
    })
  }, [applyPush])

  const setSelectedMeaningId = useCallback((meaningId: number | null) => {
    const cur = historyRef.current.entries[historyRef.current.index] ?? ROOT_ENTRY
    applyPush({
      section: "wordbank",
      selectedLemma: cur.selectedLemma,
      selectedMeaningId: meaningId,
      selectedSentenceId: null,
      pendingSentence: null,
    })
  }, [applyPush])

  const setSelectedSentenceId = useCallback((id: number | null) => {
    applyPush({
      section: "sentencebank",
      selectedLemma: null,
      selectedMeaningId: null,
      selectedSentenceId: id,
      pendingSentence: null,
    })
  }, [applyPush])

  const selectWordbank = useCallback(() => {
    applyPush({ ...ROOT_ENTRY, section: "wordbank" })
  }, [applyPush])

  const selectSentencebank = useCallback(() => {
    applyPush({ ...ROOT_ENTRY, section: "sentencebank" })
  }, [applyPush])

  const selectDeveloper = useCallback(() => {
    applyPush({ ...ROOT_ENTRY, section: "developer" })
  }, [applyPush])

  const selectAccount = useCallback(() => {
    applyPush({ ...ROOT_ENTRY, section: "account" })
  }, [applyPush])

  const openWordbankLemma = useCallback((lemma: string) => {
    applyPush({
      section: "wordbank",
      selectedLemma: builtinAwareLemma(lemma),
      selectedMeaningId: null,
      selectedSentenceId: null,
      pendingSentence: null,
    })
  }, [applyPush])

  const openWordbankLemmaRaw = useCallback((lemma: string) => {
    applyPush({
      section: "wordbank",
      selectedLemma: lemma,
      selectedMeaningId: null,
      selectedSentenceId: null,
      pendingSentence: null,
    })
  }, [applyPush])

  const openWordbankPinnedTab = useCallback((sentinel: string) => {
    applyPush({
      section: "wordbank",
      selectedLemma: sentinel,
      selectedMeaningId: null,
      selectedSentenceId: null,
      pendingSentence: null,
    })
  }, [applyPush])

  const openWordbankMeaning = useCallback((lemma: string, meaningId: number) => {
    const nextLemma = builtinAwareLemma(lemma)
    applyPush({
      section: "wordbank",
      selectedLemma: nextLemma,
      selectedMeaningId: nextLemma === lemma ? meaningId : null,
      selectedSentenceId: null,
      pendingSentence: null,
    })
  }, [applyPush])

  const openWordbankMeaningRaw = useCallback((lemma: string, meaningId: number) => {
    applyPush({
      section: "wordbank",
      selectedLemma: lemma,
      selectedMeaningId: meaningId,
      selectedSentenceId: null,
      pendingSentence: null,
    })
  }, [applyPush])

  const openWordbankTarget = useCallback((lemma: string, meaningId: number | null) => {
    applyPush({
      section: "wordbank",
      selectedLemma: lemma,
      selectedMeaningId: meaningId,
      selectedSentenceId: null,
      pendingSentence: null,
    })
  }, [applyPush])

  const openWordbankRoot = useCallback(() => {
    applyPush({ ...ROOT_ENTRY, section: "wordbank" })
  }, [applyPush])

  const openPendingSentence = useCallback(
    (sourceText: string, englishTranslation: string | null = null) => {
      applyPush({
        section: "sentencebank",
        selectedLemma: null,
        selectedMeaningId: null,
        selectedSentenceId: null,
        pendingSentence: { source_text: sourceText, english_translation: englishTranslation },
      })
    },
    [applyPush],
  )

  const openSentence = useCallback((id: number) => {
    applyPush({
      section: "sentencebank",
      selectedLemma: null,
      selectedMeaningId: null,
      selectedSentenceId: id,
      pendingSentence: null,
    })
  }, [applyPush])

  const replaceCurrentSentence = useCallback((id: number) => {
    const cur = historyRef.current
    const next: NavEntry = {
      section: "sentencebank",
      selectedLemma: null,
      selectedMeaningId: null,
      selectedSentenceId: id,
      pendingSentence: null,
    }
    const entries = [...cur.entries]
    entries[cur.index] = next
    const nextState: HistoryState = { entries, index: cur.index }
    historyRef.current = nextState
    setHistory(nextState)
  }, [])

  return useMemo(() => ({
    activeSection: current.section,
    selectedLemma: current.selectedLemma,
    selectedMeaningId: current.selectedMeaningId,
    selectedSentenceId: current.selectedSentenceId,
    pendingSentence: current.pendingSentence,
    canGoBack: history.index > 0,
    canGoForward: history.index < history.entries.length - 1,
    previousEntry,
    nextEntry,
    currentEntry: current,
    goBack,
    goForward,
    setActiveSection,
    setSelectedLemma,
    setSelectedMeaningId,
    setSelectedSentenceId,
    selectWordbank,
    selectSentencebank,
    selectDeveloper,
    selectAccount,
    openWordbankLemma,
    openWordbankLemmaRaw,
    openWordbankPinnedTab,
    openWordbankMeaning,
    openWordbankMeaningRaw,
    openWordbankTarget,
    openWordbankRoot,
    openPendingSentence,
    openSentence,
    replaceCurrentSentence,
  }), [
    current,
    history.index,
    history.entries.length,
    previousEntry,
    nextEntry,
    goBack,
    goForward,
    setActiveSection,
    setSelectedLemma,
    setSelectedMeaningId,
    setSelectedSentenceId,
    selectWordbank,
    selectSentencebank,
    selectDeveloper,
    selectAccount,
    openWordbankLemma,
    openWordbankLemmaRaw,
    openWordbankPinnedTab,
    openWordbankMeaning,
    openWordbankMeaningRaw,
    openWordbankTarget,
    openWordbankRoot,
    openPendingSentence,
    openSentence,
    replaceCurrentSentence,
  ])
}
