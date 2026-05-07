import type { WordbankLemma } from "@/app/core"
import type { PronounCategory } from "@/app/sections/wordbank/pronouns/pronouns-data"
import { WordbankPronounDemonstrativeTable } from "@/app/sections/wordbank/pronouns/wordbank-pronoun-demonstrative-table"
import { WordbankPronounOtherList } from "@/app/sections/wordbank/pronouns/wordbank-pronoun-other-list"
import { WordbankPronounPersonalTable } from "@/app/sections/wordbank/pronouns/wordbank-pronoun-personal-table"
import { ScrollArea } from "@/components/ui/scroll-area"

type WordbankPronounPageProps = {
  category: PronounCategory
  lemmas: WordbankLemma[]
}

export function WordbankPronounPage({ category, lemmas }: WordbankPronounPageProps) {
  const savedLemmas = new Set(lemmas.map((l) => l.lemma.toLowerCase()))

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-4 pr-1">
          {category === "personal_possessive" && <WordbankPronounPersonalTable savedLemmas={savedLemmas} />}
          {category === "demonstrative" && <WordbankPronounDemonstrativeTable savedLemmas={savedLemmas} />}
          {category === "interrogative_other" && <WordbankPronounOtherList savedLemmas={savedLemmas} />}
        </div>
      </ScrollArea>
    </div>
  )
}
