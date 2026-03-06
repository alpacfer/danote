import type { UseAppSectionPropsParams } from "@/app/hooks/app/use-app-section-props"
import type { PlaygroundContext } from "@/app/hooks/app/controller/section-props-types"

export function buildPlaygroundSectionProps(
  context: PlaygroundContext,
): Pick<UseAppSectionPropsParams, "autosaveStatus" | "playgroundProps" | "savedNotes" | "openSavedNoteInPlayground"> {
  return {
    autosaveStatus: context.autosaveStatus,
    playgroundProps: context.playgroundProps,
    savedNotes: context.savedNotes,
    openSavedNoteInPlayground: context.openSavedNoteInPlayground,
  }
}
