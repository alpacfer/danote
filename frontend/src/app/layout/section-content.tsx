import { type ComponentProps } from "react"

import {
  DeveloperSection,
  NotesSection,
  SentencebankSection,
  WordbankSection,
} from "@/app/sections"
import { type AppSection } from "@/app/core"

type SectionContentProps = {
  activeSection: AppSection
  notesProps: ComponentProps<typeof NotesSection>
  wordbankProps: ComponentProps<typeof WordbankSection>
  sentencebankProps: ComponentProps<typeof SentencebankSection>
  developerProps: ComponentProps<typeof DeveloperSection>
}

export function SectionContent({
  activeSection,
  notesProps,
  wordbankProps,
  sentencebankProps,
  developerProps,
}: SectionContentProps) {
  if (activeSection === "notes") {
    return <NotesSection {...notesProps} />
  }
  if (activeSection === "wordbank") {
    return <WordbankSection {...wordbankProps} />
  }
  if (activeSection === "sentencebank") {
    return <SentencebankSection {...sentencebankProps} />
  }
  return <DeveloperSection {...developerProps} />
}
