import {
  ARTICLES_GENDER_RULES,
  DEFINITE_SUFFIX_ROWS,
  INDEFINITE_ARTICLE_ROWS,
  NOUN_PARADIGM_ROWS,
} from "@/app/sections/wordbank/articles-gender/articles-gender-data"
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

export function WordbankArticlesGenderPage({
  pronunciationLoadingByForm,
  onPlayPronunciation,
}: Props) {
  const indefiniteRows: ParadigmRow[] = INDEFINITE_ARTICLE_ROWS.map((row) => ({
    key: `indef-${row.label}`,
    cells: [
      { type: "label", text: row.label },
      { type: "lemma", lemma: row.example },
      { type: "text", text: row.english, muted: true, italic: true },
    ],
  }))
  const definiteRows: ParadigmRow[] = DEFINITE_SUFFIX_ROWS.map((row) => ({
    key: `def-${row.label}`,
    cells: [
      { type: "label", text: row.label },
      { type: "lemma", lemma: row.example.split(" / ")[0] ?? row.example },
      { type: "text", text: row.english, muted: true, italic: true },
    ],
  }))
  const paradigmRows: ParadigmRow[] = NOUN_PARADIGM_ROWS.map((row) => ({
    key: `paradigm-${row.indefinite}`,
    cells: [
      { type: "text", text: row.english, muted: true, italic: true },
      { type: "lemma", lemma: row.indefinite },
      { type: "lemma", lemma: row.definite },
      { type: "lemma", lemma: row.pluralIndefinite },
      { type: "lemma", lemma: row.pluralDefinite },
    ],
  }))

  return (
    <PinnedPageLayout
      title="Articles & Gender"
      description="Danish nouns are either common (en) or neuter (et). The article fuses with the noun in the definite form."
    >
      <div className="grid gap-4 xl:grid-cols-2">
        <PinnedPageSection title="Indefinite article">
          <PinnedParadigmTable
            headers={[null, "Example", "English"]}
            rows={indefiniteRows}
            pronunciationLoadingByForm={pronunciationLoadingByForm}
            onPlayPronunciation={onPlayPronunciation}
          />
        </PinnedPageSection>
        <PinnedPageSection title="Definite suffix">
          <PinnedParadigmTable
            headers={[null, "Example", "English"]}
            rows={definiteRows}
            pronunciationLoadingByForm={pronunciationLoadingByForm}
            onPlayPronunciation={onPlayPronunciation}
          />
        </PinnedPageSection>
      </div>
      <PinnedPageSection title="Full noun paradigm">
        <PinnedParadigmTable
          headers={["Meaning", "Indef. sg.", "Def. sg.", "Indef. pl.", "Def. pl."]}
          rows={paradigmRows}
          pronunciationLoadingByForm={pronunciationLoadingByForm}
          onPlayPronunciation={onPlayPronunciation}
        />
      </PinnedPageSection>
      <PinnedPageSection title="Notes">
        <ul className="space-y-2 text-sm">
          {ARTICLES_GENDER_RULES.map((rule) => (
            <li key={rule} className="text-muted-foreground leading-relaxed">
              {rule}
            </li>
          ))}
        </ul>
      </PinnedPageSection>
    </PinnedPageLayout>
  )
}
