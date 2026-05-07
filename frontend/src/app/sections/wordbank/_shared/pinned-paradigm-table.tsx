import type { ReactNode } from "react"

import { WordbankPronunciationWord } from "@/app/sections/wordbank/wordbank-pronunciation-word"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

export type ParadigmCell =
  | { type: "lemma"; lemma: string; tooltip?: string | null; muted?: boolean }
  | { type: "label"; text: string }
  | { type: "text"; text: ReactNode; muted?: boolean; italic?: boolean }
  | { type: "empty" }

export type ParadigmRow = {
  key: string
  cells: ParadigmCell[]
}

type PinnedParadigmTableProps = {
  headers: Array<string | null>
  rows: ParadigmRow[]
  pronunciationLoadingByForm?: Record<string, boolean>
  onPlayPronunciation?: (form: string) => void
  className?: string
}

export function PinnedParadigmTable({
  headers,
  rows,
  pronunciationLoadingByForm,
  onPlayPronunciation,
  className,
}: PinnedParadigmTableProps) {
  return (
    <Table className={className}>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          {headers.map((header, index) => (
            <TableHead
              key={`h-${index}`}
              className="text-muted-foreground text-[11px] font-semibold uppercase tracking-wide"
            >
              {header ?? ""}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.key} className="hover:bg-transparent">
            {row.cells.map((cell, cellIndex) => (
              <TableCell key={`${row.key}-${cellIndex}`} className="align-top">
                <ParadigmCellContent
                  cell={cell}
                  pronunciationLoadingByForm={pronunciationLoadingByForm}
                  onPlayPronunciation={onPlayPronunciation}
                />
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function ParadigmCellContent({
  cell,
  pronunciationLoadingByForm,
  onPlayPronunciation,
}: {
  cell: ParadigmCell
  pronunciationLoadingByForm?: Record<string, boolean>
  onPlayPronunciation?: (form: string) => void
}) {
  if (cell.type === "empty") {
    return <span className="text-muted-foreground/40 text-sm">—</span>
  }
  if (cell.type === "label") {
    return (
      <span className="text-muted-foreground whitespace-nowrap pr-3 text-xs font-medium">
        {cell.text}
      </span>
    )
  }
  if (cell.type === "text") {
    return (
      <span
        className={cn(
          "text-sm",
          cell.muted && "text-muted-foreground",
          cell.italic && "italic",
        )}
      >
        {cell.text}
      </span>
    )
  }
  const lemmaContent = (
    <span
      className={cn(
        "text-foreground rounded px-1.5 py-0.5 text-sm font-semibold",
        cell.muted && "text-muted-foreground",
      )}
    >
      {pronunciationLoadingByForm && onPlayPronunciation ? (
        <WordbankPronunciationWord
          form={cell.lemma}
          hasPronunciation={true}
          pronunciationLoadingByForm={pronunciationLoadingByForm}
          onPlayPronunciation={onPlayPronunciation}
          className="text-sm font-semibold"
        />
      ) : (
        cell.lemma
      )}
    </span>
  )
  if (!cell.tooltip) {
    return lemmaContent
  }
  return (
    <Tooltip>
      <TooltipTrigger asChild>{lemmaContent}</TooltipTrigger>
      <TooltipContent side="right" sideOffset={8}>
        <p>{cell.tooltip}</p>
      </TooltipContent>
    </Tooltip>
  )
}
