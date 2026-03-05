import { useState } from "react"

import { type AppSection } from "@/app/core"

export function useSectionNavigation() {
  const [activeSection, setActiveSection] = useState<AppSection>("playground")
  const [selectedLemma, setSelectedLemma] = useState<string | null>(null)

  return {
    activeSection,
    selectedLemma,
    setActiveSection,
    setSelectedLemma,
    selectPlayground: () => {
      setActiveSection("playground")
    },
    selectNotes: () => {
      setActiveSection("notes")
      setSelectedLemma(null)
    },
    selectWordbank: () => {
      setActiveSection("wordbank")
      setSelectedLemma(null)
    },
    selectSentencebank: () => {
      setActiveSection("sentencebank")
      setSelectedLemma(null)
    },
    selectDeveloper: () => {
      setActiveSection("developer")
      setSelectedLemma(null)
    },
    openWordbankLemma: (lemma: string) => {
      setActiveSection("wordbank")
      setSelectedLemma(lemma)
    },
    openWordbankRoot: () => {
      setActiveSection("wordbank")
      setSelectedLemma(null)
    },
  }
}
