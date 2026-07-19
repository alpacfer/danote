import {
  SearchResultAction,
  SearchSection,
} from "@/app/chrome/sidebar/sidebar-search-presentation"
import { CommandItem } from "@/components/ui/command"
import { formatSentenceTranslation, type SentencebankSentence } from "@/app/core"

export type SavedSentencesGroupProps = {
  sentences: SentencebankSentence[]
  onOpen: (id: number) => void
}

export function SavedSentencesGroup({ sentences, onOpen }: SavedSentencesGroupProps) {
  return (
    <SearchSection heading="In your sentences" material="sentence">
      {sentences.map((sentence) => {
        const translation = formatSentenceTranslation(sentence.english_translation)
        return (
          <CommandItem
            key={sentence.id}
            value={`saved-sentence-${sentence.id}`}
            onSelect={() => onOpen(sentence.id)}
            data-search-slip
            data-material="sentence"
            className="flex items-center justify-between gap-3"
          >
            <span className="flex min-w-0 flex-col items-start gap-0.5">
              <span data-search-lexical className="font-semibold leading-snug">
                {sentence.source_text}
              </span>
              {translation ? (
                <span className="text-muted-foreground text-xs leading-4">{translation}</span>
              ) : null}
            </span>
            <SearchResultAction kind="open" />
          </CommandItem>
        )
      })}
    </SearchSection>
  )
}
