import type { UseAppSectionPropsParams } from "@/app/hooks/app/use-app-section-props"
import { buildDeveloperSectionProps } from "@/app/hooks/app/controller/build-developer-section-props"
import { buildPlaygroundSectionProps } from "@/app/hooks/app/controller/build-playground-section-props"
import { buildWordbankSectionProps } from "@/app/hooks/app/controller/build-wordbank-section-props"
import type { DeveloperContext, PlaygroundContext, WordbankContext } from "@/app/hooks/app/controller/section-props-types"

type BuildAppSectionPropsParamsArgs = {
  playgroundContext: PlaygroundContext
  wordbankContext: WordbankContext
  developerContext: DeveloperContext
}

export function buildAppSectionPropsParams(args: BuildAppSectionPropsParamsArgs): UseAppSectionPropsParams {
  return {
    ...buildPlaygroundSectionProps(args.playgroundContext),
    ...buildWordbankSectionProps(args.wordbankContext),
    ...buildDeveloperSectionProps(args.developerContext),
  }
}
