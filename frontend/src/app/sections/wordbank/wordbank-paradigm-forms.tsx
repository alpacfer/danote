import { Fragment } from "react"

import { normalizeSearchWord } from "@/app/core"
import type { ParadigmCellEntry, SurfaceForm } from "@/app/sections/wordbank/wordbank-paradigm-utils"
import { WordbankPronunciationWord } from "@/app/sections/wordbank/wordbank-pronunciation-word"
import { AudioLines, Loader2 } from "lucide-react"

type PronunciationProps = {
  pronunciationLoadingByForm: Record<string, boolean>
  regeneratingPronunciationByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  onRegeneratePronunciation: (form: string) => void
  nonInteractiveForms?: Set<string>
}

export function ParadigmCellEntries({
  entries,
  ...pronunciationProps
}: PronunciationProps & {
  entries: ParadigmCellEntry[]
}) {
  return (
    <div className="flex flex-col gap-1">
      {groupCellEntries(entries).map((group) => (
        <div
          key={`${group.label ?? "form"}-${group.forms.map((form) => form.form).join("/")}`}
          className="flex flex-wrap items-center gap-x-1.5 gap-y-1"
        >
          {group.label ? <span data-paradigm-form-label>{group.label}:</span> : null}
          {group.forms.map((form, index) => (
            <Fragment key={`${form.form}-${index}`}>
              {index > 0 ? <span data-paradigm-form-separator>/</span> : null}
              <ParadigmCellForm form={form} {...pronunciationProps} />
            </Fragment>
          ))}
        </div>
      ))}
    </div>
  )
}

export function ParadigmCellForm({
  form,
  pronunciationLoadingByForm,
  regeneratingPronunciationByForm,
  onPlayPronunciation,
  onRegeneratePronunciation,
  nonInteractiveForms,
}: PronunciationProps & {
  form: SurfaceForm
}) {
  const normalizedForm = normalizeSearchWord(form.form)
  const isRegenerating = Boolean(regeneratingPronunciationByForm[normalizedForm])
  if (nonInteractiveForms?.has(normalizedForm)) {
    return <span data-paradigm-form>{form.form}</span>
  }
  return (
    <WordbankPronunciationWord
      form={form.form}
      hasPronunciation={form.has_pronunciation ?? false}
      pronunciationLoadingByForm={pronunciationLoadingByForm}
      onPlayPronunciation={onPlayPronunciation}
      contextMenuItems={[
        {
          icon: isRegenerating ? <Loader2 className="animate-spin" /> : <AudioLines />,
          label: isRegenerating ? "Regenerating audio..." : "Regenerate audio",
          disabled: isRegenerating,
          onSelect: () => onRegeneratePronunciation(form.form),
        },
      ]}
      className="font-lexical text-[15px] leading-5 font-semibold"
      iconClassName="size-3"
    />
  )
}

function groupCellEntries(entries: ParadigmCellEntry[]): Array<{ label?: string; forms: SurfaceForm[] }> {
  const groups: Array<{ label?: string; forms: SurfaceForm[] }> = []
  for (const entry of entries) {
    const group = groups.find((item) => item.label === entry.label)
    if (group) {
      group.forms.push(entry.form)
    } else {
      groups.push({ label: entry.label, forms: [entry.form] })
    }
  }
  return groups
}
