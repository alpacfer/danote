import { type ComponentProps } from "react"

import {
  AccountSection,
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
  accountProps: ComponentProps<typeof AccountSection>
}

export function SectionContent({
  activeSection,
  wordbankProps,
  sentencebankProps,
  developerProps,
  accountProps,
}: SectionContentProps) {
  if (activeSection === "wordbank") {
    return <WordbankSection {...wordbankProps} />
  }
  if (activeSection === "sentencebank") {
    return <SentencebankSection {...sentencebankProps} />
  }
  if (activeSection === "account") {
    return <AccountSection {...accountProps} />
  }
  return <DeveloperSection {...developerProps} />
}
