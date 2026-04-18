import { type ComponentProps } from "react"

import { SentencebankSection } from "@/app/sections/sentencebank-section"

export type SentencebankSectionAdapterArgs = {
  sentencebankError: ComponentProps<typeof SentencebankSection>["sentencebankError"]
  isSentencebankLoading: ComponentProps<typeof SentencebankSection>["isSentencebankLoading"]
  sentences: ComponentProps<typeof SentencebankSection>["sentences"]
  selectedSentenceId: ComponentProps<typeof SentencebankSection>["selectedSentenceId"]
  pendingSentence: ComponentProps<typeof SentencebankSection>["pendingSentence"]
  pronunciationLoadingBySentenceId: ComponentProps<typeof SentencebankSection>["pronunciationLoadingBySentenceId"]
  regeneratingPronunciationBySentenceId: ComponentProps<typeof SentencebankSection>["regeneratingPronunciationBySentenceId"]
  openSentence: ComponentProps<typeof SentencebankSection>["onOpenSentence"]
  openWordbankLemma: ComponentProps<typeof SentencebankSection>["onOpenWordbankLemma"]
  openWordbankMeaning: ComponentProps<typeof SentencebankSection>["onOpenWordbankMeaning"]
  playPronunciation: (sentenceId: number) => Promise<void>
  playPronunciationSlowly: (sentenceId: number) => Promise<void>
  regeneratePronunciation: (sentenceId: number) => Promise<void>
}

export function buildSentencebankSectionProps({
  sentencebankError,
  isSentencebankLoading,
  sentences,
  selectedSentenceId,
  pendingSentence,
  pronunciationLoadingBySentenceId,
  regeneratingPronunciationBySentenceId,
  openSentence,
  openWordbankLemma,
  openWordbankMeaning,
  playPronunciation,
  playPronunciationSlowly,
  regeneratePronunciation,
}: SentencebankSectionAdapterArgs): ComponentProps<typeof SentencebankSection> {
  return {
    sentencebankError,
    isSentencebankLoading,
    sentences,
    selectedSentenceId,
    pendingSentence,
    pronunciationLoadingBySentenceId,
    regeneratingPronunciationBySentenceId,
    onOpenSentence: openSentence,
    onOpenWordbankLemma: openWordbankLemma,
    onOpenWordbankMeaning: openWordbankMeaning,
    onPlayPronunciation: (sentenceId: number) => {
      void playPronunciation(sentenceId)
    },
    onPlayPronunciationSlowly: (sentenceId: number) => {
      void playPronunciationSlowly(sentenceId)
    },
    onRegeneratePronunciation: (sentenceId: number) => {
      void regeneratePronunciation(sentenceId)
    },
  }
}
