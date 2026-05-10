import { pinnedHomesForLemma } from "@/app/sections/wordbank/_shared/pinned-word-index"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type PinnedWordHomeCardProps = {
  lemma: string
  onOpenPinnedTab: (sentinel: string) => void
}

export function PinnedWordHomeCard({ lemma, onOpenPinnedTab }: PinnedWordHomeCardProps) {
  const homes = pinnedHomesForLemma(lemma)
  if (homes.length === 0) {
    return null
  }

  return (
    <Card data-testid="wordbank-pinned-home-card" className="w-full py-4 xl:w-1/2">
      <CardHeader>
        <CardTitle className="text-sm">Pinned section</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        {homes.map((home) => (
          <Button
            key={home.sentinel}
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenPinnedTab(home.sentinel)}
          >
            {home.pageTitle}: {home.tabTitle}
          </Button>
        ))}
      </CardContent>
    </Card>
  )
}
