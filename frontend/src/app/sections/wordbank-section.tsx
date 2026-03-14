import type { WordbankSectionProps } from "@/app/sections/wordbank/wordbank-section-types"
import { WordbankListView } from "@/app/sections/wordbank/wordbank-list-view"
import { WordbankWordPage } from "@/app/sections/wordbank/wordbank-word-page"

export type { WordbankSectionProps } from "@/app/sections/wordbank/wordbank-section-types"

export function WordbankSection(props: WordbankSectionProps) {
  if (!props.selectedLemma) {
    return <WordbankListView {...props} />
  }

  return <WordbankWordPage {...props} />
}
