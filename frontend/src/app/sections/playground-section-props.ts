import { type ComponentProps } from "react"

import { PlaygroundSection } from "@/app/sections/playground-section"

export type PlaygroundSectionAdapterArgs = {
  playgroundProps: ComponentProps<typeof PlaygroundSection>
}

export function buildPlaygroundSectionProps({
  playgroundProps,
}: PlaygroundSectionAdapterArgs): ComponentProps<typeof PlaygroundSection> {
  return playgroundProps
}
