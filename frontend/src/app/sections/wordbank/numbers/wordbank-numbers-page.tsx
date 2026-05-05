import { ChevronLeft } from "lucide-react"

import {
  BASIC_NUMBER_ROWS,
  NUMBER_RULE_ROWS,
  TENS_NUMBER_ROWS,
} from "@/app/sections/wordbank/numbers/numbers-data"
import { useNumberAudio } from "@/app/sections/wordbank/numbers/use-number-audio"
import { WordbankPronunciationWord } from "@/app/sections/wordbank/wordbank-pronunciation-word"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export function WordbankNumbersPage({ onBack }: { onBack: () => void }) {
  const { loadingByTerm, playTerm } = useNumberAudio()

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <div>
        <Button type="button" variant="ghost" size="sm" className="-ml-2" onClick={onBack}>
          <ChevronLeft className="size-4" />
          Back
        </Button>
      </div>
      <ScrollArea className="min-h-0 flex-1">
        <div className="grid gap-4 pr-2 xl:grid-cols-[1fr_1fr]">
          <NumberTable
            title="0-19"
            rows={BASIC_NUMBER_ROWS}
            loadingByTerm={loadingByTerm}
            onPlayTerm={playTerm}
          />
          <NumberTable
            title="Tens"
            rows={TENS_NUMBER_ROWS}
            loadingByTerm={loadingByTerm}
            onPlayTerm={playTerm}
          />
          <Card className="xl:col-span-2">
            <CardHeader>
              <CardTitle className="text-lg">Forming Numbers</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Range</TableHead>
                    <TableHead>Form</TableHead>
                    <TableHead>Example</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {NUMBER_RULE_ROWS.map((row) => (
                    <TableRow key={row.pattern}>
                      <TableCell className="font-medium">{row.pattern}</TableCell>
                      <TableCell>{row.form}</TableCell>
                      <TableCell>{row.example}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      </ScrollArea>
    </div>
  )
}

function NumberTable({
  title,
  rows,
  loadingByTerm,
  onPlayTerm,
}: {
  title: string
  rows: Array<{ number: number; word: string }>
  loadingByTerm: Record<string, boolean>
  onPlayTerm: (term: string) => void
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Number</TableHead>
              <TableHead>Danish</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.number}>
                <TableCell className="font-medium">{row.number}</TableCell>
                <TableCell>
                  <WordbankPronunciationWord
                    form={row.word}
                    hasPronunciation={true}
                    pronunciationLoadingByForm={loadingByTerm}
                    onPlayPronunciation={onPlayTerm}
                    className="text-sm font-semibold"
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
