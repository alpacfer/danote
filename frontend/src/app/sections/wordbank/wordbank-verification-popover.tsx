import type { ReactNode } from "react"

import type { VerificationOverview, VerificationTargetView } from "@/app/core"
import {
  getVerificationViewState,
  groupVerificationTargets,
  latestVerifiedTimestamp,
  verificationActionButtonLabel,
  verificationActionSummary,
  verificationBadgeLabel,
  verificationBadgeVariant,
  verificationReviewPrimaryCopy,
  verificationReviewSupportingCopy,
  verificationSummary,
  verificationTargetTimestampMeta,
  verificationTriggerLabel,
  type WordbankVerificationViewState,
} from "@/app/sections/wordbank/wordbank-verification-view"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Spinner } from "@/components/ui/spinner"
import { BadgeCheck, CircleAlert, Info } from "lucide-react"

type WordbankVerificationPopoverProps = {
  verificationOverview: VerificationOverview
  isApplyingVerificationChanges: boolean
  isRetryingVerification: boolean
  onOpenChange?: (open: boolean) => void
  onApplyVerificationAction: (targetKey: string, actionIndex: number) => void
  onRetryVerificationTarget: (targetKey: string) => void
}

export function WordbankVerificationPopover({
  verificationOverview,
  isApplyingVerificationChanges,
  isRetryingVerification,
  onOpenChange,
  onApplyVerificationAction,
  onRetryVerificationTarget,
}: WordbankVerificationPopoverProps) {
  const viewState = getVerificationViewState(verificationOverview)
  const providerLabel = verificationOverview.targets.find((target) => target.verification?.provider)?.verification?.provider ?? "gemini"
  const { reviewTargets, queuedTargets, verifiedTargets } = groupVerificationTargets(verificationOverview)
  const latestVerifiedAt = latestVerifiedTimestamp(verifiedTargets)
  const verifiedSummary = verifiedTargets.length === verificationOverview.targets.length && verifiedTargets.length > 0
    ? "All visible targets look correct."
    : `${verifiedTargets.length} checked ${verifiedTargets.length === 1 ? "item" : "items"}.`

  return (
    <Popover onOpenChange={onOpenChange}>
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
      <PopoverContent
        align="end"
        data-testid="wordbank-verification-popover"
        className="flex max-h-[min(70vh,var(--radix-popover-content-available-height))] w-[28rem] max-w-[calc(100vw-1rem)] flex-col overflow-hidden p-0"
      >
        <div className="space-y-1 border-b px-4 py-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-semibold">Verification</p>
            <Badge variant={verificationBadgeVariant(viewState)}>{verificationBadgeLabel(viewState)}</Badge>
          </div>
          <p className="text-muted-foreground text-sm">{verificationSummary(verificationOverview, viewState)}</p>
        </div>
        <ScrollArea
          data-testid="wordbank-verification-scroll-area"
          className="min-h-0 flex-1 overscroll-contain"
        >
          <div className="space-y-3 px-4 py-3">
            {verificationOverview.targets.length > 0 ? (
              <>
                {reviewTargets.length > 0 ? (
                  <VerificationSection label="Needs review" count={reviewTargets.length}>
                    {reviewTargets.map((target) => (
                      <VerificationReviewRow
                        key={target.key}
                        target={target}
                        isApplyingVerificationChanges={isApplyingVerificationChanges}
                        isRetryingVerification={isRetryingVerification}
                        onApplyVerificationAction={onApplyVerificationAction}
                        onRetryVerificationTarget={onRetryVerificationTarget}
                      />
                    ))}
                  </VerificationSection>
                ) : null}

                {queuedTargets.length > 0 ? (
                  <VerificationSection label="In progress" count={queuedTargets.length}>
                    {queuedTargets.map((target) => (
                      <VerificationQueuedRow key={target.key} target={target} />
                    ))}
                  </VerificationSection>
                ) : null}

                {verifiedTargets.length > 0 ? (
                  <VerificationSection label="Checked" count={verifiedTargets.length}>
                    <Card variant="subtle">
                      <CardContent className="space-y-2 px-3 py-3">
                        <div className="flex items-start gap-2">
                          <VerificationStateIcon state="verified" className="mt-0.5 size-4 shrink-0" />
                          <div className="space-y-1">
                            <p className="text-sm font-medium">{verifiedSummary}</p>
                            {latestVerifiedAt ? (
                              <p className="text-muted-foreground text-xs">Last checked {latestVerifiedAt}</p>
                            ) : null}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </VerificationSection>
                ) : null}
              </>
            ) : (
              <p className="text-muted-foreground text-sm">
                Verification details, progress, and suggested changes will appear here after Gemini processes this word page.
              </p>
            )}

            {verificationOverview.targets.length > 0 ? (
              <>
                <Separator />
                <p className="text-muted-foreground text-xs">Provider: {providerLabel}</p>
              </>
            ) : null}
          </div>
        </ScrollArea>
      </PopoverContent>
    </Popover>
  )
}

function VerificationSection({
  label,
  count,
  children,
}: {
  label: string
  count: number
  children: ReactNode
}) {
  return (
    <section
      data-testid={`wordbank-verification-section-${label.toLocaleLowerCase("en-US").replace(/\s+/g, "-")}`}
      className="space-y-2"
    >
      <div className="flex items-center justify-between gap-3">
        <p className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">{label}</p>
        <p className="text-muted-foreground text-xs">{count}</p>
      </div>
      <div className="space-y-2">{children}</div>
    </section>
  )
}

function VerificationReviewRow({
  target,
  isApplyingVerificationChanges,
  isRetryingVerification,
  onApplyVerificationAction,
  onRetryVerificationTarget,
}: {
  target: VerificationTargetView
  isApplyingVerificationChanges: boolean
  isRetryingVerification: boolean
  onApplyVerificationAction: (targetKey: string, actionIndex: number) => void
  onRetryVerificationTarget: (targetKey: string) => void
}) {
  const timestampMeta = verificationTargetTimestampMeta(target)
  const supportingCopy = verificationReviewSupportingCopy(target)

  return (
    <Card variant="subtle">
      <CardContent className="space-y-3 px-3 py-3">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <p className="text-sm font-medium">{target.label}</p>
            <p className="text-muted-foreground text-xs">{target.scopeLabel}</p>
          </div>
          <Badge variant={verificationBadgeVariant("review")}>{verificationBadgeLabel("review")}</Badge>
        </div>
        <p className="text-sm">{verificationReviewPrimaryCopy(target)}</p>
        {supportingCopy ? <p className="text-muted-foreground text-sm">{supportingCopy}</p> : null}
        <p className="text-muted-foreground text-xs">{timestampMeta.label}: {timestampMeta.value}</p>
        {target.errorDetail ? (
          <>
            {target.errorDetail.suggestedActions.length > 0 ? (
              <div className="space-y-2">
                {target.errorDetail.suggestedActions.map((action, index) => (
                  <Card
                    key={`${target.key}-${action.action_type}-${index}`}
                    variant="subtle"
                    className="px-3 py-2 border-border/70"
                  >
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <p className="text-muted-foreground text-sm">{verificationActionSummary(action)}</p>
                      <Button
                        type="button"
                        size="sm"
                        className="sm:shrink-0"
                        disabled={isApplyingVerificationChanges}
                        onClick={() => onApplyVerificationAction(target.key, index)}
                      >
                        {isApplyingVerificationChanges ? "Applying..." : verificationActionButtonLabel(action)}
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            ) : null}
            {target.errorDetail.status === "error" ? (
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={isRetryingVerification}
                onClick={() => onRetryVerificationTarget(target.key)}
              >
                {isRetryingVerification ? "Retrying..." : "Retry verification"}
              </Button>
            ) : null}
          </>
        ) : null}
      </CardContent>
    </Card>
  )
}

function VerificationQueuedRow({ target }: { target: VerificationTargetView }) {
  const timestampMeta = verificationTargetTimestampMeta(target)

  return (
    <Card variant="subtle">
      <CardContent className="space-y-2 px-3 py-3">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <p className="text-sm font-medium">{target.label}</p>
            <p className="text-muted-foreground text-xs">{target.scopeLabel}</p>
          </div>
          <Badge variant={verificationBadgeVariant("queued")}>{verificationBadgeLabel("queued")}</Badge>
        </div>
        <p className="text-muted-foreground text-sm">Gemini is still processing this target.</p>
        <p className="text-muted-foreground text-xs">{timestampMeta.label}: {timestampMeta.value}</p>
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
