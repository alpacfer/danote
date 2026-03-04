import { useMemo, useState } from "react"

import {
  createNotificationId,
  type AppNotification,
} from "@/app/core"

export function useNotificationCenter() {
  const [notifications, setNotifications] = useState<AppNotification[]>([])
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false)

  const unreadNotifications = useMemo(
    () => notifications.filter((notification) => !notification.read),
    [notifications],
  )
  const hasUnreadNotifications = unreadNotifications.length > 0

  function pushNotification(message: string) {
    const nextNotification: AppNotification = {
      id: createNotificationId(),
      message,
      createdAt: new Date().toISOString(),
      read: false,
    }
    setNotifications((current) => [nextNotification, ...current])
  }

  function markAllNotificationsAsRead() {
    setNotifications((current) => current.map((notification) => ({ ...notification, read: true })))
  }

  return {
    notifications,
    setNotifications,
    isNotificationsOpen,
    setIsNotificationsOpen,
    unreadNotifications,
    hasUnreadNotifications,
    pushNotification,
    markAllNotificationsAsRead,
  }
}
