import { Eye } from "lucide-react"

import { CommandItem } from "@/components/ui/command"
import { Skeleton } from "@/components/ui/skeleton"

export function SidebarSearchPendingSkeleton() {
  return (
    <CommandItem
      disabled
      aria-hidden="true"
      data-testid="search-pending-skeleton"
      data-search-slip
      data-material="discovery"
      className="flex items-start justify-between gap-3"
    >
      <div className="flex min-w-0 flex-col items-start gap-1">
        <Skeleton className="h-3.5 w-28" />
        <Skeleton className="h-3 w-36" />
        <div className="mt-1 flex flex-wrap gap-1.5">
          <Skeleton className="h-5 w-10 rounded-full" />
          <Skeleton className="h-5 w-14 rounded-full" />
        </div>
      </div>
      <Eye className="text-muted-foreground size-4 shrink-0 opacity-0" aria-hidden />
    </CommandItem>
  )
}

export function SidebarSearchEnSkeletons({ count }: { count: number }) {
  return (
    <>
      {Array.from({ length: count }, (_, i) => (
        <CommandItem
          key={`en-skeleton-${i}`}
          disabled
          aria-hidden="true"
          data-testid="search-en-skeleton"
          data-search-slip
          data-material="discovery"
          className="flex items-start justify-between gap-3"
        >
          <div className="flex min-w-0 flex-col items-start gap-0.5">
            <Skeleton className="h-3.5 w-24" />
            <Skeleton className="h-3 w-36" />
            <div className="mt-1 flex flex-wrap gap-1.5">
              <Skeleton className="h-5 w-10 rounded-full" />
            </div>
          </div>
          <Eye className="text-muted-foreground size-4 shrink-0 opacity-0" aria-hidden />
        </CommandItem>
      ))}
    </>
  )
}
