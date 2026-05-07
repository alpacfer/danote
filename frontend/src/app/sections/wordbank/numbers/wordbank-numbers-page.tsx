import {
  BASIC_NUMBER_ROWS,
  NUMBER_RULE_ROWS,
  ORDINAL_NUMBER_ROWS,
  ORDINAL_NUMBER_RULE,
  TENS_NUMBER_ROWS,
} from "@/app/sections/wordbank/numbers/numbers-data"
import { useNumberAudio } from "@/app/sections/wordbank/numbers/use-number-audio"
import {
  PinnedPageLayout,
  PinnedPageSection,
  PinnedParadigmTable,
  type ParadigmRow,
} from "@/app/sections/wordbank/_shared"

export function WordbankNumbersPage() {
  const { loadingByTerm, playTerm } = useNumberAudio()

  const basicRows: ParadigmRow[] = BASIC_NUMBER_ROWS.map((row) => ({
    key: `basic-${row.number}`,
    cells: [
      { type: "text", text: String(row.number), muted: true },
      { type: "lemma", lemma: row.word },
    ],
  }))
  const tensRows: ParadigmRow[] = TENS_NUMBER_ROWS.map((row) => ({
    key: `tens-${row.number}`,
    cells: [
      { type: "text", text: String(row.number), muted: true },
      { type: "lemma", lemma: row.word },
    ],
  }))
  const ruleRows: ParadigmRow[] = NUMBER_RULE_ROWS.map((row) => ({
    key: `rule-${row.pattern}`,
    cells: [
      { type: "text", text: row.pattern, muted: true },
      { type: "text", text: row.form },
      { type: "text", text: row.example, italic: true },
    ],
  }))
  const ordinalRows: ParadigmRow[] = ORDINAL_NUMBER_ROWS.map((row) => ({
    key: `ord-${row.number}`,
    cells: [
      { type: "text", text: `${row.number}.`, muted: true },
      { type: "lemma", lemma: row.cardinal },
      { type: "lemma", lemma: row.ordinal },
      { type: "text", text: row.english, muted: true, italic: true },
    ],
  }))

  return (
    <PinnedPageLayout
      title="Numbers"
      description="Cardinal and ordinal numbers in Danish, with the rules for forming larger numbers."
    >
      <div className="grid gap-4 xl:grid-cols-2">
        <PinnedPageSection title="0–19">
          <PinnedParadigmTable
            headers={["Number", "Danish"]}
            rows={basicRows}
            pronunciationLoadingByForm={loadingByTerm}
            onPlayPronunciation={playTerm}
          />
        </PinnedPageSection>
        <PinnedPageSection title="Tens">
          <PinnedParadigmTable
            headers={["Number", "Danish"]}
            rows={tensRows}
            pronunciationLoadingByForm={loadingByTerm}
            onPlayPronunciation={playTerm}
          />
        </PinnedPageSection>
      </div>
      <PinnedPageSection title="Forming larger numbers">
        <PinnedParadigmTable headers={["Range", "Form", "Example"]} rows={ruleRows} />
      </PinnedPageSection>
      <PinnedPageSection
        title="Ordinal numbers"
        description={ORDINAL_NUMBER_RULE}
      >
        <PinnedParadigmTable
          headers={["#", "Cardinal", "Ordinal", "English"]}
          rows={ordinalRows}
          pronunciationLoadingByForm={loadingByTerm}
          onPlayPronunciation={playTerm}
        />
      </PinnedPageSection>
    </PinnedPageLayout>
  )
}
