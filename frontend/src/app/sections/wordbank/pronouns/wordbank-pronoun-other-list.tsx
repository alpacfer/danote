import type { OtherPronounGroup } from "@/app/sections/wordbank/pronouns/pronouns-data"
import { OTHER_PRONOUN_GROUPS, pronounTranslation } from "@/app/sections/wordbank/pronouns/pronouns-data"
import { Card, CardContent } from "@/components/ui/card"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

type Props = {
  savedLemmas?: Set<string>
}

function PronounRow({ lemma, english }: { lemma: string; english: string; savedLemmas?: Set<string> }) {
  const translation = pronounTranslation(lemma) ?? english
  const content = (
    <span className="text-foreground rounded px-1.5 py-0.5 text-sm font-semibold">
      {lemma}
    </span>
  )
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-dashed border-border/60 py-1.5 last:border-b-0">
      <Tooltip>
        <TooltipTrigger asChild>{content}</TooltipTrigger>
        <TooltipContent side="right" sideOffset={8}>
          <p>{translation}</p>
        </TooltipContent>
      </Tooltip>
      <span className="text-muted-foreground/70 text-xs italic">{english}</span>
    </div>
  )
}

function GroupCard({ group, savedLemmas }: { group: OtherPronounGroup; savedLemmas: Set<string> }) {
  return (
    <Card className="py-5">
      <CardContent className="space-y-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold">{group.heading}</h3>
          </div>
        </div>
        <div>
          {group.items.map((item) => (
            <PronounRow key={item.lemma} lemma={item.lemma} english={item.english} savedLemmas={savedLemmas} />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

export function WordbankPronounOtherList({ savedLemmas }: Props) {
  return (
    <div className="grid gap-3 lg:grid-cols-3">
      {OTHER_PRONOUN_GROUPS.map((group) => (
        <GroupCard key={group.heading} group={group} savedLemmas={savedLemmas} />
      ))}
    </div>
  )
}
