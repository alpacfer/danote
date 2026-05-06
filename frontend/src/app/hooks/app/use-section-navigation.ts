import { useCallback, useMemo, useState } from "react"

import { type AppSection } from "@/app/core"
import { getHvQuestionEntry, HV_QUESTION_SENTINEL } from "@/app/sections/wordbank/hv-questions/hv-question-data"
import { getPronounCategory, PRONOUN_SENTINELS } from "@/app/sections/wordbank/pronouns/pronouns-data"

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
  if (getHvQuestionEntry(lemma)) return HV_QUESTION_SENTINEL
  const category = getPronounCategory(lemma)
  return category ? PRONOUN_SENTINELS[category] : lemma
}

type HistoryState = { entries: NavEntry[]; index: number }

function pushEntry(prev: HistoryState, next: NavEntry): HistoryState {
  const currentEntry = prev.entries[prev.index] ?? ROOT_ENTRY
  if (entriesEqual(currentEntry, next)) return prev
  const truncated = prev.entries.slice(0, prev.index + 1)
  return { entries: [...truncated, next], index: truncated.length }
}

export function useSectionNavigation() {
  const [history, setHistory] = useState<HistoryState>(() => ({ entries: [ROOT_ENTRY], index: 0 }))

  const current = history.entries[history.index] ?? ROOT_ENTRY
  const previousEntry = history.index > 0 ? history.entries[history.index - 1] : null
  const nextEntry = history.index < history.entries.length - 1 ? history.entries[history.index + 1] : null

  const goBack = useCallback(() => {
    setHistory(prev => (prev.index > 0 ? { ...prev, index: prev.index - 1 } : prev))
  }, [])

  const goForward = useCallback(() => {
    setHistory(prev => (prev.index < prev.entries.length - 1 ? { ...prev, index: prev.index + 1 } : prev))
  }, [])

  const setActiveSection = useCallback((section: AppSection) => {
    setHistory(prev => pushEntry(prev, { ...ROOT_ENTRY, section }))
  }, [])

  const setSelectedLemma = useCallback((lemma: string | null) => {
    const resolved = builtinAwareLemma(lemma)
    setHistory(prev => pushEntry(prev, {
      section: "wordbank",
      selectedLemma: resolved,
      selectedMeaningId: null,
      selectedSentenceId: null,
      pendingSentence: null,
    }))
  }, [])

  const setSelectedMeaningId = useCallback((meaningId: number | null) => {
    setHistory(prev => {
      const cur = prev.entries[prev.index] ?? ROOT_ENTRY
      return pushEntry(prev, {
        section: "wordbank",
        selectedLemma: cur.selectedLemma,
        selectedMeaningId: meaningId,
        selectedSentenceId: null,
        pendingSentence: null,
      })
    })
  }, [])

  const setSelectedSentenceId = useCallback((id: number | null) => {
    setHistory(prev => pushEntry(prev, {
      section: "sentencebank",
      selectedLemma: null,
      selectedMeaningId: null,
      selectedSentenceId: id,
      pendingSentence: null,
    }))
  }, [])

  const selectWordbank = useCallback(() => {
    setHistory(prev => pushEntry(prev, { ...ROOT_ENTRY, section: "wordbank" }))
  }, [])

  const selectSentencebank = useCallback(() => {
    setHistory(prev => pushEntry(prev, { ...ROOT_ENTRY, section: "sentencebank" }))
  }, [])

  const selectDeveloper = useCallback(() => {
    setHistory(prev => pushEntry(prev, { ...ROOT_ENTRY, section: "developer" }))
  }, [])

  const openWordbankLemma = useCallback((lemma: string) => {
    setHistory(prev => pushEntry(prev, {
      section: "wordbank",
      selectedLemma: builtinAwareLemma(lemma),
      selectedMeaningId: null,
      selectedSentenceId: null,
      pendingSentence: null,
    }))
  }, [])

  const openWordbankMeaning = useCallback((lemma: string, meaningId: number) => {
    const nextLemma = builtinAwareLemma(lemma)
    setHistory(prev => pushEntry(prev, {
      section: "wordbank",
      selectedLemma: nextLemma,
      selectedMeaningId: nextLemma === lemma ? meaningId : null,
      selectedSentenceId: null,
      pendingSentence: null,
    }))
  }, [])

  const openWordbankTarget = useCallback((lemma: string, meaningId: number | null) => {
    const nextLemma = builtinAwareLemma(lemma)
    setHistory(prev => pushEntry(prev, {
      section: "wordbank",
      selectedLemma: nextLemma,
      selectedMeaningId: nextLemma === lemma ? meaningId : null,
      selectedSentenceId: null,
      pendingSentence: null,
    }))
  }, [])

  const openWordbankRoot = useCallback(() => {
    setHistory(prev => pushEntry(prev, { ...ROOT_ENTRY, section: "wordbank" }))
  }, [])

  const openPendingSentence = useCallback(
    (sourceText: string, englishTranslation: string | null = null) => {
      setHistory(prev => pushEntry(prev, {
        section: "sentencebank",
        selectedLemma: null,
        selectedMeaningId: null,
        selectedSentenceId: null,
        pendingSentence: { source_text: sourceText, english_translation: englishTranslation },
      }))
    },
    [],
  )

  const openSentence = useCallback((id: number) => {
    setHistory(prev => pushEntry(prev, {
      section: "sentencebank",
      selectedLemma: null,
      selectedMeaningId: null,
      selectedSentenceId: id,
      pendingSentence: null,
    }))
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
    openWordbankLemma,
    openWordbankMeaning,
    openWordbankTarget,
    openWordbankRoot,
    openPendingSentence,
    openSentence,
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
    openWordbankLemma,
    openWordbankMeaning,
    openWordbankTarget,
    openWordbankRoot,
    openPendingSentence,
    openSentence,
  ])
}
