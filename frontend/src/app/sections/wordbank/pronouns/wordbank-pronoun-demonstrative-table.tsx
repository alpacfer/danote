import { DEMONSTRATIVE_ROWS, pronounTranslation } from "@/app/sections/wordbank/pronouns/pronouns-data"
import { Card, CardContent } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

type Props = {
  savedLemmas?: Set<string>
}

function PronounCell({ lemma }: { lemma: string; savedLemmas?: Set<string> }) {
  const translation = pronounTranslation(lemma)
  const content = (
    <span className="text-foreground rounded px-1.5 py-0.5 text-sm font-semibold">
      {lemma}
    </span>
  )
  if (!translation) {
    return content
  }
  return (
    <Tooltip>
      <TooltipTrigger asChild>{content}</TooltipTrigger>
      <TooltipContent side="right" sideOffset={8}>
        <p>{translation}</p>
      </TooltipContent>
    </Tooltip>
  )
}

export function WordbankPronounDemonstrativeTable({ savedLemmas }: Props) {
  return (
    <Card className="py-5">
      <CardContent className="space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold">Demonstrative</h3>
            </div>
          </div>
        </div>
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="text-muted-foreground w-24 text-[11px] font-semibold uppercase tracking-wide" />
              <TableHead className="text-muted-foreground text-[11px] font-semibold uppercase tracking-wide" />
              <TableHead className="text-muted-foreground text-[11px] font-semibold uppercase tracking-wide">
                Common
              </TableHead>
              <TableHead className="text-muted-foreground text-[11px] font-semibold uppercase tracking-wide">
                Neuter
              </TableHead>
              <TableHead className="text-muted-foreground text-[11px] font-semibold uppercase tracking-wide">
                Plural
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {DEMONSTRATIVE_ROWS.map((row) => (
              <TableRow key={row.label} className="hover:bg-transparent">
                <TableCell className="text-muted-foreground whitespace-nowrap pr-2 text-xs font-medium">
                  {row.label}
                </TableCell>
                <TableCell className="text-muted-foreground/70 pr-4 text-xs italic">{row.english}</TableCell>
                <TableCell>
                  <PronounCell lemma={row.common} savedLemmas={savedLemmas} />
                </TableCell>
                <TableCell>
                  <PronounCell lemma={row.neuter} savedLemmas={savedLemmas} />
                </TableCell>
                <TableCell>
                  <PronounCell lemma={row.plural} savedLemmas={savedLemmas} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
