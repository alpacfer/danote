import { useState } from "react"
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export type ApiKeysFormProps = {
  status: AccountStatus
  onChange: () => Promise<void> | void
}

export function ApiKeysForm({ status, onChange }: ApiKeysFormProps) {
  return (
    <div className="flex flex-col gap-4">
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
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base">{label}</CardTitle>
            <CardDescription>
              <a
                href={helpUrl}
                target="_blank"
                rel="noreferrer noopener"
                className="text-sm text-muted-foreground underline-offset-2 hover:underline"
              >
                Get a key
              </a>
            </CardDescription>
          </div>
          {isSet ? (
            <Badge variant="secondary" className="shrink-0">
              Set{lastFour ? ` · ••••${lastFour}` : ""}
            </Badge>
          ) : (
            <Badge variant="outline" className="shrink-0">
              Not set
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-col gap-2">
          <Label htmlFor={`api-key-${provider}`} className="text-xs uppercase tracking-wide">
            {isSet ? "Replace" : "Enter"} key
          </Label>
          <Input
            id={`api-key-${provider}`}
            type="password"
            autoComplete="off"
            value={value}
            onChange={(event) => setValue(event.target.value)}
            placeholder={isSet ? "Paste a new key to replace…" : "Paste your API key"}
            disabled={busy}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={handleSave} disabled={busy || !value.trim()}>
            {isSet ? "Replace" : "Save"} key
          </Button>
          {isSet ? (
            <Button variant="ghost" onClick={handleRemove} disabled={busy}>
              Remove
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  )
}
