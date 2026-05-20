import { useState } from "react"

import { ChevronRight, Trash2 } from "lucide-react"

import { PINNED_PAGES, type PinnedPageMeta } from "@/app/sections/wordbank/_shared/pinned-pages-registry"
import { LemmaDeletionDialog } from "@/app/sections/wordbank/wordbank-deletion-dialogs"
import type { WordbankSectionProps } from "@/app/sections/wordbank/wordbank-section-types"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"

type WordbankListViewProps = Pick<
  WordbankSectionProps,
  "wordbankError" | "isWordbankLoading" | "lemmas" | "groupedWordbankLemmas" | "unreadWordbankLemmaCounts" | "onSelectLemma"
  | "onDeleteLemma"
>

export function WordbankListView({
  wordbankError,
  isWordbankLoading,
  lemmas,
  groupedWordbankLemmas,
  unreadWordbankLemmaCounts,
  onSelectLemma,
  onDeleteLemma,
}: WordbankListViewProps) {
  const [lemmaToDelete, setLemmaToDelete] = useState<{ lemma: string; displayWord: string } | null>(null)

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
      ) : (
        <ScrollArea className="min-h-0 flex-1">
          <div className="space-y-5">
            <PinnedGroupSection pages={PINNED_PAGES} onSelectLemma={onSelectLemma} />

            {groupedWordbankLemmas.map((group) => (
              <section key={group.letter} className="space-y-2">
                <h3 className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">{group.letter}</h3>
                <div className="flex flex-wrap gap-2">
                  {group.items.map((lemma) => {
                    const displayWord = lemma.display_lemma?.trim() || lemma.lemma
                    const unreadCount = unreadWordbankLemmaCounts.get(lemma.lemma) ?? 0
                    return (
                      <ContextMenu key={lemma.lemma}>
                        <ContextMenuTrigger asChild>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="relative w-auto pr-3"
                            onClick={() => onSelectLemma(lemma.lemma)}
                          >
                            {displayWord}
                            {unreadCount > 0 ? (
                              unreadCount > 1 ? (
                                <span className="bg-primary text-primary-foreground ml-2 inline-flex min-w-5 items-center justify-center rounded-full px-1.5 text-[10px] leading-5">
                                  {unreadCount}
                                </span>
                              ) : (
                                <span
                                  aria-label={`Pending verification for ${displayWord}`}
                                  className="bg-primary ml-2 inline-flex size-2.5 rounded-full"
                                />
                              )
                            ) : null}
                          </Button>
                        </ContextMenuTrigger>
                        <ContextMenuContent>
                          <ContextMenuItem
                            variant="destructive"
                            onSelect={() => setLemmaToDelete({ lemma: lemma.lemma, displayWord })}
                          >
                            <Trash2 />
                            Delete whole lemma
                          </ContextMenuItem>
                        </ContextMenuContent>
                      </ContextMenu>
                    )
                  })}
                </div>
              </section>
            ))}
          </div>
        </ScrollArea>
      )}
      <LemmaDeletionDialog
        lemma={lemmaToDelete}
        onOpenChange={(open) => {
          if (!open) setLemmaToDelete(null)
        }}
        onConfirm={(lemma) => {
          onDeleteLemma(lemma)
          setLemmaToDelete(null)
        }}
      />
    </div>
  )
}

function PinnedGroupSection({
  pages,
  onSelectLemma,
}: {
  pages: PinnedPageMeta[]
  onSelectLemma: (lemma: string) => void
}) {
  return (
    <section className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {pages.map((page) => (
          <BuiltInReferenceCard
            key={page.sentinel}
            label={page.title}
            ariaLabel={`Open ${page.title} reference`}
            onClick={() => onSelectLemma(page.sentinel)}
          />
        ))}
      </div>
    </section>
  )
}

function BuiltInReferenceCard({
  label,
  ariaLabel,
  onClick,
}: {
  label: string
  ariaLabel: string
  onClick: () => void
}) {
  return (
    <Card className="overflow-hidden py-0 gap-0">
      <CardContent className="p-0">
        <Button
          type="button"
          variant="ghost"
          className="hover:bg-accent/60 h-auto w-auto items-center justify-between gap-3 rounded-none px-4 py-3 text-left"
          onClick={onClick}
          aria-label={ariaLabel}
        >
          <span className="text-sm font-semibold">{label}</span>
          <ChevronRight className="text-muted-foreground size-4 shrink-0" />
        </Button>
      </CardContent>
    </Card>
  )
}
