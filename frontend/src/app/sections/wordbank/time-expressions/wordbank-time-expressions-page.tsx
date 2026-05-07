import {
  CLOCK_PHRASES,
  DURATION_ROWS,
  FREQUENCY_ROWS,
  RELATIVE_DAY_ROWS,
  type TimeExpressionRow,
} from "@/app/sections/wordbank/time-expressions/time-expressions-data"
import {
  PinnedPageLayout,
  PinnedPageSection,
  PinnedParadigmTable,
  type ParadigmRow,
} from "@/app/sections/wordbank/_shared"

type Props = {
  pronunciationLoadingByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
}

export function WordbankTimeExpressionsPage({
  pronunciationLoadingByForm,
  onPlayPronunciation,
}: Props) {
  return (
    <PinnedPageLayout
      title="Time Expressions"
      description="Telling time, talking about days relative to today, and expressing durations and frequency."
    >
      <PinnedPageSection title="Clock">
        <PinnedParadigmTable
          headers={["Danish", "English"]}
          rows={toRows(CLOCK_PHRASES, "clock")}
          pronunciationLoadingByForm={pronunciationLoadingByForm}
          onPlayPronunciation={onPlayPronunciation}
        />
      </PinnedPageSection>
      <div className="grid gap-4 xl:grid-cols-2">
        <PinnedPageSection title="Relative day">
          <PinnedParadigmTable
            headers={["Danish", "English"]}
            rows={toRows(RELATIVE_DAY_ROWS, "rel")}
            pronunciationLoadingByForm={pronunciationLoadingByForm}
            onPlayPronunciation={onPlayPronunciation}
          />
        </PinnedPageSection>
        <PinnedPageSection title="Duration">
          <PinnedParadigmTable
            headers={["Danish", "English"]}
            rows={toRows(DURATION_ROWS, "dur")}
            pronunciationLoadingByForm={pronunciationLoadingByForm}
            onPlayPronunciation={onPlayPronunciation}
          />
        </PinnedPageSection>
      </div>
      <PinnedPageSection title="Frequency">
        <PinnedParadigmTable
          headers={["Danish", "English"]}
          rows={toRows(FREQUENCY_ROWS, "freq")}
          pronunciationLoadingByForm={pronunciationLoadingByForm}
          onPlayPronunciation={onPlayPronunciation}
        />
      </PinnedPageSection>
    </PinnedPageLayout>
  )
}

function toRows(rows: TimeExpressionRow[], prefix: string): ParadigmRow[] {
  return rows.map((row, index) => ({
    key: `${prefix}-${index}`,
    cells: row.note
      ? [
          { type: "lemma", lemma: row.lemma, tooltip: row.note },
          { type: "text", text: row.english, muted: true, italic: true },
        ]
      : [
          { type: "lemma", lemma: row.lemma },
          { type: "text", text: row.english, muted: true, italic: true },
        ],
  }))
}
