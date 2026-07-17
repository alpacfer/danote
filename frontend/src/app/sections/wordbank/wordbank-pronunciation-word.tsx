import { Fragment, type ReactNode, useEffect, useRef, useState } from "react"
import { normalizeSearchWord } from "@/app/core"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import { Volume2 } from "lucide-react"
import { cn } from "@/lib/utils"

export type WordbankPronunciationContextMenuItem = {
  icon?: ReactNode
  label: string
  disabled?: boolean
  separatorBefore?: boolean
  onSelect: () => void
}

type WordbankPronunciationWordProps = {
  form: string
  playForm?: string
  hasPronunciation: boolean
  pronunciationLoadingByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  contextMenuItems?: WordbankPronunciationContextMenuItem[]
  children?: ReactNode
  className?: string
  iconClassName?: string
  as?: "h2" | "h3" | "span"
}

export function WordbankPronunciationWord({
  form,
  playForm,
  hasPronunciation,
  pronunciationLoadingByForm,
  onPlayPronunciation,
  contextMenuItems,
  children,
  className,
  iconClassName,
  as: Wrapper,
}: WordbankPronunciationWordProps) {
  const effectivePlayForm = playForm ?? form
  const isLoading = Boolean(pronunciationLoadingByForm[normalizeSearchWord(effectivePlayForm)])
  const isDisabled = isLoading
  const hasContextMenu = Boolean(contextMenuItems && contextMenuItems.length > 0)
  const [isPulsing, setIsPulsing] = useState(false)
  const pulseTimeoutRef = useRef<number | null>(null)

  useEffect(() => () => {
    if (pulseTimeoutRef.current !== null) {
      window.clearTimeout(pulseTimeoutRef.current)
    }
  }, [])

  const play = () => {
    setIsPulsing(false)
    window.requestAnimationFrame(() => setIsPulsing(true))
    if (pulseTimeoutRef.current !== null) {
      window.clearTimeout(pulseTimeoutRef.current)
    }
    pulseTimeoutRef.current = window.setTimeout(() => setIsPulsing(false), 520)
    onPlayPronunciation(effectivePlayForm)
  }

  const button = (
    <button
      type="button"
      aria-label={`Listen to ${form}`}
      disabled={isDisabled}
      onClick={play}
      data-audio-pulse={isPulsing ? "true" : "false"}
      onContextMenu={hasContextMenu ? (event) => {
        event.stopPropagation()
      } : undefined}
      className={cn(
        "danote-audio-trigger relative inline-flex cursor-pointer items-center gap-1.5 rounded-md px-1 -ml-1 outline-none transition-colors",
        "hover:bg-accent/60 focus-visible:ring-ring/50 focus-visible:ring-2",
        "disabled:pointer-events-none disabled:opacity-70",
      )}
    >
      <span className={className}>{children ?? form}</span>
      <Volume2
        className={cn(
          "shrink-0 text-muted-foreground",
          iconClassName ?? "size-3.5",
          isLoading && "animate-pulse",
          !hasPronunciation && "opacity-30",
        )}
      />
    </button>
  )

  const interactiveButton = hasContextMenu ? (
    <ContextMenu>
      <ContextMenuTrigger asChild>{button}</ContextMenuTrigger>
      <ContextMenuContent>
        {contextMenuItems?.map((item) => (
          <Fragment key={`${form}-${item.label}`}>
            {item.separatorBefore ? <ContextMenuSeparator /> : null}
            <ContextMenuItem
              disabled={item.disabled}
              onSelect={item.onSelect}
            >
              {item.icon}
              {item.label}
            </ContextMenuItem>
          </Fragment>
        ))}
      </ContextMenuContent>
    </ContextMenu>
  ) : (
    button
  )

  if (Wrapper) {
    return <Wrapper className="inline-flex min-h-8 items-center">{interactiveButton}</Wrapper>
  }

  return interactiveButton
}
