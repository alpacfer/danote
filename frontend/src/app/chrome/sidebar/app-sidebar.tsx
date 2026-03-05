import { useCallback, useEffect, useMemo, useState } from "react"
import { BookOpen, Eye, NotebookPen, Plus, Settings } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandShortcut,
  CommandSeparator,
} from "@/components/ui/command"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import {
  badgesForSavedForm,
  badgesFromGramRaw,
  corSecondaryBadgeClass,
  glossDisplayForVariant,
  lemmaDisplayForVariant,
  lemmaTranslationForVariant,
  normalizeSearchWord,
  posBadgeClass,
  previewText,
  type CORSearchGroup,
  type CORSearchVariant,
  type SearchFeedbackContext,
  type WordbankLemma,
  type AppSection,
  type SavedNote,
} from "@/app/core"

import { ThemeToggleButton } from "@/app/chrome/theme-toggle-button"

import { useSidebarHotkeys } from "@/app/chrome/sidebar/use-sidebar-hotkeys"
import { useSidebarSearch } from "@/app/chrome/sidebar/use-sidebar-search"

export type AppSidebarProps = {
  activeSection: AppSection
  lemmas: WordbankLemma[]
  wordbankCacheVersion: number
  savedNotes: SavedNote[]
  onSelectPlayground: () => void
  onSelectNotes: () => void
  onSelectWordbank: () => void
  onSelectSentencebank: () => void
  onSelectDeveloper: () => void
  onOpenWordbankLemma: (lemma: string) => void
  onOpenSavedNote: (noteId: string) => void
  onAddWordFromSearch: (
    surfaceToken: string,
    lemmaCandidate: string | null,
    feedbackContext?: SearchFeedbackContext,
    metadata?: {
      posTag?: string | null
      morphology?: string | null
    },
  ) => Promise<string | null>
}

export function AppSidebar({
  activeSection,
  lemmas,
  wordbankCacheVersion,
  savedNotes,
  onSelectPlayground,
  onSelectNotes,
  onSelectWordbank,
  onSelectSentencebank,
  onSelectDeveloper,
  onOpenWordbankLemma,
  onOpenSavedNote,
  onAddWordFromSearch,
}: AppSidebarProps) {
  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [commandSelectionOverride, setCommandSelectionOverride] = useState("")
  const {
    searchQuery,
    setSearchQuery,
    normalizedQuery,
    matchingNotes,
    wordbankResults,
    corSearchGroups,
    corSearchVariants,
  } = useSidebarSearch({
    savedNotes,
    wordbankCacheVersion,
  })
  const savedLemmaKeySet = useMemo(
    () => new Set(lemmas.map((item) => normalizeSearchWord(item.lemma)).filter(Boolean)),
    [lemmas],
  )
  const hasWordbankResults = wordbankResults.length > 0
  const addVariationBySavedLemma = useMemo(() => {
    const linked = new Map<string, { group: CORSearchGroup; variant: CORSearchVariant }>()
    if (!normalizedQuery || wordbankResults.length === 0 || corSearchVariants.length === 0) {
      return linked
    }

    const savedLemmaKeys = new Set(wordbankResults.map(({ lemma }) => normalizeSearchWord(lemma.lemma)))
    for (const candidate of corSearchVariants) {
      const lemmaKey = normalizeSearchWord(candidate.variant.lemma)
      if (!lemmaKey || !savedLemmaKeys.has(lemmaKey)) {
        continue
      }
      const formKey = normalizeSearchWord(candidate.variant.form)
      if (!formKey || formKey === lemmaKey) {
        continue
      }
      if (formKey !== normalizedQuery) {
        continue
      }
      const existing = linked.get(lemmaKey)
      if (!existing) {
        linked.set(lemmaKey, candidate)
        continue
      }
      const existingFormKey = normalizeSearchWord(existing.variant.form)
      if (formKey === normalizedQuery && existingFormKey !== normalizedQuery) {
        linked.set(lemmaKey, candidate)
      }
    }
    return linked
  }, [corSearchVariants, normalizedQuery, wordbankResults])
  const displayVariantBySavedLemma = useMemo(() => {
    const linked = new Map<string, { group: CORSearchGroup; variant: CORSearchVariant }>()
    if (!normalizedQuery || wordbankResults.length === 0 || corSearchVariants.length === 0) {
      return linked
    }

    const savedLemmaKeys = new Set(wordbankResults.map(({ lemma }) => normalizeSearchWord(lemma.lemma)))
    for (const candidate of corSearchVariants) {
      const lemmaKey = normalizeSearchWord(candidate.variant.lemma)
      if (!lemmaKey || !savedLemmaKeys.has(lemmaKey)) {
        continue
      }
      const formKey = normalizeSearchWord(candidate.variant.form)
      if (!formKey || formKey !== normalizedQuery) {
        continue
      }
      const existing = linked.get(lemmaKey)
      if (!existing) {
        linked.set(lemmaKey, candidate)
        continue
      }
      const existingFormKey = normalizeSearchWord(existing.variant.form)
      if (formKey === normalizedQuery && existingFormKey !== normalizedQuery) {
        linked.set(lemmaKey, candidate)
      }
    }
    return linked
  }, [corSearchVariants, normalizedQuery, wordbankResults])
  const exactSavedVariationLemmaKeySet = useMemo(
    () =>
      new Set(
        wordbankResults
          .filter(({ matchSurface }) => normalizeSearchWord(matchSurface ?? "") === normalizedQuery)
          .map(({ lemma }) => normalizeSearchWord(lemma.lemma))
          .filter(Boolean),
      ),
    [normalizedQuery, wordbankResults],
  )
  const orderedWordbankResults = useMemo(() => {
    return [...wordbankResults].sort((left, right) => {
      const leftLemmaKey = normalizeSearchWord(left.lemma.lemma)
      const rightLemmaKey = normalizeSearchWord(right.lemma.lemma)
      const leftLinked = addVariationBySavedLemma.get(leftLemmaKey)?.variant ?? null
      const rightLinked = addVariationBySavedLemma.get(rightLemmaKey)?.variant ?? null
      const leftMatchSurface = normalizeSearchWord(left.matchSurface ?? "")
      const rightMatchSurface = normalizeSearchWord(right.matchSurface ?? "")
      const leftLinkedForm = normalizeSearchWord(leftLinked?.form ?? "")
      const rightLinkedForm = normalizeSearchWord(rightLinked?.form ?? "")
      const leftIsExactSaved = exactSavedVariationLemmaKeySet.has(leftLemmaKey)
      const rightIsExactSaved = exactSavedVariationLemmaKeySet.has(rightLemmaKey)
      const query = normalizedQuery

      const score = (payload: {
        lemmaKey: string
        linkedForm: string
        matchSurface: string
        isExactSaved: boolean
      }): number => {
        if (!query) {
          return 0
        }
        if (payload.isExactSaved) {
          return 520
        }
        if (payload.lemmaKey === query) {
          return 480
        }
        if (payload.linkedForm && payload.linkedForm === query) {
          return 400
        }
        if (payload.matchSurface && payload.matchSurface === query) {
          return 360
        }
        if (payload.linkedForm && payload.linkedForm.includes(query)) {
          return 280
        }
        if (payload.matchSurface && payload.matchSurface.includes(query)) {
          return 240
        }
        if (payload.lemmaKey.startsWith(query)) {
          return 200
        }
        return 0
      }

      const leftScore = score({
        lemmaKey: leftLemmaKey,
        linkedForm: leftLinkedForm,
        matchSurface: leftMatchSurface,
        isExactSaved: leftIsExactSaved,
      })
      const rightScore = score({
        lemmaKey: rightLemmaKey,
        linkedForm: rightLinkedForm,
        matchSurface: rightMatchSurface,
        isExactSaved: rightIsExactSaved,
      })
      if (leftScore !== rightScore) {
        return rightScore - leftScore
      }
      return left.lemma.lemma.localeCompare(right.lemma.lemma, "da-DK")
    })
  }, [addVariationBySavedLemma, exactSavedVariationLemmaKeySet, normalizedQuery, wordbankResults])
  const corSearchVariantsToRender = useMemo(
    () =>
      corSearchVariants.filter((candidate) => {
        const formKey = normalizeSearchWord(candidate.variant.form)
        const lemmaKey = normalizeSearchWord(candidate.variant.lemma)
        const isExactSavedVariation = formKey === normalizedQuery && exactSavedVariationLemmaKeySet.has(lemmaKey)
        if (isExactSavedVariation) {
          return false
        }
        const linked = addVariationBySavedLemma.get(lemmaKey)
        return !linked || linked.variant.cor_id !== candidate.variant.cor_id
      }),
    [addVariationBySavedLemma, corSearchVariants, exactSavedVariationLemmaKeySet, normalizedQuery],
  )
  const orderedCorSearchGroups = useMemo(() => {
    if (corSearchGroups.length <= 1) {
      return corSearchGroups
    }

    const groupScore = (group: CORSearchGroup): number => {
      let best = 0
      for (const variant of group.variants ?? []) {
        const formKey = normalizeSearchWord(variant.form)
        const lemmaKey = normalizeSearchWord(variant.lemma)
        const isVariationCandidate = formKey !== lemmaKey
        const isVariationAdd = isVariationCandidate && savedLemmaKeySet.has(lemmaKey)
        if (isVariationAdd && formKey === normalizedQuery) {
          best = Math.max(best, 400)
          continue
        }
        if (isVariationAdd) {
          best = Math.max(best, 320)
          continue
        }
        if (formKey === normalizedQuery) {
          best = Math.max(best, 240)
          continue
        }
        if (formKey.startsWith(normalizedQuery)) {
          best = Math.max(best, 160)
        }
      }
      return best
    }

    return [...corSearchGroups].sort((left, right) => {
      const leftScore = groupScore(left)
      const rightScore = groupScore(right)
      if (leftScore !== rightScore) {
        return rightScore - leftScore
      }
      return left.lemma.localeCompare(right.lemma, "da-DK")
    })
  }, [corSearchGroups, normalizedQuery, savedLemmaKeySet])
  const hasWordbankSectionResults = hasWordbankResults || corSearchVariantsToRender.length > 0
  const hasWordbankActions = corSearchVariantsToRender.length > 0
  const hasNoteResults = matchingNotes.length > 0
  const wordbankItemValue = useCallback((lemma: WordbankLemma): string =>
    `wordbank-${normalizeSearchWord(lemma.lemma)}`, [])
  const corVariantItemValue = useCallback((variant: CORSearchVariant): string =>
    `cor-variant-${variant.cor_id}`, [])
  const pageItems = useMemo(
    () => [
      {
        key: "page-playground",
        label: "Playground",
        shortcut: "Alt+P",
        icon: NotebookPen,
        onSelect: onSelectPlayground,
      },
      {
        key: "page-notes",
        label: "Notes",
        shortcut: "Alt+N",
        icon: BookOpen,
        onSelect: onSelectNotes,
      },
      {
        key: "page-wordbank",
        label: "Wordbank",
        shortcut: "Alt+W",
        icon: BookOpen,
        onSelect: onSelectWordbank,
      },
      {
        key: "page-sentencebank",
        label: "Sentencebank",
        shortcut: "Alt+S",
        icon: BookOpen,
        onSelect: onSelectSentencebank,
      },
      {
        key: "page-developer",
        label: "Developer",
        shortcut: "Alt+D",
        icon: Settings,
        onSelect: onSelectDeveloper,
      },
    ],
    [onSelectDeveloper, onSelectNotes, onSelectPlayground, onSelectSentencebank, onSelectWordbank],
  )
  const matchingPageItems = useMemo(() => {
    if (!normalizedQuery) {
      return pageItems
    }
    return pageItems.filter((item) => item.label.toLocaleLowerCase("da-DK").includes(normalizedQuery))
  }, [normalizedQuery, pageItems])
  const hasPageResults = matchingPageItems.length > 0
  const hasAnyResults = hasWordbankSectionResults || hasNoteResults || hasPageResults
  const orderedCorVariantsToRender = useMemo(() => {
    const variants: CORSearchVariant[] = []
    for (const group of orderedCorSearchGroups) {
      for (const item of corSearchVariantsToRender) {
        if (item.group !== group) {
          continue
        }
        variants.push(item.variant)
      }
    }
    return variants
  }, [corSearchVariantsToRender, orderedCorSearchGroups])
  const orderedCommandItemValues = useMemo(() => {
    const values: string[] = []
    for (const { lemma } of orderedWordbankResults) {
      values.push(wordbankItemValue(lemma))
    }
    for (const variant of orderedCorVariantsToRender) {
      values.push(corVariantItemValue(variant))
    }
    for (const note of matchingNotes) {
      values.push(`note-${note.id}`)
    }
    for (const page of matchingPageItems) {
      values.push(page.key)
    }
    return values
  }, [
    corVariantItemValue,
    matchingNotes,
    matchingPageItems,
    orderedCorVariantsToRender,
    orderedWordbankResults,
    wordbankItemValue,
  ])
  const commandSelectionValue = useMemo(() => {
    if (
      commandSelectionOverride
      && orderedCommandItemValues.includes(commandSelectionOverride)
    ) {
      return commandSelectionOverride
    }
    return orderedCommandItemValues[0] ?? ""
  }, [commandSelectionOverride, orderedCommandItemValues])



  useSidebarHotkeys({
    onToggleSearch: () => {
      setIsSearchOpen((current) => !current)
    },
    onSelectPlayground,
    onSelectNotes,
    onSelectWordbank,
    onSelectSentencebank,
    onSelectDeveloper,
  })

  useEffect(() => {
    if (isSearchOpen) {
      return
    }
    const clearTimeoutId = window.setTimeout(() => {
      setSearchQuery("")
    }, 220)
    return () => {
      window.clearTimeout(clearTimeoutId)
    }
  }, [isSearchOpen, setSearchQuery])

  return (
    <Sidebar variant="inset">
      <SidebarHeader className="gap-2">
        <p className="px-2 text-sm font-semibold">Danote</p>
        <Button
          type="button"
          variant="outline"
          className="justify-between"
          onClick={() => setIsSearchOpen(true)}
        >
          Search...
          <span className="text-muted-foreground text-[10px] uppercase">Cmd/Ctrl+K</span>
        </Button>
        <CommandDialog
          open={isSearchOpen}
          onOpenChange={(open) => {
            setIsSearchOpen(open)
            if (!open) {
              setCommandSelectionOverride("")
            }
          }}
          commandShouldFilter={false}
          commandValue={commandSelectionValue}
          onCommandValueChange={setCommandSelectionOverride}
          title="Search wordbank and notes"
          description="Search saved words, local COR analyses, and notes."
        >
          <CommandInput
            placeholder="Search words and notes..."
            value={searchQuery}
            onValueChange={(value) => {
              setSearchQuery(normalizeSearchWord(value))
              setCommandSelectionOverride("")
            }}
            aria-label="command search"
          />
          <CommandList>
            {normalizedQuery && !hasAnyResults ? <CommandEmpty>No results found.</CommandEmpty> : null}
            {hasWordbankSectionResults ? (
              <CommandGroup heading="Wordbank">
                {orderedWordbankResults.map(({ lemma }) => (
                  <CommandItem
                    key={`search-lemma-${lemma.lemma}`}
                    value={wordbankItemValue(lemma)}
                    onSelect={() => {
                      const addVariation = addVariationBySavedLemma.get(normalizeSearchWord(lemma.lemma))
                      const isExactSavedVariation = exactSavedVariationLemmaKeySet.has(normalizeSearchWord(lemma.lemma))
                      if (addVariation && !isExactSavedVariation) {
                        void (async () => {
                          const addedLemma = await onAddWordFromSearch(
                            addVariation.variant.form,
                            addVariation.variant.lemma,
                            {
                              rawToken: normalizedQuery,
                              predictedStatus: "variation",
                              suggestionsShown: [`${addVariation.variant.lemma}:${addVariation.variant.gram_raw}`],
                            },
                            {
                              posTag: addVariation.variant.pos_tag ?? null,
                              morphology: addVariation.variant.morphology ?? null,
                            },
                          )
                          if (addedLemma) {
                            setIsSearchOpen(false)
                            setSearchQuery("")
                          }
                        })()
                        return
                      }
                      onOpenWordbankLemma(lemma.lemma)
                      setIsSearchOpen(false)
                      setSearchQuery("")
                    }}
                    className="flex items-center justify-between gap-3"
                  >
                    <div className="flex min-w-0 flex-col items-start gap-0.5">
                      {(() => {
                        const displayVariant = displayVariantBySavedLemma.get(normalizeSearchWord(lemma.lemma))?.variant ?? null
                        const displayTitle = displayVariant?.form?.trim()
                          || lemma.display_lemma?.trim()
                          || lemma.lemma
                        const displayVariantFormKey = normalizeSearchWord(displayVariant?.form ?? "")
                        const displayVariantLemmaKey = normalizeSearchWord(displayVariant?.lemma ?? "")
                        const showLinkedLemma = Boolean(
                          displayVariant
                          && displayVariantLemmaKey
                          && displayVariantFormKey
                          && displayVariantLemmaKey !== displayVariantFormKey,
                        )
                        const linkedLemmaDisplay = showLinkedLemma && displayVariant
                          ? lemmaDisplayForVariant(displayVariant)
                          : null
                        const linkedLemmaTranslation = showLinkedLemma && displayVariant
                          ? lemmaTranslationForVariant(displayVariant)
                          : null
                        const detailLine = displayVariant
                          ? (glossDisplayForVariant(displayVariant) ?? (lemma.english_translation?.trim() || "No translation available."))
                          : (lemma.english_translation?.trim() || "No translation available.")
                        const badges = displayVariant
                          ? badgesFromGramRaw(displayVariant.gram_raw)
                          : badgesForSavedForm({
                            pos_tag: lemma.pos_tag ?? null,
                            morphology: lemma.morphology ?? null,
                          })
                        return (
                          <>
                            <span>
                              <strong className="font-semibold">{displayTitle}</strong>
                              {linkedLemmaDisplay ? (
                                <span className="text-muted-foreground text-xs">
                                  {" "}from <em>{linkedLemmaDisplay}</em>
                                  {linkedLemmaTranslation ? ` (${linkedLemmaTranslation})` : ""}
                                </span>
                              ) : null}
                            </span>
                            <span className="text-muted-foreground text-xs">{detailLine}</span>
                            {badges.length > 0 ? (
                              <div className="mt-1 flex flex-wrap gap-1.5">
                                {badges.map((badge) => (
                                  <Badge
                                    key={`search-wordbank-${lemma.lemma}-badge-${badge.label}`}
                                    variant={badge.tone === "primary" ? "default" : "secondary"}
                                    className={`text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(displayVariant?.pos_tag ?? lemma.pos_tag ?? null)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
                                    data-testid="search-metadata-badge"
                                  >
                                    {badge.label}
                                  </Badge>
                                ))}
                              </div>
                            ) : null}
                          </>
                        )
                      })()}
                    </div>
                    {(() => {
                      const lemmaKey = normalizeSearchWord(lemma.lemma)
                      const linkedVariation = addVariationBySavedLemma.get(lemmaKey)
                      const isExactSavedVariation = exactSavedVariationLemmaKeySet.has(lemmaKey)
                      if (linkedVariation && !isExactSavedVariation) {
                        return (
                      <span className="text-muted-foreground flex items-center gap-1 text-xs font-semibold">
                        <span data-testid="search-add-variation-label">variation</span>
                        <Plus data-testid="search-add-icon" className="size-4 shrink-0" />
                      </span>
                        )
                      }
                      return (
                      <Eye data-testid="search-open-icon" className="text-muted-foreground size-4 shrink-0" />
                      )
                    })()}
                  </CommandItem>
                ))}
                {orderedCorSearchGroups.map((group, groupIndex) => (
                  <div
                    key={`cor-group-${group.lemma}-${group.gloss ?? ""}-${group.pos_tag ?? ""}-${groupIndex}`}
                    className="mt-1 first:mt-0"
                  >
                    {corSearchVariantsToRender
                      .filter((item) => item.group === group)
                      .map(({ variant }) => {
                        const isVariationCandidate = normalizeSearchWord(variant.form) !== normalizeSearchWord(variant.lemma)
                        const isVariationAdd = isVariationCandidate && savedLemmaKeySet.has(normalizeSearchWord(variant.lemma))
                        return (
                      <CommandItem
                        key={`cor-variant-${variant.cor_id}`}
                        value={corVariantItemValue(variant)}
                        onSelect={() => {
                          void (async () => {
                            const addedLemma = await onAddWordFromSearch(
                              variant.form,
                              variant.lemma,
                              {
                                rawToken: normalizedQuery,
                                predictedStatus: isVariationAdd ? "variation" : "new",
                                suggestionsShown: [`${variant.lemma}:${variant.gram_raw}`],
                              },
                              {
                                posTag: variant.pos_tag ?? null,
                                morphology: variant.morphology ?? null,
                              },
                            )
                            if (addedLemma) {
                              setIsSearchOpen(false)
                              setSearchQuery("")
                            }
                          })()
                        }}
                        className="flex items-center justify-between gap-3"
                      >
                        <div className="flex min-w-0 flex-col items-start gap-0.5">
                          <span>
                            <strong className="font-semibold">{variant.form}</strong>
                            {lemmaDisplayForVariant(variant) ? (
                              <span className="text-muted-foreground text-xs">
                                {" "}from <em>{lemmaDisplayForVariant(variant)}</em>
                                {lemmaTranslationForVariant(variant) ? ` (${lemmaTranslationForVariant(variant)})` : ""}
                              </span>
                            ) : null}
                          </span>
                          {glossDisplayForVariant(variant) ? (
                            <span className="text-muted-foreground text-xs">{glossDisplayForVariant(variant)}</span>
                          ) : null}
                          <div className="mt-1 flex flex-wrap gap-1.5">
                            {badgesFromGramRaw(variant.gram_raw).map((badge) => (
                              <Badge
                                key={`cor-variant-${variant.cor_id}-gram-${badge.label}`}
                                variant={badge.tone === "primary" ? "default" : "secondary"}
                                className={`text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(variant.pos_tag ?? null)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
                                data-testid="search-metadata-badge"
                              >
                                {badge.label}
                              </Badge>
                            ))}
                          </div>
                        </div>
                        {isVariationAdd ? (
                          <span className="text-muted-foreground flex items-center gap-1 text-xs font-semibold">
                            <span data-testid="search-add-variation-label">variation</span>
                            <Plus data-testid="search-add-icon" className="size-4 shrink-0" />
                          </span>
                        ) : (
                          <Plus data-testid="search-add-icon" className="text-muted-foreground size-4 shrink-0" />
                        )}
                      </CommandItem>
                        )
                      })}
                  </div>
                ))}
              </CommandGroup>
            ) : null}
            {(hasWordbankSectionResults || hasWordbankActions) && hasNoteResults ? <CommandSeparator /> : null}
            {hasNoteResults ? (
              <CommandGroup heading="Notes">
                {matchingNotes.map((note) => (
                  <CommandItem
                    key={`search-note-${note.id}`}
                    value={`note-${note.id}`}
                    onSelect={() => {
                      onOpenSavedNote(note.id)
                      setIsSearchOpen(false)
                      setSearchQuery("")
                    }}
                    className="flex-col items-start gap-0.5"
                  >
                    <span className="font-medium">{note.name}</span>
                    <span className="text-muted-foreground line-clamp-2 text-xs">
                      {previewText(note.text, 80)}
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            ) : null}
            {(hasWordbankSectionResults || hasWordbankActions || hasNoteResults) && hasPageResults ? <CommandSeparator /> : null}
            {hasPageResults ? (
              <CommandGroup heading="Pages">
                {matchingPageItems.map((item) => {
                  const Icon = item.icon
                  return (
                    <CommandItem
                      key={item.key}
                      value={item.key}
                      onSelect={() => {
                        item.onSelect()
                        setIsSearchOpen(false)
                      }}
                    >
                      <Icon />
                      <span>{item.label}</span>
                      <CommandShortcut>{item.shortcut}</CommandShortcut>
                    </CommandItem>
                  )
                })}
              </CommandGroup>
            ) : null}
          </CommandList>
        </CommandDialog>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  type="button"
                  isActive={activeSection === "playground"}
                  onClick={onSelectPlayground}
                >
                  <NotebookPen />
                  <span>Playground</span>
                  <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+P</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  type="button"
                  isActive={activeSection === "notes"}
                  onClick={onSelectNotes}
                >
                  <BookOpen />
                  <span>Notes</span>
                  <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+N</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  type="button"
                  isActive={activeSection === "wordbank"}
                  onClick={onSelectWordbank}
                >
                  <BookOpen />
                  <span>Wordbank</span>
                  <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+W</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  type="button"
                  isActive={activeSection === "sentencebank"}
                  onClick={onSelectSentencebank}
                >
                  <BookOpen />
                  <span>Sentencebank</span>
                  <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+S</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  type="button"
                  isActive={activeSection === "developer"}
                  onClick={onSelectDeveloper}
                >
                  <Settings />
                  <span>Developer</span>
                  <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+D</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <ThemeToggleButton />
      </SidebarFooter>
    </Sidebar>
  )
}
