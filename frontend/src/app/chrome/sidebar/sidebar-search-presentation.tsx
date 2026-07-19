import { ChevronDown, Eye, Plus } from "lucide-react"
import type { ReactNode } from "react"

import type { SearchLanguageMode } from "@/app/chrome/sidebar/sidebar-search-types"
import { Button } from "@/components/ui/button"
import { CommandGroup } from "@/components/ui/command"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"

type SearchMaterial = "word" | "discovery" | "sentence" | "reference"

type SearchSectionProps = {
  heading: string
  material: SearchMaterial
  children: ReactNode
  className?: string
}

export function SearchSection({
  heading,
  material,
  children,
  className,
}: SearchSectionProps) {
  return (
    <CommandGroup
      heading={heading}
      data-search-section
      data-search-material={material}
      className={className}
    >
      {children}
    </CommandGroup>
  )
}

type SearchFolioControlsProps = {
  searchLanguageMode: SearchLanguageMode
  onLanguageModeChange: (mode: SearchLanguageMode) => void
  onCloseSearch: () => void
  children: ReactNode
}

export function SearchFolioControls({
  searchLanguageMode,
  onLanguageModeChange,
  onCloseSearch,
  children,
}: SearchFolioControlsProps) {
  return (
    <div
      data-search-folio-controls
      className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2 px-4 pt-3 pb-[calc(1rem+env(safe-area-inset-bottom))] md:grid-cols-[minmax(0,1fr)_auto] md:px-5 md:pt-4 md:pb-2"
    >
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label="Close search"
        className="shrink-0 rounded-full md:hidden"
        onClick={onCloseSearch}
      >
        <ChevronDown />
      </Button>
      <div
        data-search-input-cell
        className="col-span-3 col-start-1 row-start-2 min-w-0 md:col-span-1 md:col-start-1 md:row-start-1"
      >
        {children}
      </div>
      <ToggleGroup
        type="single"
        value={searchLanguageMode}
        onValueChange={(value) => {
          if (value === "da" || value === "en") {
            onLanguageModeChange(value)
          }
        }}
        aria-label="Search language"
        variant="default"
        size="sm"
        spacing={1}
        className="col-start-3 row-start-1 ml-auto md:col-start-2"
        data-search-language-toggle
      >
        <ToggleGroupItem value="da" aria-label="Search in Danish">
          Dansk
        </ToggleGroupItem>
        <ToggleGroupItem value="en" aria-label="Search in English">
          English
        </ToggleGroupItem>
      </ToggleGroup>
    </div>
  )
}

type SearchResultActionProps = {
  kind: "open" | "add" | "add-form"
  muted?: boolean
  iconTestId?: string
}

export function SearchResultAction({
  kind,
  muted = false,
  iconTestId,
}: SearchResultActionProps) {
  const label = kind === "open" ? "Open" : kind === "add-form" ? "Add form" : "Add"
  const Icon = kind === "open" ? Eye : Plus

  return (
    <span
      data-search-result-action
      className={muted ? "text-muted-foreground/45" : "text-muted-foreground"}
    >
      <span>{label}</span>
      <Icon aria-hidden data-testid={iconTestId} />
    </span>
  )
}
