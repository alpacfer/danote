import { Button } from "@/components/ui/button"

type DatabaseTabProps = {
  isResettingDatabase: boolean
  isSeedingNumbersAudio: boolean
  isSeedingPresavedWordsAudio: boolean
  isRegeneratingPresavedWordsAudio: boolean
  onResetDatabase: () => void
  onSeedNumbersAudio: () => void
  onSeedPresavedWordsAudio: () => void
  onRegeneratePresavedWordsAudio: () => void
}

export function DatabaseTab({
  isResettingDatabase,
  isSeedingNumbersAudio,
  isSeedingPresavedWordsAudio,
  isRegeneratingPresavedWordsAudio,
  onResetDatabase,
  onSeedNumbersAudio,
  onSeedPresavedWordsAudio,
  onRegeneratePresavedWordsAudio,
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
        <p className="text-sm font-medium">Presaved word audio</p>
        <p className="text-muted-foreground text-xs">
          Generates and stores TTS audio for every term shown on a pinned reference page —
          pronouns, question words, articles & gender examples, prepositions, conjunctions,
          days/months/seasons, ordinal numbers, and frequency adverbs. Uses the Azure Speech
          key configured in API Keys.
        </p>
        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={isSeedingPresavedWordsAudio || isRegeneratingPresavedWordsAudio}
            onClick={onSeedPresavedWordsAudio}
          >
            {isSeedingPresavedWordsAudio ? "Generating..." : "Generate missing"}
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={isSeedingPresavedWordsAudio || isRegeneratingPresavedWordsAudio}
            onClick={onRegeneratePresavedWordsAudio}
          >
            {isRegeneratingPresavedWordsAudio ? "Regenerating..." : "Regenerate all"}
          </Button>
        </div>
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
