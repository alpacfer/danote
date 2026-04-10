import { Bell, LoaderCircle, Save } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import { Card } from "@/components/ui/card"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import {
  formatSavedNoteTimestamp,
  type AppNotification,
} from "@/app/core"

export type PlaygroundHeaderActionsProps = {
  autosaveStatusLabel: string
  hasActiveSavedNote: boolean
  isNotificationsOpen: boolean
  isVerifyingWords: boolean
  hasUnreadNotifications: boolean
  unreadCount: number
  notifications: AppNotification[]
  onOpenSaveDialog: () => void
  onNotificationsOpenChange: (open: boolean) => void
}

export function PlaygroundHeaderActions({
  autosaveStatusLabel,
  hasActiveSavedNote,
  isNotificationsOpen,
  isVerifyingWords,
  hasUnreadNotifications,
  unreadCount,
  notifications,
  onOpenSaveDialog,
  onNotificationsOpenChange,
}: PlaygroundHeaderActionsProps) {
  return (
    <div className="flex items-center gap-2">
      <p className="text-muted-foreground text-xs" aria-label="note-autosave-status">
        {autosaveStatusLabel}
      </p>
      <ButtonGroup>
        <ButtonGroup>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="gap-1.5"
            onClick={onOpenSaveDialog}
          >
            <Save className="size-3.5" />
            {hasActiveSavedNote ? "Create new note" : "Save note"}
          </Button>
        </ButtonGroup>
        <ButtonGroup>
          <Popover
            open={isNotificationsOpen}
            onOpenChange={onNotificationsOpenChange}
          >
            <PopoverTrigger asChild>
              <Button
                type="button"
                size="sm"
                variant={hasUnreadNotifications ? "default" : "outline"}
                className="gap-1.5"
                aria-label={
                  isVerifyingWords
                    ? "Word verification is running"
                    : hasUnreadNotifications
                    ? `Show notifications (${unreadCount} unread)`
                    : "No unread notifications"
                }
                disabled={!hasUnreadNotifications && !isVerifyingWords}
              >
                {isVerifyingWords ? <LoaderCircle className="size-3.5 animate-spin" /> : <Bell className="size-3.5" />}
                {hasUnreadNotifications ? (
                  <span className="text-[11px] leading-none">{unreadCount}</span>
                ) : null}
              </Button>
            </PopoverTrigger>
            <PopoverContent align="end" className="w-80 space-y-2">
              <p className="text-sm font-medium">Notifications</p>
              {notifications.length === 0 ? (
                <p className="text-muted-foreground text-xs">No notifications yet.</p>
              ) : (
                <ul className="space-y-2" aria-label="notification-list">
                  {notifications.map((notification) => (
                    <li key={notification.id}>
                      <Card variant="subtle" className="px-3 py-2">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-sm">{notification.message}</p>
                          {!notification.read ? <Badge variant="secondary">New</Badge> : null}
                        </div>
                        <p className="text-muted-foreground mt-1 text-xs">
                          {formatSavedNoteTimestamp(notification.createdAt)}
                        </p>
                      </Card>
                    </li>
                  ))}
                </ul>
              )}
            </PopoverContent>
          </Popover>
        </ButtonGroup>
      </ButtonGroup>
    </div>
  )
}
