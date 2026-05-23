
import { parsePinnedPageSentinel } from "@/app/sections/wordbank/_shared/pinned-pages-registry"
import { WordbankFunctionWordsPage } from "@/app/sections/wordbank/function-words/wordbank-function-words-page"
import { WordbankNumbersTimePage } from "@/app/sections/wordbank/numbers-time/wordbank-numbers-time-page"
import { WordbankPronounsPage } from "@/app/sections/wordbank/pronouns/wordbank-pronouns-page"
import { WordbankListView } from "@/app/sections/wordbank/wordbank-list-view"
import { type WordbankSectionProps } from "@/app/sections/wordbank/wordbank-section-types"
import { WordbankWordPage } from "@/app/sections/wordbank/wordbank-word-page"

export type { WordbankSectionProps } from "@/app/sections/wordbank/wordbank-section-types"

export function WordbankSection(props: WordbankSectionProps) {
  if (!props.selectedLemma) {
    return (
      <WordbankListView
        {...props}
        filters={props.filters}
        onFiltersChange={props.onFiltersChange}
      />
    )
  }

  const pinned = parsePinnedPageSentinel(props.selectedLemma)
  if (pinned) {
    const pageProps = {
      defaultTab: pinned.defaultTab,
      onOpenWord: props.onOpenPinnedWord,
      onOpenTab: props.onOpenPinnedTab,
    }
    switch (pinned.id) {
      case "pronouns":
        return <WordbankPronounsPage key={props.selectedLemma} {...pageProps} />
      case "function_words":
        return <WordbankFunctionWordsPage key={props.selectedLemma} {...pageProps} />
      case "numbers_time":
        return <WordbankNumbersTimePage key={props.selectedLemma} {...pageProps} />
    }
  }

  return (
    <WordbankWordPage
      {...props}
      onApplyFilterAndNavigateBack={(type: "pos" | "category", value: string) => {
        if (type === "pos") {
          const normalized = value.trim().toUpperCase()
          props.onApplyFilterAndNavigateBack({
            posTags: [normalized],
            categories: [],
          })
        } else {
          const normalized = value.trim()
          props.onApplyFilterAndNavigateBack({
            posTags: [],
            categories: [normalized],
          })
        }
      }}
    />
  )
}
