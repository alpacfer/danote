import { useEffect, useMemo, useState, type CSSProperties } from "react"

import { normalizeSearchWord, type CompleteVariationsResponse } from "@/app/core"
import {
  ParadigmCellEntries,
  ParadigmCellForm,
} from "@/app/sections/wordbank/wordbank-paradigm-forms"
import {
  ParadigmMissingCell,
  type ParadigmCellCoordinate,
} from "@/app/sections/wordbank/wordbank-paradigm-reveal"
import type { ParadigmTableData } from "@/app/sections/wordbank/wordbank-paradigm-utils"
import { Table, TableBody, TableHead, TableHeader, TableRow } from "@/components/ui/table"

type WordbankParadigmTableProps = {
  paradigm: ParadigmTableData
  pronunciationLoadingByForm: Record<string, boolean>
  regeneratingPronunciationByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  onRegeneratePronunciation: (form: string) => void
  nonInteractiveForms?: Set<string>
  isCompletionAvailable?: boolean
  completionUnavailableReason?: string
  isCompletingVariations?: boolean
  onCompleteVariations?: () => Promise<CompleteVariationsResponse | null>
}

type RevealState = {
  origin: ParadigmCellCoordinate
  normalizedForms: Set<string>
}

export function WordbankParadigmTable({
  paradigm,
  pronunciationLoadingByForm,
  regeneratingPronunciationByForm,
  onPlayPronunciation,
  onRegeneratePronunciation,
  nonInteractiveForms,
  isCompletionAvailable = false,
  completionUnavailableReason = "Complete variations unavailable",
  isCompletingVariations = false,
  onCompleteVariations,
}: WordbankParadigmTableProps) {
  const [pendingCell, setPendingCell] = useState<ParadigmCellCoordinate | null>(null)
  const [reveal, setReveal] = useState<RevealState | null>(null)
  const revealedCellKeys = useMemo(
    () => reveal
      ? paradigm.cells
        .filter((cell) => cell.entries.some((entry) => reveal.normalizedForms.has(normalizeSearchWord(entry.form.form))))
        .map((cell) => cellKey(cell))
      : [],
    [paradigm.cells, reveal],
  )
  const revealedCellsSignature = revealedCellKeys.join("|")

  useEffect(() => {
    if (!reveal || !revealedCellsSignature) {
      return
    }
    const timeout = window.setTimeout(() => setReveal(null), 1200)
    return () => window.clearTimeout(timeout)
  }, [reveal, revealedCellsSignature])

  const pronunciationProps = {
    pronunciationLoadingByForm,
    regeneratingPronunciationByForm,
    onPlayPronunciation,
    onRegeneratePronunciation,
    nonInteractiveForms,
  }

  const revealFromCell = async (origin: ParadigmCellCoordinate) => {
    if (!onCompleteVariations || pendingCell || isCompletingVariations || !isCompletionAvailable) {
      return
    }
    setReveal(null)
    setPendingCell(origin)
    const response = await onCompleteVariations()
    setPendingCell(null)
    if (response?.status === "updated" && response.added_surface_forms.length > 0) {
      setReveal({
        origin,
        normalizedForms: new Set(response.added_surface_forms.map(normalizeSearchWord)),
      })
    }
  }

  return (
    <div className="flex flex-col gap-4" data-morphology-journey>
      <Table className="table-fixed">
        <colgroup>
          <col className="w-32" />
          {paradigm.columns.map((column) => <col key={column} />)}
        </colgroup>
        <TableHeader>
          <TableRow>
            <TableHead scope="col">{paradigm.axisLabel}</TableHead>
            {paradigm.columns.map((column) => (
              <TableHead key={column} scope="col">{column}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {paradigm.rows.map((row) => (
            <TableRow key={row}>
              <TableHead scope="row">{row}</TableHead>
              {paradigm.columns.map((column) => {
                const cell = paradigm.cells.find((item) => item.row === row && item.column === column)
                const coordinate = { row, column }
                const key = cell ? cellKey(cell) : `${row}-${column}`
                const revealIndex = revealedCellKeys.indexOf(key)
                const isRevealOrigin = reveal?.origin.row === row && reveal.origin.column === column
                const isPending = pendingCell?.row === row && pendingCell.column === column
                return (
                  <td
                    key={key}
                    data-paradigm-cell
                    data-empty-cell={!cell || cell.entries.length === 0 ? "true" : undefined}
                    data-reveal-origin={isRevealOrigin ? "true" : undefined}
                    data-newly-revealed={revealIndex >= 0 ? "true" : undefined}
                    style={revealIndex >= 0
                      ? { "--danote-reveal-index": revealIndex } as CSSProperties
                      : undefined}
                  >
                    {cell && cell.entries.length > 0 ? (
                      <ParadigmCellEntries entries={cell.entries} {...pronunciationProps} />
                    ) : (
                      <ParadigmMissingCell
                        {...coordinate}
                        isLoading={isPending}
                        isLocked={!isCompletionAvailable || !onCompleteVariations}
                        isTemporarilyDisabled={Boolean(pendingCell) || isCompletingVariations}
                        lockedReason={completionUnavailableReason}
                        onReveal={() => {
                          void revealFromCell(coordinate)
                        }}
                      />
                    )}
                  </td>
                )
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {paradigm.supplementaryGroups.map((group) => (
        <div key={group.label} className="flex flex-col gap-2" data-paradigm-supplement>
          <p>{group.label}</p>
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            {group.forms.map((form) => (
              <ParadigmCellForm key={form.form} form={form} {...pronunciationProps} />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function cellKey(cell: { row: string; column: string }): string {
  return `${cell.row}-${cell.column}`
}
