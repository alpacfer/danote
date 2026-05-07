import {
  PERSONAL_PRONOUN_ROWS,
  pronounTranslation,
} from "@/app/sections/wordbank/pronouns/pronouns-data"
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

export function WordbankPronounPersonalPage({
  pronunciationLoadingByForm,
  onPlayPronunciation,
}: Props) {
  const rows: ParadigmRow[] = PERSONAL_PRONOUN_ROWS.map((row) => ({
    key: row.label,
    cells: [
      { type: "label", text: row.label },
      row.nominative
        ? { type: "lemma", lemma: row.nominative, tooltip: pronounTranslation(row.nominative) }
        : { type: "empty" },
      { type: "lemma", lemma: row.accusative, tooltip: pronounTranslation(row.accusative) },
    ],
  }))
  return (
    <PinnedPageLayout
      title="Personal Pronouns"
      description="Subject (nominative) and object (accusative) forms across person and number, including the formal register De/Dem."
    >
      <PinnedPageSection>
        <PinnedParadigmTable
          headers={[null, "Nominative", "Accusative"]}
          rows={rows}
          pronunciationLoadingByForm={pronunciationLoadingByForm}
          onPlayPronunciation={onPlayPronunciation}
        />
      </PinnedPageSection>
    </PinnedPageLayout>
  )
}
