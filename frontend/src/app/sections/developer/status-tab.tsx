import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import {
  apiStatusBadgeClass,
  humanizeApiStatus,
  type ApiStatusItem,
  type ConnectionStatus,
} from "@/app/core"

type StatusTabProps = {
  badgeVariant: "secondary" | "outline" | "destructive"
  status: ConnectionStatus
  backendUrl: string
  apiStatusItems: ApiStatusItem[]
}

export function StatusTab({
  badgeVariant,
  status,
  backendUrl,
  apiStatusItems,
}: StatusTabProps) {
  return (
    <div className="space-y-6">
      <Card variant="subtle" className="flex items-center justify-between p-4">
        <div>
          <p className="text-sm font-medium">Backend connection</p>
          <p className="text-muted-foreground mt-1 text-xs">
            <code>{backendUrl}</code>
          </p>
        </div>
        <Badge variant={badgeVariant} aria-label="backend-connection-status">
          {status}
        </Badge>
      </Card>

      <div>
        <p className="mb-3 text-sm font-medium">Service status</p>
        <div className="grid grid-cols-2 gap-2" aria-label="api-status-list">
          {apiStatusItems.map((item) => (
            <Card key={item.name} variant="subtle" className="flex items-center justify-between gap-2 p-3">
              <span className="text-sm">{item.label}</span>
              <Badge variant="outline" className={apiStatusBadgeClass(item.status)}>
                {humanizeApiStatus(item.status)}
              </Badge>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
