import { useState } from "react"

import { type AppSection } from "@/app/core"

export function useSectionNavigation() {
  const [activeSection, setActiveSection] = useState<AppSection>("playground")
  const [selectedLemma, setSelectedLemma] = useState<string | null>(null)
  const [selectedMeaningId, setSelectedMeaningId] = useState<number | null>(null)
  const [selectedSentenceId, setSelectedSentenceId] = useState<number | null>(null)

  return {
    activeSection,
    selectedLemma,
    selectedMeaningId,
    selectedSentenceId,
    setActiveSection,
    setSelectedLemma,
    setSelectedMeaningId,
    setSelectedSentenceId,
    selectPlayground: () => {
      setActiveSection("playground")
      setSelectedMeaningId(null)
      setSelectedSentenceId(null)
    },
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
    openSentence: (id: number) => {
      setActiveSection("sentencebank")
      setSelectedSentenceId(id)
      setSelectedLemma(null)
      setSelectedMeaningId(null)
    },
  }
}
