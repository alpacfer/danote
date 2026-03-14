import type { VerificationOverview, VerificationTargetView } from "@/app/core"
import {
  getVerificationViewState,
  verificationActionSummary,
  verificationActionTitle,
  verificationBadgeLabel,
  verificationBadgeVariant,
  verificationCountsSummary,
  verificationHeadline,
  verificationProgressLabel,
  verificationSummary,
  verificationTargetState,
  verificationTargetSummary,
  verificationTargetTimestampMeta,
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
  verificationOverview: VerificationOverview
  isApplyingVerificationChanges: boolean
  onApplyVerificationAction: (targetKey: string, actionIndex: number) => void
}

export function WordbankVerificationPopover({
  verificationOverview,
  isApplyingVerificationChanges,
  onApplyVerificationAction,
}: WordbankVerificationPopoverProps) {
  const viewState = getVerificationViewState(verificationOverview)
  const providerLabel = verificationOverview.targets.find((target) => target.verification?.provider)?.verification?.provider ?? "gemini"

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
          {verificationOverview.totalSuggestedActions > 0 ? (
            <span className="text-[11px] leading-none">{verificationOverview.totalSuggestedActions}</span>
          ) : null}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="h-[32rem] max-h-[70vh] w-[28rem] overflow-y-auto overscroll-contain space-y-3">
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
                  {verificationSummary(verificationOverview, viewState)}
                </p>
              </div>
            </div>
            <Separator />
            <div className="space-y-2 text-sm">
              <VerificationMetaRow
                label="Progress"
                value={verificationProgressLabel(verificationOverview, viewState)}
              />
              <VerificationMetaRow
                label="Targets"
                value={verificationCountsSummary(verificationOverview)}
              />
            </div>
          </CardContent>
        </Card>

        {verificationOverview.targets.length > 0 ? (
          <div className="space-y-2">
            {verificationOverview.targets.map((target) => (
              <VerificationTargetCard
                key={target.key}
                target={target}
                isApplyingVerificationChanges={isApplyingVerificationChanges}
                onApplyVerificationAction={onApplyVerificationAction}
              />
            ))}
          </div>
        ) : (
          <p className="text-muted-foreground text-sm">
            Verification details, progress, and suggested changes will appear here after Gemini processes this word page.
          </p>
        )}
      </PopoverContent>
    </Popover>
  )
}

function VerificationTargetCard({
  target,
  isApplyingVerificationChanges,
  onApplyVerificationAction,
}: {
  target: VerificationTargetView
  isApplyingVerificationChanges: boolean
  onApplyVerificationAction: (targetKey: string, actionIndex: number) => void
}) {
  const state = verificationTargetState(target)
  const timestampMeta = verificationTargetTimestampMeta(target)

  return (
    <Card className="gap-3 py-3 shadow-none">
      <CardContent className="space-y-3 px-3">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <p className="text-sm font-medium">{target.label}</p>
            <p className="text-muted-foreground text-xs">{target.scopeLabel}</p>
          </div>
          <Badge variant={verificationBadgeVariant(state)}>{verificationBadgeLabel(state)}</Badge>
        </div>
        <p className="text-muted-foreground text-sm">{verificationTargetSummary(target)}</p>
        <div className="space-y-2 text-sm">
          <VerificationMetaRow label="Progress" value={verificationBadgeLabel(state)} />
          <VerificationMetaRow label={timestampMeta.label} value={timestampMeta.value} />
        </div>
        {target.errorDetail ? (
          <>
            <Separator />
            <div className="space-y-1">
              <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">Problem</p>
              <p className="text-sm">{target.errorDetail.problem}</p>
            </div>
            <div className="space-y-1">
              <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">Change to implement</p>
              <p className="text-sm">{target.errorDetail.changeToImplement}</p>
            </div>
            {target.errorDetail.suggestedActions.length > 0 ? (
              <div className="space-y-2">
                <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">Apply changes</p>
                {target.errorDetail.suggestedActions.map((action, index) => (
                  <Card key={`${target.key}-${action.action_type}-${index}`} className="gap-3 py-3 shadow-none">
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
                          onClick={() => onApplyVerificationAction(target.key, index)}
                        >
                          {isApplyingVerificationChanges ? "Applying..." : "Apply change"}
                        </Button>
                      </ButtonGroup>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : null}
          </>
        ) : null}
      </CardContent>
    </Card>
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
