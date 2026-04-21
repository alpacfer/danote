import { Eye } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { CommandItem } from "@/components/ui/command"
import { Skeleton } from "@/components/ui/skeleton"
import { posBadgeClass, type ENPosGroup } from "@/app/core"

type SidebarEnResultsProps = {
  enPosGroups: ENPosGroup[]
  originalQuery: string
  isLoading?: boolean
  onCloseSearch: () => void
}

export function SidebarEnResults({ enPosGroups, originalQuery, isLoading = false, onCloseSearch }: SidebarEnResultsProps) {
  return (
    <>
      {enPosGroups.map((group) => {
        const displayWord = group.danish_translation ?? ""
        if (!displayWord) {
          return null
        }
        const key = `${displayWord.toLowerCase()}-${group.pos_ud}`
        const topSense = group.senses[0]
        return (
          <CommandItem
            key={`search-en-${key}`}
            value={`en-${key}`}
            onSelect={() => {
              onCloseSearch()
            }}
            className="flex items-start justify-between gap-3"
          >
            <div className="flex min-w-0 flex-col items-start gap-0.5">
              <span>
                <strong className="font-semibold">{displayWord}</strong>
                <span className="text-muted-foreground text-xs">
                  {" "}from <em>{displayWord}</em> ({originalQuery})
                </span>
              </span>
              {isLoading ? (
                <Skeleton className="h-3 w-36" />
              ) : topSense ? (
                <span className="text-muted-foreground text-xs leading-4 line-clamp-2">
                  {topSense.gloss}
                </span>
              ) : null}
              {!isLoading && group.senses.length > 1 ? (
                <span className="text-muted-foreground text-[11px] leading-4">
                  +{group.senses.length - 1} more sense{group.senses.length > 2 ? "s" : ""}
                </span>
              ) : null}
              <div className="mt-1 flex flex-wrap gap-1.5">
                <Badge
                  variant="default"
                  className={`text-xs border ${posBadgeClass(group.pos_ud)}`}
                >
                  {group.pos_ud}
                </Badge>
              </div>
            </div>
            <Eye className="text-muted-foreground size-4 shrink-0" />
          </CommandItem>
        )
      })}
    </>
  )
}
