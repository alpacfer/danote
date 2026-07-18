import { Button } from "@/components/ui/button"

const DANISH_ALPHABET = [
  "A",
  "B",
  "C",
  "D",
  "E",
  "F",
  "G",
  "H",
  "I",
  "J",
  "K",
  "L",
  "M",
  "N",
  "O",
  "P",
  "Q",
  "R",
  "S",
  "T",
  "U",
  "V",
  "W",
  "X",
  "Y",
  "Z",
  "Æ",
  "Ø",
  "Å",
] as const

type WordbankAlphabetIndexProps = {
  activeLetter: string | null
  availableLetters: ReadonlySet<string>
  onSelectLetter: (letter: string) => void
}

export function WordbankAlphabetIndex({
  activeLetter,
  availableLetters,
  onSelectLetter,
}: WordbankAlphabetIndexProps) {
  return (
    <nav
      className="danote-alphabet-index sticky top-0 flex min-w-0 overflow-x-auto p-0 md:order-2 md:top-4 md:self-start md:justify-self-end md:overflow-visible"
      aria-label="Word catalogue alphabet"
      data-grid-anchor="unit"
    >
      <div className="ml-auto flex w-max md:grid md:grid-cols-1">
        {DANISH_ALPHABET.filter((letter) => availableLetters.has(letter)).map((letter) => {
          const isActive = activeLetter === letter
          return (
            <Button
              key={letter}
              type="button"
              variant="ghost"
              size="icon-sm"
              className={
                isActive
                  ? "text-primary relative shrink-0 rounded-none after:absolute after:bottom-0.5 after:h-px after:w-3 after:bg-current"
                  : "text-muted-foreground shrink-0 rounded-none"
              }
              aria-label={`Jump to ${letter}`}
              aria-current={isActive ? "true" : undefined}
              onClick={() => onSelectLetter(letter)}
            >
              <span className="font-section-title text-sm" aria-hidden="true">
                {letter}
              </span>
            </Button>
          )
        })}
      </div>
    </nav>
  )
}
