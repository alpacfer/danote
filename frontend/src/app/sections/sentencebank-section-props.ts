import { type ComponentProps } from "react"

import { SentencebankSection } from "@/app/sections/sentencebank-section"

export type SentencebankSectionAdapterArgs = {
  sentencebankError: ComponentProps<typeof SentencebankSection>["sentencebankError"]
  isSentencebankLoading: ComponentProps<typeof SentencebankSection>["isSentencebankLoading"]
  sentences: ComponentProps<typeof SentencebankSection>["sentences"]
}

export function buildSentencebankSectionProps({
  sentencebankError,
  isSentencebankLoading,
  sentences,
}: SentencebankSectionAdapterArgs): ComponentProps<typeof SentencebankSection> {
  return {
    sentencebankError,
    isSentencebankLoading,
    sentences,
  }
}
