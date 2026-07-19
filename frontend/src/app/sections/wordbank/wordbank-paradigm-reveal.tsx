import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { Eye, LockKeyhole } from "lucide-react"

export type ParadigmCellCoordinate = {
  row: string
  column: string
}

type ParadigmMissingCellProps = ParadigmCellCoordinate & {
  isLoading: boolean
  isLocked: boolean
  isTemporarilyDisabled: boolean
  lockedReason: string
  onReveal: () => void
}

export function ParadigmMissingCell({
  row,
  column,
  isLoading,
  isLocked,
  isTemporarilyDisabled,
  lockedReason,
  onReveal,
}: ParadigmMissingCellProps) {
  const focusLabel = `${row}, ${column}`
  const isUnavailable = isLocked || isTemporarilyDisabled
  const accessibleLabel = isLocked
    ? lockedReason
    : `Reveal missing forms — focus: ${focusLabel}`

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-xs"
      className="group/paradigm-reveal h-full w-full"
      data-paradigm-reveal
      data-state={isLoading ? "loading" : isLocked ? "locked" : isTemporarilyDisabled ? "disabled" : "idle"}
      aria-label={isLocked ? `${accessibleLabel}: ${focusLabel}` : accessibleLabel}
      aria-disabled={isUnavailable}
      onClick={(event) => {
        if (isUnavailable || isLoading) {
          event.preventDefault()
          return
        }
        onReveal()
      }}
    >
      {isLoading ? (
        <Spinner />
      ) : (
        <>
          <span data-paradigm-reveal-dash aria-hidden="true">—</span>
          {isLocked ? (
            <LockKeyhole data-paradigm-reveal-icon="lock" aria-hidden="true" />
          ) : (
            <Eye data-paradigm-reveal-icon="eye" aria-hidden="true" />
          )}
        </>
      )}
    </Button>
  )
}
