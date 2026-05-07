import {
  DEMONSTRATIVE_ROWS,
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

export function WordbankPronounDemonstrativePage({
  pronunciationLoadingByForm,
  onPlayPronunciation,
}: Props) {
  const rows: ParadigmRow[] = DEMONSTRATIVE_ROWS.map((row) => ({
    key: row.label,
    cells: [
      { type: "label", text: row.label },
      { type: "text", text: row.english, muted: true, italic: true },
      { type: "lemma", lemma: row.common, tooltip: pronounTranslation(row.common) },
      { type: "lemma", lemma: row.neuter, tooltip: pronounTranslation(row.neuter) },
      { type: "lemma", lemma: row.plural, tooltip: pronounTranslation(row.plural) },
    ],
  }))
  return (
    <PinnedPageLayout
      title="Demonstrative Pronouns"
      description="Proximal forms (this/these) and distal forms (that/those), both inflected for common, neuter, and plural."
    >
      <PinnedPageSection>
        <PinnedParadigmTable
          headers={[null, null, "Common", "Neuter", "Plural"]}
          rows={rows}
          pronunciationLoadingByForm={pronunciationLoadingByForm}
          onPlayPronunciation={onPlayPronunciation}
        />
      </PinnedPageSection>
    </PinnedPageLayout>
  )
}
