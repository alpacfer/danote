import type { WordbankLemma } from "@/app/core"
import type { PronounCategory } from "@/app/sections/wordbank/pronouns/pronouns-data"
import { WordbankPronounDemonstrativeTable } from "@/app/sections/wordbank/pronouns/wordbank-pronoun-demonstrative-table"
import { WordbankPronounOtherList } from "@/app/sections/wordbank/pronouns/wordbank-pronoun-other-list"
import { WordbankPronounPersonalTable } from "@/app/sections/wordbank/pronouns/wordbank-pronoun-personal-table"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ChevronLeft } from "lucide-react"

type WordbankPronounPageProps = {
  category: PronounCategory
  lemmas: WordbankLemma[]
  onBack: () => void
}

export function WordbankPronounPage({ category, lemmas, onBack }: WordbankPronounPageProps) {
  const savedLemmas = new Set(lemmas.map((l) => l.lemma.toLowerCase()))

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-4 pr-1">
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="text-muted-foreground -ml-2 h-7 gap-1 px-2"
              onClick={onBack}
              aria-label="Back to wordbank"
            >
              <ChevronLeft className="size-4" />
              Back
            </Button>
          </div>

          {category === "personal_possessive" && <WordbankPronounPersonalTable savedLemmas={savedLemmas} />}
          {category === "demonstrative" && <WordbankPronounDemonstrativeTable savedLemmas={savedLemmas} />}
          {category === "interrogative_other" && <WordbankPronounOtherList savedLemmas={savedLemmas} />}
        </div>
      </ScrollArea>
    </div>
  )
}
