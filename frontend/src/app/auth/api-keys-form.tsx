import { useState } from "react"
import { ExternalLink, KeyRound, Save, Trash2 } from "lucide-react"
import { toast } from "sonner"

import {
  API_KEY_PROVIDERS,
  PROVIDER_HELP_URLS,
  PROVIDER_LABELS,
  type AccountStatus,
  type ApiKeyProvider,
  deleteApiKey,
  upsertApiKey,
} from "@/app/auth/account-api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"

export type ApiKeysFormProps = {
  status: AccountStatus
  onChange: () => Promise<void> | void
}

export function ApiKeysForm({ status, onChange }: ApiKeysFormProps) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {API_KEY_PROVIDERS.map((provider) => (
        <ApiKeyRow
          key={provider}
          provider={provider}
          isSet={status.providers[provider]?.is_set ?? false}
          lastFour={status.providers[provider]?.last_four ?? null}
          onChange={onChange}
        />
      ))}
    </div>
  )
}

type ApiKeyRowProps = {
  provider: ApiKeyProvider
  isSet: boolean
  lastFour: string | null
  onChange: () => Promise<void> | void
}

function ApiKeyRow({ provider, isSet, lastFour, onChange }: ApiKeyRowProps) {
  const [value, setValue] = useState("")
  const [busy, setBusy] = useState(false)
  const label = PROVIDER_LABELS[provider]
  const helpUrl = PROVIDER_HELP_URLS[provider]

  const handleSave = async () => {
    if (!value.trim()) {
      return
    }
    setBusy(true)
    try {
      await upsertApiKey(provider, value.trim())
      setValue("")
      toast.success(`${label} key saved.`)
      await onChange()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : `Could not save ${label}.`)
    } finally {
      setBusy(false)
    }
  }

  const handleRemove = async () => {
    setBusy(true)
    try {
      await deleteApiKey(provider)
      toast.success(`${label} key removed.`)
      await onChange()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : `Could not remove ${label}.`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-4 rounded-lg border bg-background p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
            <KeyRound />
          </span>
          <div className="flex min-w-0 flex-col gap-1">
            <h3 className="truncate text-base font-medium">{label}</h3>
            <Button variant="link" size="sm" className="h-auto justify-start p-0" asChild>
              <a href={helpUrl} target="_blank" rel="noreferrer noopener">
                Get a key
                <ExternalLink data-icon="inline-end" />
              </a>
            </Button>
          </div>
        </div>
        {isSet ? (
          <Badge variant="secondary" className="shrink-0">
            Set{lastFour ? ` ...${lastFour}` : ""}
          </Badge>
        ) : (
          <Badge variant="outline" className="shrink-0">
            Not set
          </Badge>
        )}
      </div>

      <Separator />

      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-2">
          <Label htmlFor={`api-key-${provider}`} className="text-sm">
            {isSet ? "Replace key" : "API key"}
          </Label>
          <Input
            id={`api-key-${provider}`}
            type="password"
            autoComplete="off"
            value={value}
            onChange={(event) => setValue(event.target.value)}
            placeholder={isSet ? "Paste a new key to replace" : "Paste your API key"}
            disabled={busy}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={handleSave} disabled={busy || !value.trim()}>
            <Save data-icon="inline-start" />
            {isSet ? "Replace" : "Save"} key
          </Button>
          {isSet ? (
            <Button variant="ghost" onClick={handleRemove} disabled={busy}>
              <Trash2 data-icon="inline-start" />
              Remove
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  )
}
