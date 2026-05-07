type DanoteIconProps = {
  className?: string
}

export function DanoteIcon({ className }: DanoteIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      {/* right/bottom arc — from ~55° to ~195° clockwise */}
      <path
        d="M19 7.1 A8.5 8.5 0 0 1 9.8 20.2"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      {/* left/top arc — from ~235° to ~15° clockwise */}
      <path
        d="M5 16.9 A8.5 8.5 0 0 1 14.2 3.8"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      {/* diagonal slash */}
      <line
        x1="17.2" y1="4.6"
        x2="6.8" y2="19.4"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  )
}
