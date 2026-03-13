import type { VerificationErrorDetail, VerificationQueuedDetail, VerificationSuccessDetail } from "@/app/core"
import {
  getVerificationTimestampMeta,
  getVerificationViewState,
  verificationActionSummary,
  verificationActionTitle,
  verificationBadgeLabel,
  verificationBadgeVariant,
  verificationHeadline,
  verificationProgressLabel,
  verificationSummary,
  verificationTriggerLabel,
  type WordbankVerificationViewState,
} from "@/app/sections/wordbank/wordbank-verification-view"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import { Card, CardContent } from "@/components/ui/card"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Separator } from "@/components/ui/separator"
import { Spinner } from "@/components/ui/spinner"
import { BadgeCheck, CircleAlert, Info } from "lucide-react"

type WordbankVerificationPopoverProps = {
  selectedLemmaVerificationError: VerificationErrorDetail | null
  selectedLemmaVerificationQueued: VerificationQueuedDetail | null
  selectedLemmaVerificationSuccess: VerificationSuccessDetail | null
  selectedVerificationTimestamp: string
  hasSuggestedVerificationActions: (detail: VerificationErrorDetail | null) => boolean
  isApplyingVerificationChanges: boolean
  onApplySelectedLemmaVerificationAction: (actionIndex: number) => void
}

export function WordbankVerificationPopover({
  selectedLemmaVerificationError,
  selectedLemmaVerificationQueued,
  selectedLemmaVerificationSuccess,
  selectedVerificationTimestamp,
  hasSuggestedVerificationActions,
  isApplyingVerificationChanges,
  onApplySelectedLemmaVerificationAction,
}: WordbankVerificationPopoverProps) {
  const viewState = getVerificationViewState({
    selectedLemmaVerificationError,
    selectedLemmaVerificationQueued,
    selectedLemmaVerificationSuccess,
  })
  const providerLabel =
    selectedLemmaVerificationError?.provider
    ?? selectedLemmaVerificationQueued?.provider
    ?? selectedLemmaVerificationSuccess?.provider
    ?? "gemini"
  const timestampMeta = getVerificationTimestampMeta({
    selectedLemmaVerificationError,
    selectedLemmaVerificationQueued,
    selectedLemmaVerificationSuccess,
    selectedVerificationTimestamp,
  })
  const countLabel = selectedLemmaVerificationError?.suggestedActions.length

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="gap-1.5"
          aria-label={verificationTriggerLabel(viewState)}
        >
          <VerificationStateIcon state={viewState} className="size-4" />
          {viewState === "review" && countLabel ? (
            <span className="text-[11px] leading-none">{countLabel}</span>
          ) : null}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-96 space-y-3">
        <div className="space-y-1">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-semibold">Verification</p>
            <Badge variant={verificationBadgeVariant(viewState)}>{verificationBadgeLabel(viewState)}</Badge>
          </div>
          <p className="text-muted-foreground text-xs">Provider: {providerLabel}</p>
        </div>

        <Card className="gap-3 py-3 shadow-none">
          <CardContent className="space-y-3 px-3">
            <div className="flex items-start gap-2">
              <VerificationStateIcon state={viewState} className="mt-0.5 size-4 shrink-0" />
              <div className="space-y-1">
                <p className="text-sm font-medium">{verificationHeadline(viewState)}</p>
                <p className="text-muted-foreground text-sm">
                  {verificationSummary({
                    viewState,
                    selectedLemmaVerificationError,
                    selectedLemmaVerificationQueued,
                    selectedLemmaVerificationSuccess,
                  })}
                </p>
              </div>
            </div>
            <Separator />
            <div className="space-y-2 text-sm">
              <VerificationMetaRow label="Progress" value={verificationProgressLabel(viewState)} />
              <VerificationMetaRow label={timestampMeta.label} value={timestampMeta.value} />
            </div>
          </CardContent>
        </Card>

        {selectedLemmaVerificationError ? (
          <>
            <div className="space-y-1">
              <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">Problem</p>
              <p className="text-sm">{selectedLemmaVerificationError.problem}</p>
            </div>
            <div className="space-y-1">
              <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">Change to implement</p>
              <p className="text-sm">{selectedLemmaVerificationError.changeToImplement}</p>
            </div>
            {hasSuggestedVerificationActions(selectedLemmaVerificationError) ? (
              <div className="space-y-2">
                <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">Apply changes</p>
                <div className="space-y-2">
                  {selectedLemmaVerificationError.suggestedActions.map((action, index) => (
                    <Card key={`${action.action_type}-${index}`} className="gap-3 py-3 shadow-none">
                      <CardContent className="space-y-3 px-3">
                        <div className="space-y-1">
                          <p className="text-sm font-medium">{verificationActionTitle(action)}</p>
                          <p className="text-muted-foreground text-xs">
                            {action.reason?.trim() || verificationActionSummary(action)}
                          </p>
                          {!action.reason?.trim() ? null : (
                            <p className="text-sm">{verificationActionSummary(action)}</p>
                          )}
                        </div>
                        <ButtonGroup>
                          <Button
                            type="button"
                            size="sm"
                            className="w-full"
                            disabled={isApplyingVerificationChanges}
                            onClick={() => onApplySelectedLemmaVerificationAction(index)}
                          >
                            {isApplyingVerificationChanges ? "Applying..." : "Apply change"}
                          </Button>
                        </ButtonGroup>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ) : null}
          </>
        ) : null}
      </PopoverContent>
    </Popover>
  )
}

function VerificationStateIcon({
  state,
  className,
}: {
  state: WordbankVerificationViewState
  className?: string
}) {
  if (state === "queued") {
    return <Spinner className={className} />
  }
  if (state === "verified") {
    return <BadgeCheck className={className} />
  }
  if (state === "review") {
    return <CircleAlert className={className} />
  }
  return <Info className={className} />
}

function VerificationMetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">{label}</p>
      <p className="text-right text-sm">{value}</p>
    </div>
  )
}
