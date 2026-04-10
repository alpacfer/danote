import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  apiStatusBadgeClass,
  humanizeApiStatus,
  type ApiStatusItem,
  type ConnectionStatus,
  type NlpModelOption,
} from "@/app/core"

type StatusTabProps = {
  badgeVariant: "secondary" | "outline" | "destructive"
  status: ConnectionStatus
  backendUrl: string
  apiStatusItems: ApiStatusItem[]
  selectedNlpModel: NlpModelOption
  nlpModelOptions: readonly NlpModelOption[]
  onSelectedNlpModelChange: (value: NlpModelOption) => void
}

export function StatusTab({
  badgeVariant,
  status,
  backendUrl,
  apiStatusItems,
  selectedNlpModel,
  nlpModelOptions,
  onSelectedNlpModelChange,
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

      <div className="space-y-2">
        <Label className="text-sm font-medium">NLP model</Label>
        <Select value={selectedNlpModel} onValueChange={(value) => onSelectedNlpModelChange(value as NlpModelOption)}>
          <SelectTrigger aria-label="NLP model picker" className="w-full max-w-sm">
            <SelectValue placeholder="Select model" />
          </SelectTrigger>
          <SelectContent>
            {nlpModelOptions.map((model) => (
              <SelectItem key={model} value={model}>
                {model}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-muted-foreground text-xs">
          Preferred model for local benchmarking. Backend default remains <code>da_dacy_small_trf-0.2.0</code> unless{" "}
          <code>DANOTE_NLP_MODEL</code> is set before startup.
        </p>
      </div>
    </div>
  )
}