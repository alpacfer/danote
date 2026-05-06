"use client"

import * as React from "react"
import { Command as CommandPrimitive } from "cmdk"
import { SearchIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

function Command({
  className,
  ...props
}: React.ComponentProps<typeof CommandPrimitive>) {
  return (
    <CommandPrimitive
      data-slot="command"
      className={cn(
        "bg-popover text-popover-foreground flex h-full w-full flex-col overflow-hidden rounded-md",
        className
      )}
      {...props}
    />
  )
}

function CommandDialog({
  title = "Command Palette",
  description = "Search for a command to run...",
  children,
  className,
  showCloseButton = true,
  commandKey,
  commandValue,
  onCommandValueChange,
  commandShouldFilter,
  ...props
}: React.ComponentProps<typeof Dialog> & {
  title?: string
  description?: string
  className?: string
  showCloseButton?: boolean
  commandKey?: string
  commandValue?: string
  onCommandValueChange?: (value: string) => void
  commandShouldFilter?: boolean
}) {
  return (
    <Dialog {...props}>
      <DialogHeader className="sr-only">
        <DialogTitle>{title}</DialogTitle>
        <DialogDescription>{description}</DialogDescription>
      </DialogHeader>
      <DialogContent
        className={cn("overflow-hidden p-0 top-[40%]", className)}
        showCloseButton={showCloseButton}
      >
        <Command
          key={commandKey}
          value={commandValue}
          onValueChange={onCommandValueChange}
          shouldFilter={commandShouldFilter}
          className="[&_[cmdk-group-heading]]:text-muted-foreground [&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group]]:px-2 [&_[cmdk-group]:not([hidden])_~[cmdk-group]]:pt-0 [&_[cmdk-input-wrapper]_svg]:h-4 [&_[cmdk-input-wrapper]_svg]:w-4 [&_[cmdk-input]]:!h-9 [&_[cmdk-input]]:!py-0 [&_[cmdk-item]]:px-3 [&_[cmdk-item]]:py-2 [&_[cmdk-item]_svg]:h-5 [&_[cmdk-item]_svg]:w-5"
        >
          {children}
        </Command>
      </DialogContent>
    </Dialog>
  )
}

function CommandInput({
  overlay,
  suffix,
  concealValue = false,
  multiline = false,
  className,
  ...props
}: React.ComponentProps<typeof CommandPrimitive.Input> & {
  overlay?: React.ReactNode
  suffix?: React.ReactNode
  concealValue?: boolean
  multiline?: boolean
}) {
  const { value, onValueChange, onKeyDown, maxLength, placeholder, autoFocus, ...restProps } = props
  const ariaLabel = restProps['aria-label']

  if (multiline) {
    return (
      <div
        data-slot="command-input-wrapper"
        className="!h-auto min-h-9 m-2 flex items-center gap-2 rounded-md border px-3"
      >
        <SearchIcon className="self-start mt-2 size-4 shrink-0 opacity-50" />
        <div className="relative min-w-0 flex-1">
          {overlay ? (
            <div
              aria-hidden="true"
              data-slot="command-input-overlay"
              className="text-foreground pointer-events-none absolute inset-0 overflow-hidden py-1.5 text-sm whitespace-pre-wrap"
            >
              {overlay}
            </div>
          ) : null}
          <textarea
            data-slot="command-input"
            rows={1}
            value={value as string ?? ""}
            onChange={(e) => onValueChange?.(e.target.value)}
            onKeyDown={onKeyDown as unknown as React.KeyboardEventHandler<HTMLTextAreaElement>}
            maxLength={maxLength}
            placeholder={placeholder}
            aria-label={ariaLabel as string | undefined}
            autoFocus={autoFocus}
            autoCorrect="off"
            autoComplete="off"
            spellCheck={false}
            autoCapitalize="none"
            className={cn(
              "placeholder:text-muted-foreground field-sizing-content w-full resize-none bg-transparent py-1.5 text-sm outline-hidden disabled:cursor-not-allowed disabled:opacity-50",
              concealValue ? "relative z-10 text-transparent caret-foreground" : "",
              className
            )}
          />
          <CommandPrimitive.Input
            value={value}
            onValueChange={onValueChange}
            className="sr-only absolute"
            tabIndex={-1}
            aria-hidden="true"
          />
        </div>
      </div>
    )
  }

  return (
    <div
      data-slot="command-input-wrapper"
      className="m-2 flex h-9 items-center gap-2 rounded-md border px-3"
    >
      <SearchIcon className="size-4 shrink-0 opacity-50" />
      <div className="relative min-w-0 flex-1">
        {overlay ? (
          <div
            aria-hidden="true"
            data-slot="command-input-overlay"
            className="text-foreground pointer-events-none absolute inset-0 flex items-center overflow-hidden py-3 text-sm whitespace-pre"
          >
            {overlay}
          </div>
        ) : null}
        <CommandPrimitive.Input
          data-slot="command-input"
          className={cn(
            "placeholder:text-muted-foreground flex h-10 w-full rounded-md bg-transparent py-3 text-sm outline-hidden disabled:cursor-not-allowed disabled:opacity-50",
            suffix ? "pr-28" : "",
            concealValue ? "relative z-10 text-transparent caret-foreground" : "",
            className
          )}
          value={value}
          onValueChange={onValueChange}
          onKeyDown={onKeyDown}
          maxLength={maxLength}
          placeholder={placeholder}
          autoFocus={autoFocus}
          autoCorrect="off"
          autoComplete="off"
          spellCheck={false}
          autoCapitalize="none"
          {...restProps}
        />
        {suffix ? (
          <div className="pointer-events-none absolute inset-y-0 right-0 flex min-w-10 items-center justify-end">
            {suffix}
          </div>
        ) : null}
      </div>
    </div>
  )
}

function CommandList({
  className,
  ...props
}: React.ComponentProps<typeof CommandPrimitive.List>) {
  return (
    <CommandPrimitive.List
      data-slot="command-list"
      className={cn(
        "max-h-[65vh] scroll-py-1 overflow-x-hidden overflow-y-auto pb-1",
        className
      )}
      {...props}
    />
  )
}

function CommandEmpty({
  ...props
}: React.ComponentProps<typeof CommandPrimitive.Empty>) {
  return (
    <CommandPrimitive.Empty
      data-slot="command-empty"
      className="py-6 text-center text-sm"
      {...props}
    />
  )
}

function CommandGroup({
  className,
  ...props
}: React.ComponentProps<typeof CommandPrimitive.Group>) {
  return (
    <CommandPrimitive.Group
      data-slot="command-group"
      className={cn(
        "text-foreground [&_[cmdk-group-heading]]:text-muted-foreground overflow-hidden px-1 pb-1 [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:pt-1.5 [&_[cmdk-group-heading]]:pb-1 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium",
        className
      )}
      {...props}
    />
  )
}

function CommandSeparator({
  className,
  ...props
}: React.ComponentProps<typeof CommandPrimitive.Separator>) {
  return (
    <CommandPrimitive.Separator
      data-slot="command-separator"
      className={cn("bg-border -mx-1 h-px", className)}
      {...props}
    />
  )
}

function CommandItem({
  className,
  ...props
}: React.ComponentProps<typeof CommandPrimitive.Item>) {
  return (
    <CommandPrimitive.Item
      data-slot="command-item"
      className={cn(
        "group/search-item data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground [&_svg:not([class*='text-'])]:text-muted-foreground relative flex cursor-default items-center gap-2 rounded-md px-2 py-1.5 text-sm outline-hidden select-none data-[disabled=true]:pointer-events-none data-[disabled=true]:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className
      )}
      {...props}
    />
  )
}

function CommandShortcut({
  className,
  ...props
}: React.ComponentProps<"span">) {
  return (
    <span
      data-slot="command-shortcut"
      className={cn(
        "text-muted-foreground ml-auto text-xs tracking-widest",
        className
      )}
      {...props}
    />
  )
}

export {
  Command,
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandShortcut,
  CommandSeparator,
}
