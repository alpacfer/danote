import { useEffect, useMemo, useState } from "react"

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

type CompletionRevealState = {
  generatedForms: Set<string>
  revealedCellKeys: Set<string>
  lastRevealedCellKey: string | null
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
  const [completionReveal, setCompletionReveal] = useState<CompletionRevealState | null>(null)
  const generatedCellKeys = useMemo(
    () => new Set(
      completionReveal
        ? paradigm.cells
          .filter((cell) => cell.entries.some((entry) => completionReveal.generatedForms.has(normalizeSearchWord(entry.form.form))))
          .map(cellKey)
        : [],
    ),
    [completionReveal, paradigm.cells],
  )

  useEffect(() => {
    if (!completionReveal?.lastRevealedCellKey) {
      return
    }
    const timeout = window.setTimeout(() => {
      setCompletionReveal((current) => current
        ? { ...current, lastRevealedCellKey: null }
        : null)
    }, 1200)
    return () => window.clearTimeout(timeout)
  }, [completionReveal?.lastRevealedCellKey])

  const pronunciationProps = {
    pronunciationLoadingByForm,
    regeneratingPronunciationByForm,
    onPlayPronunciation,
    onRegeneratePronunciation,
    nonInteractiveForms,
  }

  const generateFromCell = async (origin: ParadigmCellCoordinate) => {
    if (!onCompleteVariations || pendingCell || isCompletingVariations || !isCompletionAvailable) {
      return
    }
    setCompletionReveal(null)
    setPendingCell(origin)
    const response = await onCompleteVariations()
    setPendingCell(null)
    if (response) {
      const originKey = coordinateKey(origin)
      setCompletionReveal({
        generatedForms: new Set(response.added_surface_forms.map(normalizeSearchWord)),
        revealedCellKeys: new Set([originKey]),
        lastRevealedCellKey: originKey,
      })
    }
  }

  const revealGeneratedCell = (key: string) => {
    setCompletionReveal((current) => current
      ? {
          ...current,
          revealedCellKeys: new Set([...current.revealedCellKeys, key]),
          lastRevealedCellKey: key,
        }
      : null)
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
                const key = cell ? cellKey(cell) : coordinateKey(coordinate)
                const isGeneratedCell = generatedCellKeys.has(key)
                const isConcealedGeneratedCell = isGeneratedCell && !completionReveal?.revealedCellKeys.has(key)
                const isNewlyRevealed = completionReveal?.lastRevealedCellKey === key
                const isKnownUnavailable = Boolean(completionReveal) && !isGeneratedCell && (!cell || cell.entries.length === 0)
                const isPending = pendingCell?.row === row && pendingCell.column === column
                return (
                  <td
                    key={key}
                    data-paradigm-cell
                    data-empty-cell={!cell || cell.entries.length === 0 || isConcealedGeneratedCell ? "true" : undefined}
                    data-newly-revealed={isNewlyRevealed ? "true" : undefined}
                  >
                    {cell && cell.entries.length > 0 && !isConcealedGeneratedCell ? (
                      <ParadigmCellEntries entries={cell.entries} {...pronunciationProps} />
                    ) : (
                      <ParadigmMissingCell
                        {...coordinate}
                        isLoading={isPending}
                        isLocked={isKnownUnavailable || (!isConcealedGeneratedCell && (!isCompletionAvailable || !onCompleteVariations))}
                        isTemporarilyDisabled={Boolean(pendingCell) || isCompletingVariations}
                        lockedReason={isKnownUnavailable ? "This form is unavailable" : completionUnavailableReason}
                        onReveal={() => {
                          if (isConcealedGeneratedCell) {
                            revealGeneratedCell(key)
                            return
                          }
                          void generateFromCell(coordinate)
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
  return coordinateKey(cell)
}

function coordinateKey(coordinate: ParadigmCellCoordinate): string {
  return `${coordinate.row}-${coordinate.column}`
}
