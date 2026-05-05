import { Button } from "@/components/ui/button"

type DatabaseTabProps = {
  isResettingDatabase: boolean
  isSeedingNumbersAudio: boolean
  onResetDatabase: () => void
  onSeedNumbersAudio: () => void
}

export function DatabaseTab({
  isResettingDatabase,
  isSeedingNumbersAudio,
  onResetDatabase,
  onSeedNumbersAudio,
}: DatabaseTabProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <p className="text-sm font-medium">Number audio</p>
        <p className="text-muted-foreground text-xs">
          Generates and stores TTS audio for all 28 Danish number words (0–90). Uses the Azure
          Speech key configured in API Keys. Already-stored terms are skipped.
        </p>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={isSeedingNumbersAudio}
          onClick={onSeedNumbersAudio}
        >
          {isSeedingNumbersAudio ? "Generating..." : "Seed number audio"}
        </Button>
      </div>

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
    </div>
  )
}
