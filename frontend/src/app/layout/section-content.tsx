import { type ComponentProps } from "react"

import {
  DeveloperSection,
  NotesSection,
  PlaygroundSection,
  SentencebankSection,
  WordbankSection,
} from "@/app/sections"
import { type AppSection } from "@/app/core"

type SectionContentProps = {
  activeSection: AppSection
  playgroundProps: ComponentProps<typeof PlaygroundSection>
  notesProps: ComponentProps<typeof NotesSection>
  wordbankProps: ComponentProps<typeof WordbankSection>
  sentencebankProps: ComponentProps<typeof SentencebankSection>
  developerProps: ComponentProps<typeof DeveloperSection>
}

export function SectionContent({
  activeSection,
  playgroundProps,
  notesProps,
  wordbankProps,
  sentencebankProps,
  developerProps,
}: SectionContentProps) {
  if (activeSection === "playground") {
    return <PlaygroundSection {...playgroundProps} />
  }
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
