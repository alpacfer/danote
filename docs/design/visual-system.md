# Danote visual system

Danote uses a balanced Nordic field-notebook visual language: warm paper,
botanical greens, editorial headings, soft material depth, and restrained
texture. The interface should feel collected and human without reducing the
density or clarity of linguistic information.

## Typography

- Source Sans 3 is the UI, body, control, table, and metadata face.
- Playwrite GB J is reserved for the `danote` wordmark.
- Fraunces Variable is the section-title face. Use weight `600` with
  `SOFT=70`, `WONK=1`, and `opsz=48`.
- Do not use the display faces for long text, badges, or linguistic detail.

## Color roles

- `background` / `foreground`: warm paper and muted blue ink.
- `primary`: forest green for active navigation and primary actions.
- `secondary`: sea-glass for supportive states and quiet grouping.
- `accent`: oat for hover, selection, and low-priority emphasis.
- `brand-clay`: decorative brand moments only; never errors or destructive actions.
- `brand-butter` and `brand-sky`: optional illustration and visualization accents.
- `surface-raised` / `surface-sunken`: material hierarchy, not status.
- `destructive`: remains separate from the botanical brand palette.

Feature code should use semantic Tailwind utilities such as `bg-primary`,
`text-muted-foreground`, and `bg-surface-raised`. Raw palette utilities belong
only in the existing POS, morphology, and category systems until those systems
receive their own redesign.

## Surfaces and depth

- The outer canvas uses a visible but low-contrast two-tone CSS paper grain.
  The inset application canvas adds 32px blue-gray notebook ruling beneath
  that grain. Both layers must disappear when the user requests increased
  contrast.
- Standard cards use `shadow-card`; the application inset uses `shadow-shell`;
  dialogs, popovers, and the mobile navigation use `shadow-floating`.
- Texture and shadow support hierarchy. They must not compete with word forms,
  translations, or verification states.

## Accessibility

- Normal text must meet WCAG AA contrast of at least `4.5:1`; large text and
  non-text controls must meet at least `3:1`.
- Keyboard focus uses the semantic ring color and must remain visible in both themes.
- Light is the default. Dark mode is an inky botanical counterpart, not an
  inverted grayscale theme.
- Decorative texture must carry no information and must not be the only
  distinction between surfaces.

## References

- [Material 3 Expressive research](https://design.google/library/expressive-material-design-google-research)
- [Daylight](https://daylightcomputer.com/)
- [Headspace design](https://developer.apple.com/news/?id=fkfnhq8u)
- [Duolingo art system](https://blog.duolingo.com/shape-language-duolingos-art-style/)
- [Fraunces on Fontsource](https://fontsource.org/fonts/fraunces)
