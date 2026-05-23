import { Button } from "@/components/ui/button"

type DatabaseTabProps = {
  isResettingDatabase: boolean
  isSeedingNumbersAudio: boolean
  isSeedingPresavedWordsAudio: boolean
  isRegeneratingPresavedWordsAudio: boolean
  onResetDatabase: () => void
  onSeedPresavedWordsAudio: () => void
  onRegeneratePresavedWordsAudio: () => void
}

export function DatabaseTab({
  isResettingDatabase,
  isSeedingNumbersAudio,
  isSeedingPresavedWordsAudio,
  isRegeneratingPresavedWordsAudio,
  onResetDatabase,
  onSeedPresavedWordsAudio,
  onRegeneratePresavedWordsAudio,
}: DatabaseTabProps) {
  const isSeedingPinnedAudio = isSeedingNumbersAudio || isSeedingPresavedWordsAudio
  const isRegeneratingPinnedAudio = isSeedingNumbersAudio || isRegeneratingPresavedWordsAudio

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <p className="text-sm font-medium">Pinned word audio</p>
        <p className="text-muted-foreground text-xs">
          Generates and stores TTS audio for every word shown on a pinned page, including numbers.
          Uses the Azure Speech key configured in API Keys.
        </p>
        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={isSeedingPinnedAudio || isRegeneratingPinnedAudio}
            onClick={onSeedPresavedWordsAudio}
          >
            {isSeedingPinnedAudio ? "Generating..." : "Generate missing"}
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={isSeedingPinnedAudio || isRegeneratingPinnedAudio}
            onClick={onRegeneratePresavedWordsAudio}
          >
            {isRegeneratingPinnedAudio ? "Regenerating..." : "Regenerate all"}
          </Button>
        </div>
      </div>

      <div className="space-y-4">
        <p className="text-sm font-medium">Reset database and cache</p>
        <p className="text-muted-foreground text-xs">
          Deletes your saved words, sentences, and custom categories, then restores the standard
          categories. Browser storage (localStorage, sessionStorage, service workers, Cache API)
          is also cleared. API keys are preserved. This cannot be undone.
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
