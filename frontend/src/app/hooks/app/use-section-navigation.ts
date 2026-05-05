import { useState } from "react"

import { type AppSection } from "@/app/core"
import { getHvQuestionEntry, HV_QUESTION_SENTINEL } from "@/app/sections/wordbank/hv-questions/hv-question-data"
import { getPronounCategory, PRONOUN_SENTINELS } from "@/app/sections/wordbank/pronouns/pronouns-data"

export type PendingSentence = {
  source_text: string
  english_translation: string | null
}

export function useSectionNavigation() {
  const [activeSection, setActiveSection] = useState<AppSection>("wordbank")
  const [selectedLemma, setSelectedLemmaState] = useState<string | null>(null)
  const [selectedMeaningId, setSelectedMeaningId] = useState<number | null>(null)
  const [selectedSentenceId, setSelectedSentenceId] = useState<number | null>(null)
  const [pendingSentence, setPendingSentence] = useState<PendingSentence | null>(null)

  function builtinAwareLemma(lemma: string | null): string | null {
    if (!lemma) return null
    if (getHvQuestionEntry(lemma)) return HV_QUESTION_SENTINEL
    const category = getPronounCategory(lemma)
    return category ? PRONOUN_SENTINELS[category] : lemma
  }

  function setSelectedLemma(lemma: string | null) {
    setSelectedLemmaState(builtinAwareLemma(lemma))
  }

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
    selectWordbank: () => {
      setActiveSection("wordbank")
      setSelectedLemmaState(null)
      setSelectedMeaningId(null)
      setSelectedSentenceId(null)
    },
    selectSentencebank: () => {
      setActiveSection("sentencebank")
      setSelectedLemmaState(null)
      setSelectedMeaningId(null)
      setSelectedSentenceId(null)
    },
    selectDeveloper: () => {
      setActiveSection("developer")
      setSelectedLemmaState(null)
      setSelectedMeaningId(null)
      setSelectedSentenceId(null)
    },
    openWordbankLemma: (lemma: string) => {
      setActiveSection("wordbank")
      setSelectedLemmaState(builtinAwareLemma(lemma))
      setSelectedMeaningId(null)
      setSelectedSentenceId(null)
    },
    openWordbankMeaning: (lemma: string, meaningId: number) => {
      const nextLemma = builtinAwareLemma(lemma)
      setActiveSection("wordbank")
      setSelectedLemmaState(nextLemma)
      setSelectedMeaningId(nextLemma === lemma ? meaningId : null)
      setSelectedSentenceId(null)
    },
    openWordbankRoot: () => {
      setActiveSection("wordbank")
      setSelectedLemmaState(null)
      setSelectedMeaningId(null)
      setSelectedSentenceId(null)
    },
    openPendingSentence: (sourceText: string, englishTranslation: string | null = null) => {
      setActiveSection("sentencebank")
      setPendingSentence({ source_text: sourceText, english_translation: englishTranslation })
      setSelectedSentenceId(null)
      setSelectedLemmaState(null)
      setSelectedMeaningId(null)
    },
    openSentence: (id: number) => {
      setActiveSection("sentencebank")
      setSelectedSentenceId(id)
      setPendingSentence(null)
      setSelectedLemmaState(null)
      setSelectedMeaningId(null)
    },
  }
}
