import {
  POSSESSIVE_PRONOUN_ROWS,
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

export function WordbankPronounPossessivePage({
  pronunciationLoadingByForm,
  onPlayPronunciation,
}: Props) {
  const rows: ParadigmRow[] = POSSESSIVE_PRONOUN_ROWS.map((row) => ({
    key: row.label,
    cells: [
      { type: "label", text: row.label },
      { type: "lemma", lemma: row.common, tooltip: pronounTranslation(row.common) },
      { type: "lemma", lemma: row.neuter, tooltip: pronounTranslation(row.neuter) },
      { type: "lemma", lemma: row.plural, tooltip: pronounTranslation(row.plural) },
    ],
  }))
  return (
    <PinnedPageLayout
      title="Possessive Pronouns"
      description="Possessives agree with the gender and number of the noun they modify (common, neuter, plural)."
    >
      <PinnedPageSection>
        <PinnedParadigmTable
          headers={[null, "Common", "Neuter", "Plural"]}
          rows={rows}
          pronunciationLoadingByForm={pronunciationLoadingByForm}
          onPlayPronunciation={onPlayPronunciation}
        />
      </PinnedPageSection>
    </PinnedPageLayout>
  )
}
