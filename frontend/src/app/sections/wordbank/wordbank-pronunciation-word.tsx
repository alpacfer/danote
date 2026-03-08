import { normalizeSearchWord } from "@/app/core"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Volume2 } from "lucide-react"
import { cn } from "@/lib/utils"

type WordbankPronunciationWordProps = {
  form: string
  playForm?: string
  hasPronunciation: boolean
  pronunciationLoadingByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  className?: string
  iconClassName?: string
  as?: "h2" | "span"
}

export function WordbankPronunciationWord({
  form,
  playForm,
  hasPronunciation,
  pronunciationLoadingByForm,
  onPlayPronunciation,
  className,
  iconClassName,
  as: Wrapper,
}: WordbankPronunciationWordProps) {
  const effectivePlayForm = playForm ?? form
  const isLoading = Boolean(pronunciationLoadingByForm[normalizeSearchWord(effectivePlayForm)])
  const isDisabled = !hasPronunciation || isLoading

  const button = (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          aria-label={`Listen to ${form}`}
          disabled={isDisabled}
          onClick={() => onPlayPronunciation(effectivePlayForm)}
          className={cn(
            "inline-flex cursor-pointer items-center gap-1.5 rounded-md px-1 -ml-1 outline-none transition-colors",
            "hover:bg-accent/60 focus-visible:ring-ring/50 focus-visible:ring-2",
            "disabled:pointer-events-none disabled:opacity-70",
          )}
        >
          <span className={className}>{form}</span>
          <Volume2
            className={cn(
              "shrink-0 text-muted-foreground",
              iconClassName ?? "size-3.5",
              isLoading && "animate-pulse",
              !hasPronunciation && "opacity-30",
            )}
          />
        </button>
      </TooltipTrigger>
      <TooltipContent side="bottom" sideOffset={4}><p>Click to listen</p></TooltipContent>
    </Tooltip>
  )

  if (Wrapper) {
    return <Wrapper className="inline">{button}</Wrapper>
  }

  return button
}
