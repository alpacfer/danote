import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"

import { type AppSection } from "@/app/core"
import { parseHvQuestionSentinel } from "@/app/sections/wordbank/hv-questions/hv-question-data"
import { parseNumbersSentinel } from "@/app/sections/wordbank/numbers/numbers-data"
import { parsePronounSentinel, PRONOUN_CATEGORY_LABELS } from "@/app/sections/wordbank/pronouns/pronouns-data"

export type AppBreadcrumbProps = {
  activeSection: AppSection
  selectedLemma: string | null
  onSelectWordbank: () => void
}

export function AppBreadcrumb({
  activeSection,
  selectedLemma,
  onSelectWordbank,
}: AppBreadcrumbProps) {
  const pronounCategory = selectedLemma ? parsePronounSentinel(selectedLemma) : null
  const pageLabel = selectedLemma && parseHvQuestionSentinel(selectedLemma)
    ? "HV Question Words"
    : selectedLemma && parseNumbersSentinel(selectedLemma)
      ? "Numbers"
      : pronounCategory
        ? PRONOUN_CATEGORY_LABELS[pronounCategory]
        : selectedLemma

  if (activeSection === "developer") {
    return (
      <Breadcrumb>
        <BreadcrumbList className="text-2xl leading-[1.1] font-semibold tracking-tight">
          <BreadcrumbItem>
            <BreadcrumbPage>Developer</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    )
  }

  if (activeSection === "sentencebank") {
    return (
      <Breadcrumb>
        <BreadcrumbList className="text-2xl leading-[1.1] font-semibold tracking-tight">
          <BreadcrumbItem>
            <BreadcrumbPage>Sentencebank</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    )
  }

  return (
    <Breadcrumb>
      <BreadcrumbList className="text-2xl leading-[1.1] font-semibold tracking-tight">
        <BreadcrumbItem>
          {selectedLemma ? (
            <BreadcrumbLink asChild>
              <button type="button" className="font-semibold" onClick={onSelectWordbank}>
                Wordbank
              </button>
            </BreadcrumbLink>
          ) : (
            <BreadcrumbPage>Wordbank</BreadcrumbPage>
          )}
        </BreadcrumbItem>
        {selectedLemma && (
          <>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>{pageLabel}</BreadcrumbPage>
            </BreadcrumbItem>
          </>
        )}
      </BreadcrumbList>
    </Breadcrumb>
  )
}
