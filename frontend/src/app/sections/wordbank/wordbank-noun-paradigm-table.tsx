import { normalizeSearchWord } from "@/app/core"
import type { NounParadigm, SurfaceForm } from "@/app/sections/wordbank/wordbank-paradigm-utils"
import { WordbankPronunciationWord } from "@/app/sections/wordbank/wordbank-pronunciation-word"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

type WordbankNounParadigmTableProps = {
  paradigm: NounParadigm
  pronunciationLoadingByForm: Record<string, boolean>
  regeneratingPronunciationByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  onRegeneratePronunciation: (form: string) => void
}

export function WordbankNounParadigmTable({
  paradigm,
  pronunciationLoadingByForm,
  regeneratingPronunciationByForm,
  onPlayPronunciation,
  onRegeneratePronunciation,
}: WordbankNounParadigmTableProps) {
  return (
    <div className="space-y-3">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="text-muted-foreground w-24 text-[11px] font-semibold uppercase tracking-wide" />
            {paradigm.columns.map((col) => (
              <TableHead
                key={col}
                className="text-muted-foreground text-[11px] font-semibold uppercase tracking-wide"
              >
                {col}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {paradigm.rows.map((row) => (
            <TableRow key={row} className="hover:bg-transparent">
              <TableCell className="text-muted-foreground whitespace-nowrap pr-4 text-sm font-medium">
                {row}
              </TableCell>
              {paradigm.columns.map((col) => {
                const cell = paradigm.cells.find((c) => c.row === row && c.column === col)
                return (
                  <TableCell key={`${row}-${col}`} className="whitespace-normal">
                    {cell && cell.forms.length > 0 ? (
                      <div className="space-y-1">
                        {cell.forms.map((form) => (
                          <ParadigmCellForm
                            key={form.form}
                            form={form}
                            pronunciationLoadingByForm={pronunciationLoadingByForm}
                            regeneratingPronunciationByForm={regeneratingPronunciationByForm}
                            onPlayPronunciation={onPlayPronunciation}
                            onRegeneratePronunciation={onRegeneratePronunciation}
                          />
                        ))}
                      </div>
                    ) : (
                      <span className="text-muted-foreground/40 text-sm">—</span>
                    )}
                  </TableCell>
                )
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {paradigm.genitiveForms.length > 0 ? (
        <div className="space-y-1.5">
          <p className="text-muted-foreground text-[11px] font-semibold uppercase tracking-wide">Genitive</p>
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            {paradigm.genitiveForms.map((form) => (
              <ParadigmCellForm
                key={form.form}
                form={form}
                pronunciationLoadingByForm={pronunciationLoadingByForm}
                regeneratingPronunciationByForm={regeneratingPronunciationByForm}
                onPlayPronunciation={onPlayPronunciation}
                onRegeneratePronunciation={onRegeneratePronunciation}
              />
            ))}
          </div>
        </div>
      ) : null}
      {paradigm.unclassifiedForms.length > 0 ? (
        <div className="space-y-1.5">
          <p className="text-muted-foreground text-[11px] font-semibold uppercase tracking-wide">Other forms</p>
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            {paradigm.unclassifiedForms.map((form) => (
              <ParadigmCellForm
                key={form.form}
                form={form}
                pronunciationLoadingByForm={pronunciationLoadingByForm}
                regeneratingPronunciationByForm={regeneratingPronunciationByForm}
                onPlayPronunciation={onPlayPronunciation}
                onRegeneratePronunciation={onRegeneratePronunciation}
              />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}

function ParadigmCellForm({
  form,
  pronunciationLoadingByForm,
  regeneratingPronunciationByForm,
  onPlayPronunciation,
  onRegeneratePronunciation,
}: {
  form: SurfaceForm
  pronunciationLoadingByForm: Record<string, boolean>
  regeneratingPronunciationByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  onRegeneratePronunciation: (form: string) => void
}) {
  const normalizedForm = normalizeSearchWord(form.form)
  const isRegenerating = Boolean(regeneratingPronunciationByForm[normalizedForm])
  return (
    <WordbankPronunciationWord
      form={form.form}
      hasPronunciation={form.has_pronunciation ?? false}
      pronunciationLoadingByForm={pronunciationLoadingByForm}
      onPlayPronunciation={onPlayPronunciation}
      contextMenuItems={[
        {
          label: isRegenerating ? "Regenerating audio..." : "Regenerate audio",
          disabled: isRegenerating,
          onSelect: () => onRegeneratePronunciation(form.form),
        },
      ]}
      className="text-sm font-semibold"
      iconClassName="size-3"
    />
  )
}
