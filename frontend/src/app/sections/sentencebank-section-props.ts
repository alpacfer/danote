import { type ComponentProps } from "react"

import { SentencebankSection } from "@/app/sections/sentencebank-section"

export type SentencebankSectionAdapterArgs = {
  sentencebankError: ComponentProps<typeof SentencebankSection>["sentencebankError"]
  isSentencebankLoading: ComponentProps<typeof SentencebankSection>["isSentencebankLoading"]
  sentences: ComponentProps<typeof SentencebankSection>["sentences"]
  selectedSentenceId: ComponentProps<typeof SentencebankSection>["selectedSentenceId"]
  pendingSentence: ComponentProps<typeof SentencebankSection>["pendingSentence"]
  openSentence: ComponentProps<typeof SentencebankSection>["onOpenSentence"]
  openWordbankLemma: ComponentProps<typeof SentencebankSection>["onOpenWordbankLemma"]
  openWordbankMeaning: ComponentProps<typeof SentencebankSection>["onOpenWordbankMeaning"]
}

export function buildSentencebankSectionProps({
  sentencebankError,
  isSentencebankLoading,
  sentences,
  selectedSentenceId,
  pendingSentence,
  openSentence,
  openWordbankLemma,
  openWordbankMeaning,
}: SentencebankSectionAdapterArgs): ComponentProps<typeof SentencebankSection> {
  return {
    sentencebankError,
    isSentencebankLoading,
    sentences,
    selectedSentenceId,
    pendingSentence,
    onOpenSentence: openSentence,
    onOpenWordbankLemma: openWordbankLemma,
    onOpenWordbankMeaning: openWordbankMeaning,
  }
}
