import {
  DAYS_OF_WEEK,
  MONTHS,
  SEASONS,
  type CalendarRow,
} from "@/app/sections/wordbank/days-months-seasons/days-months-seasons-data"
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

export function WordbankDaysMonthsSeasonsPage({
  pronunciationLoadingByForm,
  onPlayPronunciation,
}: Props) {
  return (
    <PinnedPageLayout
      title="Days, Months & Seasons"
      description="Day, month, and season names. None of these are capitalised in Danish, unlike English."
    >
      <div className="grid gap-4 xl:grid-cols-2">
        <PinnedPageSection title="Days of the week">
          <PinnedParadigmTable
            headers={["Danish", "English"]}
            rows={toRows(DAYS_OF_WEEK, "day")}
            pronunciationLoadingByForm={pronunciationLoadingByForm}
            onPlayPronunciation={onPlayPronunciation}
          />
        </PinnedPageSection>
        <PinnedPageSection title="Seasons">
          <PinnedParadigmTable
            headers={["Danish", "English"]}
            rows={toRows(SEASONS, "season")}
            pronunciationLoadingByForm={pronunciationLoadingByForm}
            onPlayPronunciation={onPlayPronunciation}
          />
        </PinnedPageSection>
      </div>
      <PinnedPageSection title="Months">
        <PinnedParadigmTable
          headers={["Danish", "English"]}
          rows={toRows(MONTHS, "month")}
          pronunciationLoadingByForm={pronunciationLoadingByForm}
          onPlayPronunciation={onPlayPronunciation}
        />
      </PinnedPageSection>
    </PinnedPageLayout>
  )
}

function toRows(rows: CalendarRow[], prefix: string): ParadigmRow[] {
  return rows.map((row) => ({
    key: `${prefix}-${row.lemma}`,
    cells: [
      { type: "lemma", lemma: row.lemma },
      { type: "text", text: row.english, muted: true, italic: true },
    ],
  }))
}
