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
      targetKey?: string
      status?: "queued" | "verified" | "flagged" | "error"
      signature?: string | null
      actionCount?: number
    },
  ) => {
    if (options?.kind === "word_verification" && options.lemma && options.targetKey && options.status) {
      const createdAt = new Date().toISOString()
      setNotifications((current) => {
        const existingIndex = current.findIndex(
          (notification) => notification.kind === "word_verification" && notification.targetKey === options.targetKey,
        )
        const nextNotification: WordVerificationNotification = {
          id: existingIndex >= 0 ? current[existingIndex].id : createNotificationId(),
          message,
          createdAt,
          read: false,
          kind: "word_verification",
          lemma: options.lemma,
          meaningId: options.meaningId ?? null,
          surfaceForm: options.surfaceForm ?? null,
          targetKey: options.targetKey,
          status: options.status,
          signature: options.signature ?? null,
          actionCount: options.actionCount ?? 0,
        }
        if (existingIndex < 0) {
          return [nextNotification, ...current]
        }
        const existing = current[existingIndex]
        if (
          existing.kind === "word_verification"
          && existing.signature === nextNotification.signature
          && existing.message === nextNotification.message
          && existing.actionCount === nextNotification.actionCount
          && existing.status === nextNotification.status
          && existing.read === nextNotification.read
        ) {
          return current
        }
        const next = [...current]
        next[existingIndex] = nextNotification
        return next
      })
      return
    }
    const nextNotification: AppNotification = {
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

  const markWordVerificationNotificationsAsRead = useCallback((targetKeys: string[]) => {
    if (targetKeys.length === 0) {
      return
    }
    const targetKeySet = new Set(targetKeys)
    setNotifications((current) => {
      let changed = false
      const next = current.map((notification) => {
        if (notification.kind !== "word_verification" || notification.read) {
          return notification
        }
        if (!targetKeySet.has(notification.targetKey)) {
          return notification
        }
        changed = true
        return { ...notification, read: true }
      })
      return changed ? next : current
    })
  }, [])

  const clearWordVerificationNotification = useCallback((targetKey: string) => {
    setNotifications((current) => {
      const next = current.filter(
        (notification) => notification.kind !== "word_verification" || notification.targetKey !== targetKey,
      )
      return next.length === current.length ? current : next
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
    clearWordVerificationNotification,
  }
}
