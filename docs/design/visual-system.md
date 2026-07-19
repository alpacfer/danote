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

- The outer canvas, application inset, and semantic material surfaces share a
  visible but low-contrast irregular SVG grain. The canonical scrolling
  notebook sheet adds longer directional fibers and normally places blue-gray
  ruling above them. The Wordbank collection switches that final layer to a
  real 8px dot field aligned with its foreground catalogue lattice. Grain,
  fibers, and dots use separate frequencies so the surface reads as physical
  paper rather than a repeated digital pattern. All decorative treatments
  disappear when the user requests increased contrast.
- The layout lattice starts at the notebook sheet's content-box origin. Its
  base unit is 8px; every fourth unit is a visible 32px rule. Headings and
  major section starts use `data-grid-anchor="rule"`. Cards, decks, filters,
  empty states, and exposed rows use `data-grid-anchor="unit"` where browser
  tests need to enforce alignment.
- The sheet texture and grid are full-bleed within the main viewport, while the
  foreground notebook content remains centered at a 1280px maximum width. The
  dot origin follows the capped content edge on wider screens.
- Padding, gaps, line heights, bounded rows, and responsive dimensions use 8px
  multiples. The 32px ruling is a baseline rhythm, not a requirement to leave
  32px between every element.
- Feature materials use semantic roles (`word`, `reference`, `meaning`,
  `grammar`, `discovery`, `sentence`, and `related`) through `data-material`.
  They combine a restrained full-surface tint, an organic paper shadow, and a
  stamped icon or mark. Containment may use a neutral inset hairline.
- Do not use colored top/left rails, thick edges, or asymmetric accent borders.
  Reference decks vary by restrained material tone and stamp while preserving
  one shared size and interaction model.
- Standard cards use `shadow-card`; the application inset uses `shadow-shell`;
  dialogs, popovers, and the mobile navigation use `shadow-floating`.
- Texture and shadow support hierarchy. They must not compete with word forms,
  translations, or verification states.
- The Wordbank collection uses a compact card-catalogue composition: a reference
  drawer, a reduced sticky Danish index on the right edge, plain editorial
  margin letters, and responsive word-slip columns. The index shows only letters
  represented in the current filtered result, keeping the page quieter.
- Its reference drawer, filters, and catalogue use one shared left anchor and
  32px block spacing so the tactile details do not compromise visual rhythm.
- Saved-word hover previews resemble restrained herbarium labels: warm
  semantic word material, an editorial lemma heading, compact POS badges, and
  lightly ruled translation groups. Their field-book character comes from
  real hierarchy and paper treatment, never fabricated catalogue metadata.

## Motion

- Motion explains state: audio uses a sound ring, sense selection changes
  paper depth, generated examples unfold, new variations settle into place,
  and a supported View Transition connects a collection tile to its word page.
- Unsupported View Transitions fall back immediately. Under
  `prefers-reduced-motion: reduce`, nonessential animation and smooth scrolling
  are disabled.

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
