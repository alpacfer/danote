import { CommandGroup, CommandItem } from "@/components/ui/command"
import { formatSentenceTranslation, type SentencebankSentence } from "@/app/core"

export type SavedSentencesGroupProps = {
  sentences: SentencebankSentence[]
  onOpen: (id: number) => void
}

export function SavedSentencesGroup({ sentences, onOpen }: SavedSentencesGroupProps) {
  return (
    <CommandGroup heading="Saved Sentences">
      {sentences.map((sentence) => {
        const translation = formatSentenceTranslation(sentence.english_translation)
        return (
          <CommandItem
            key={sentence.id}
            value={`saved-sentence-${sentence.id}`}
            onSelect={() => onOpen(sentence.id)}
            className="flex flex-col items-start gap-0.5"
          >
            <span className="text-sm font-medium leading-snug">{sentence.source_text}</span>
            {translation ? (
              <span className="text-muted-foreground text-xs leading-4">{translation}</span>
            ) : null}
          </CommandItem>
        )
      })}
    </CommandGroup>
  )
}
