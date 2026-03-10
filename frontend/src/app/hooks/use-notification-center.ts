import { useCallback, useMemo, useState } from "react"

import {
  createNotificationId,
  type AppNotification,
  type WordVerificationNotification,
} from "@/app/core"

export function useNotificationCenter() {
  const [notifications, setNotifications] = useState<AppNotification[]>([])
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false)

  const unreadNotifications = useMemo(
    () => notifications.filter((notification) => !notification.read),
    [notifications],
  )
  const hasUnreadNotifications = unreadNotifications.length > 0
  const unreadWordVerificationNotifications = useMemo(
    () => unreadNotifications.filter((notification): notification is WordVerificationNotification => notification.kind === "word_verification"),
    [unreadNotifications],
  )
  const unreadWordbankNotificationCount = unreadWordVerificationNotifications.length
  const unreadWordbankLemmaCounts = useMemo(() => {
    const counts = new Map<string, number>()
    for (const notification of unreadWordVerificationNotifications) {
      counts.set(notification.lemma, (counts.get(notification.lemma) ?? 0) + 1)
    }
    return counts
  }, [unreadWordVerificationNotifications])

  const pushNotification = useCallback((
    message: string,
    options?: {
      kind?: "info" | "word_verification"
      lemma?: string
      meaningId?: number | null
      surfaceForm?: string | null
      actionCount?: number
    },
  ) => {
    const nextNotification: AppNotification = options?.kind === "word_verification" && options.lemma
      ? {
          id: createNotificationId(),
          message,
          createdAt: new Date().toISOString(),
          read: false,
          kind: "word_verification",
          lemma: options.lemma,
          meaningId: options.meaningId ?? null,
          surfaceForm: options.surfaceForm ?? null,
          actionCount: options.actionCount ?? 0,
        }
      : {
          id: createNotificationId(),
          message,
          createdAt: new Date().toISOString(),
          read: false,
          kind: "info",
        }
    setNotifications((current) => [nextNotification, ...current])
  }, [])

  const markAllNotificationsAsRead = useCallback(() => {
    setNotifications((current) => {
      if (!current.some((notification) => !notification.read)) {
        return current
      }
      return current.map((notification) => ({ ...notification, read: true }))
    })
  }, [])

  const markWordVerificationNotificationsAsRead = useCallback((lemma: string, meaningId: number | null) => {
    setNotifications((current) => {
      let changed = false
      const next = current.map((notification) => {
        if (notification.kind !== "word_verification" || notification.read) {
          return notification
        }
        if (notification.lemma !== lemma) {
          return notification
        }
        if (meaningId !== null && notification.meaningId !== meaningId) {
          return notification
        }
        changed = true
        return { ...notification, read: true }
      })
      return changed ? next : current
    })
  }, [])

  return {
    notifications,
    setNotifications,
    isNotificationsOpen,
    setIsNotificationsOpen,
    unreadNotifications,
    hasUnreadNotifications,
    unreadWordVerificationNotifications,
    unreadWordbankNotificationCount,
    unreadWordbankLemmaCounts,
    pushNotification,
    markAllNotificationsAsRead,
    markWordVerificationNotificationsAsRead,
  }
}
