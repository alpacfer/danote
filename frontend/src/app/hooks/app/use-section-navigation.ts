import { useState } from "react"

import { type AppSection } from "@/app/core"

export function useSectionNavigation() {
  const [activeSection, setActiveSection] = useState<AppSection>("playground")
  const [selectedLemma, setSelectedLemma] = useState<string | null>(null)
  const [selectedMeaningId, setSelectedMeaningId] = useState<number | null>(null)

  return {
    activeSection,
    selectedLemma,
    selectedMeaningId,
    setActiveSection,
    setSelectedLemma,
    setSelectedMeaningId,
    selectPlayground: () => {
      setActiveSection("playground")
      setSelectedMeaningId(null)
    },
    selectNotes: () => {
      setActiveSection("notes")
      setSelectedLemma(null)
      setSelectedMeaningId(null)
    },
    selectWordbank: () => {
      setActiveSection("wordbank")
      setSelectedLemma(null)
      setSelectedMeaningId(null)
    },
    selectSentencebank: () => {
      setActiveSection("sentencebank")
      setSelectedLemma(null)
      setSelectedMeaningId(null)
    },
    selectDeveloper: () => {
      setActiveSection("developer")
      setSelectedLemma(null)
      setSelectedMeaningId(null)
    },
    openWordbankLemma: (lemma: string) => {
      setActiveSection("wordbank")
      setSelectedLemma(lemma)
      setSelectedMeaningId(null)
    },
    openWordbankMeaning: (lemma: string, meaningId: number) => {
      setActiveSection("wordbank")
      setSelectedLemma(lemma)
      setSelectedMeaningId(meaningId)
    },
    openWordbankRoot: () => {
      setActiveSection("wordbank")
      setSelectedLemma(null)
      setSelectedMeaningId(null)
    },
  }
}
