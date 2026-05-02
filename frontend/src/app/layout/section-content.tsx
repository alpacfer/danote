import { type ComponentProps } from "react"

import {
  DeveloperSection,
  SentencebankSection,
  WordbankSection,
} from "@/app/sections"
import { type AppSection } from "@/app/core"

type SectionContentProps = {
  activeSection: AppSection
  wordbankProps: ComponentProps<typeof WordbankSection>
  sentencebankProps: ComponentProps<typeof SentencebankSection>
  developerProps: ComponentProps<typeof DeveloperSection>
}

export function SectionContent({
  activeSection,
  wordbankProps,
  sentencebankProps,
  developerProps,
}: SectionContentProps) {
  if (activeSection === "wordbank") {
    return <WordbankSection {...wordbankProps} />
  }
  if (activeSection === "sentencebank") {
    return <SentencebankSection {...sentencebankProps} />
  }
  return <DeveloperSection {...developerProps} />
}
