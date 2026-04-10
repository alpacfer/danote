import { Button } from "@/components/ui/button"

type DatabaseTabProps = {
  isResettingDatabase: boolean
  onResetDatabase: () => void
}

export function DatabaseTab({
  isResettingDatabase,
  onResetDatabase,
}: DatabaseTabProps) {
  return (
    <div className="space-y-4">
      <p className="text-sm font-medium">Reset database and cache</p>
      <p className="text-muted-foreground text-xs">
        Deletes the SQLite database and clears all browser storage (localStorage, sessionStorage,
        service workers, Cache API). This cannot be undone.
      </p>
      <Button
        type="button"
        variant="destructive"
        disabled={isResettingDatabase}
        onClick={onResetDatabase}
      >
        {isResettingDatabase ? "Deleting..." : "Delete DB + Clear cache"}
      </Button>
    </div>
  )
}