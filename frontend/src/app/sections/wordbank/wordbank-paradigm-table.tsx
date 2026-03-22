import { normalizeSearchWord } from "@/app/core"
import type { ParadigmTableData, SurfaceForm } from "@/app/sections/wordbank/wordbank-paradigm-utils"
import { WordbankPronunciationWord } from "@/app/sections/wordbank/wordbank-pronunciation-word"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { AudioLines, Loader2 } from "lucide-react"

type WordbankParadigmTableProps = {
  paradigm: ParadigmTableData
  pronunciationLoadingByForm: Record<string, boolean>
  regeneratingPronunciationByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  onRegeneratePronunciation: (form: string) => void
}

export function WordbankParadigmTable({
  paradigm,
  pronunciationLoadingByForm,
  regeneratingPronunciationByForm,
  onPlayPronunciation,
  onRegeneratePronunciation,
}: WordbankParadigmTableProps) {
  const hideSingleFormColumnHeader = paradigm.columns.length === 1 && paradigm.columns[0] === "Form"

  return (
    <div className="space-y-3">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="text-muted-foreground w-24 text-[11px] font-semibold uppercase tracking-wide" />
            {paradigm.columns.map((column) => (
              <TableHead
                key={column}
                aria-label={hideSingleFormColumnHeader ? column : undefined}
                className="text-muted-foreground text-[11px] font-semibold uppercase tracking-wide"
              >
                {hideSingleFormColumnHeader ? null : column}
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
              {paradigm.columns.map((column) => {
                const cell = paradigm.cells.find((item) => item.row === row && item.column === column)
                return (
                  <TableCell key={`${row}-${column}`} className="whitespace-normal">
                    {cell && cell.entries.length > 0 ? (
                      <div className="space-y-1">
                        {cell.entries.map((entry) => (
                          <ParadigmCellForm
                            key={`${entry.label ?? "form"}-${entry.form.form}`}
                            form={entry.form}
                            label={entry.label}
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
      {paradigm.supplementaryGroups.map((group) => (
        <div key={group.label} className="space-y-1.5">
          <p className="text-muted-foreground text-[11px] font-semibold uppercase tracking-wide">{group.label}</p>
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            {group.forms.map((form) => (
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
      ))}
    </div>
  )
}

function ParadigmCellForm({
  form,
  label,
  pronunciationLoadingByForm,
  regeneratingPronunciationByForm,
  onPlayPronunciation,
  onRegeneratePronunciation,
}: {
  form: SurfaceForm
  label?: string
  pronunciationLoadingByForm: Record<string, boolean>
  regeneratingPronunciationByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  onRegeneratePronunciation: (form: string) => void
}) {
  const normalizedForm = normalizeSearchWord(form.form)
  const isRegenerating = Boolean(regeneratingPronunciationByForm[normalizedForm])
  return (
    <div className={label ? "flex flex-wrap items-center gap-x-1.5 gap-y-1" : undefined}>
      {label ? <span className="text-muted-foreground text-xs font-medium">{label}:</span> : null}
      <WordbankPronunciationWord
        form={form.form}
        hasPronunciation={form.has_pronunciation ?? false}
        pronunciationLoadingByForm={pronunciationLoadingByForm}
        onPlayPronunciation={onPlayPronunciation}
        contextMenuItems={[
          {
            icon: isRegenerating ? <Loader2 className="animate-spin" /> : <AudioLines />,
            label: isRegenerating ? "Regenerating audio..." : "Regenerate audio",
            disabled: isRegenerating,
            onSelect: () => onRegeneratePronunciation(form.form),
          },
        ]}
        className="text-sm font-semibold"
        iconClassName="size-3"
      />
    </div>
  )
}
