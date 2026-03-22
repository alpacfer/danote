import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"

import { type AppSection } from "@/app/core"

export type AppBreadcrumbProps = {
  activeSection: AppSection
  selectedLemma: string | null
  activeNoteName: string | null
  onSelectWordbank: () => void
}

export function AppBreadcrumb({
  activeSection,
  selectedLemma,
  activeNoteName,
  onSelectWordbank,
}: AppBreadcrumbProps) {
  if (activeSection === "playground") {
    return (
      <Breadcrumb>
        <BreadcrumbList className="text-2xl leading-[1.1] font-semibold tracking-tight">
          <BreadcrumbItem>
            <BreadcrumbPage>{activeNoteName?.trim() || "Playground"}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    )
  }

  if (activeSection === "developer") {
    return (
      <Breadcrumb>
        <BreadcrumbList className="text-2xl leading-[1.1] font-semibold tracking-tight">
          <BreadcrumbItem>
            <BreadcrumbPage>Developer</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    )
  }

  if (activeSection === "notes") {
    return (
      <Breadcrumb>
        <BreadcrumbList className="text-2xl leading-[1.1] font-semibold tracking-tight">
          <BreadcrumbItem>
            <BreadcrumbPage>Notes</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    )
  }

  if (activeSection === "sentencebank") {
    return (
      <Breadcrumb>
        <BreadcrumbList className="text-2xl leading-[1.1] font-semibold tracking-tight">
          <BreadcrumbItem>
            <BreadcrumbPage>Sentencebank</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    )
  }

  return (
    <Breadcrumb>
      <BreadcrumbList className="text-2xl leading-[1.1] font-semibold tracking-tight">
        <BreadcrumbItem>
          {selectedLemma ? (
            <BreadcrumbLink asChild>
              <button type="button" className="font-semibold" onClick={onSelectWordbank}>
                Wordbank
              </button>
            </BreadcrumbLink>
          ) : (
            <BreadcrumbPage>Wordbank</BreadcrumbPage>
          )}
        </BreadcrumbItem>
        {selectedLemma && (
          <>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>{selectedLemma}</BreadcrumbPage>
            </BreadcrumbItem>
          </>
        )}
      </BreadcrumbList>
    </Breadcrumb>
  )
}
