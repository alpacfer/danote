import type { WordbankSectionProps } from "@/app/sections/wordbank/wordbank-section-types"
import { WordbankDetailsView } from "@/app/sections/wordbank/wordbank-details-view"
import { WordbankListView } from "@/app/sections/wordbank/wordbank-list-view"

export type { WordbankSectionProps } from "@/app/sections/wordbank/wordbank-section-types"

export function WordbankSection(props: WordbankSectionProps) {
  if (!props.selectedLemma) {
    return <WordbankListView {...props} />
  }

  return <WordbankDetailsView {...props} />
}
