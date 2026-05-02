import { useState } from "react"

import { type AppSection } from "@/app/core"

export type PendingSentence = {
  source_text: string
  english_translation: string | null
}

export function useSectionNavigation() {
  const [activeSection, setActiveSection] = useState<AppSection>("wordbank")
  const [selectedLemma, setSelectedLemma] = useState<string | null>(null)
  const [selectedMeaningId, setSelectedMeaningId] = useState<number | null>(null)
  const [selectedSentenceId, setSelectedSentenceId] = useState<number | null>(null)
  const [pendingSentence, setPendingSentence] = useState<PendingSentence | null>(null)

  return {
    activeSection,
    selectedLemma,
    selectedMeaningId,
    selectedSentenceId,
    pendingSentence,
    setActiveSection,
    setSelectedLemma,
    setSelectedMeaningId,
    setSelectedSentenceId,
    selectNotes: () => {
      setActiveSection("notes")
      setSelectedLemma(null)
      setSelectedMeaningId(null)
      setSelectedSentenceId(null)
    },
    selectWordbank: () => {
      setActiveSection("wordbank")
      setSelectedLemma(null)
      setSelectedMeaningId(null)
      setSelectedSentenceId(null)
    },
    selectSentencebank: () => {
      setActiveSection("sentencebank")
      setSelectedLemma(null)
      setSelectedMeaningId(null)
      setSelectedSentenceId(null)
    },
    selectDeveloper: () => {
      setActiveSection("developer")
      setSelectedLemma(null)
      setSelectedMeaningId(null)
      setSelectedSentenceId(null)
    },
    openWordbankLemma: (lemma: string) => {
      setActiveSection("wordbank")
      setSelectedLemma(lemma)
      setSelectedMeaningId(null)
      setSelectedSentenceId(null)
    },
    openWordbankMeaning: (lemma: string, meaningId: number) => {
      setActiveSection("wordbank")
      setSelectedLemma(lemma)
      setSelectedMeaningId(meaningId)
      setSelectedSentenceId(null)
    },
    openWordbankRoot: () => {
      setActiveSection("wordbank")
      setSelectedLemma(null)
      setSelectedMeaningId(null)
      setSelectedSentenceId(null)
    },
    openPendingSentence: (sourceText: string, englishTranslation: string | null = null) => {
      setActiveSection("sentencebank")
      setPendingSentence({ source_text: sourceText, english_translation: englishTranslation })
      setSelectedSentenceId(null)
      setSelectedLemma(null)
      setSelectedMeaningId(null)
    },
    openSentence: (id: number) => {
      setActiveSection("sentencebank")
      setSelectedSentenceId(id)
      setPendingSentence(null)
      setSelectedLemma(null)
      setSelectedMeaningId(null)
    },
  }
}
