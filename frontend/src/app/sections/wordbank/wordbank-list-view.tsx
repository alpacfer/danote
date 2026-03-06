import type { WordbankSectionProps } from "@/app/sections/wordbank/wordbank-section-types"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"

type WordbankListViewProps = Pick<
  WordbankSectionProps,
  "wordbankError" | "isWordbankLoading" | "lemmas" | "groupedWordbankLemmas" | "onSelectLemma"
>

export function WordbankListView({
  wordbankError,
  isWordbankLoading,
  lemmas,
  groupedWordbankLemmas,
  onSelectLemma,
}: WordbankListViewProps) {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      {wordbankError ? (
        <p className="text-destructive text-sm" role="alert">
          {wordbankError}
        </p>
      ) : null}
      {isWordbankLoading && lemmas.length === 0 ? (
        <div className="space-y-4">
          <div className="space-y-2">
            <Skeleton className="h-3 w-4" />
            <div className="flex flex-wrap gap-2">
              <Skeleton className="h-8 w-16 rounded-md" />
              <Skeleton className="h-8 w-20 rounded-md" />
              <Skeleton className="h-8 w-14 rounded-md" />
              <Skeleton className="h-8 w-24 rounded-md" />
            </div>
          </div>
          <div className="space-y-2">
            <Skeleton className="h-3 w-4" />
            <div className="flex flex-wrap gap-2">
              <Skeleton className="h-8 w-[4.5rem] rounded-md" />
              <Skeleton className="h-8 w-12 rounded-md" />
              <Skeleton className="h-8 w-[5.5rem] rounded-md" />
            </div>
          </div>
          <div className="space-y-2">
            <Skeleton className="h-3 w-4" />
            <div className="flex flex-wrap gap-2">
              <Skeleton className="h-8 w-[3.75rem] rounded-md" />
              <Skeleton className="h-8 w-[4.75rem] rounded-md" />
              <Skeleton className="h-8 w-[2.75rem] rounded-md" />
              <Skeleton className="h-8 w-[4.25rem] rounded-md" />
            </div>
          </div>
        </div>
      ) : lemmas.length === 0 ? (
        <p className="text-muted-foreground text-sm">No saved lemmas yet.</p>
      ) : (
        <ScrollArea className="min-h-0 flex-1">
          <div className="space-y-4">
            {groupedWordbankLemmas.map((group) => (
              <section key={group.letter} className="space-y-2">
                <h3 className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">{group.letter}</h3>
                <div className="flex flex-wrap gap-2">
                  {group.items.map((lemma) => (
                    <Button
                      key={lemma.lemma}
                      type="button"
                      variant="outline"
                      size="sm"
                      className="w-auto"
                      onClick={() => onSelectLemma(lemma.lemma)}
                    >
                      {lemma.display_lemma?.trim() || lemma.lemma}
                    </Button>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </ScrollArea>
      )}
    </div>
  )
}
