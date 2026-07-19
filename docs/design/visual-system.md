# Danote visual system

Danote uses a balanced Nordic field-notebook visual language: warm paper,
botanical greens, editorial headings, soft material depth, and restrained
texture. The interface should feel collected and human without reducing the
density or clarity of linguistic information.

## Typography

- Source Sans 3 is the UI, body, control, translation, table, and metadata face.
  It carries dense information and every interactive label where quick scanning
  matters more than atmosphere.
- Playwrite GB J is reserved for the `danote` wordmark.
- Fraunces Variable has two semantic voices. Section titles use `SOFT=70`,
  `WONK=1`, and `opsz=48`; lexical text uses `SOFT=55`, `WONK=1`, and
  `opsz=24` for Danish lemmas, saved-word slips, sentence sources, and their
  previews. Both normally use weight `600`.
- Card, dialog, sheet, and empty-state titles inherit the section-title voice.
  English translations, badges, filters, timestamps, and long explanatory text
  remain Source Sans so the serif never compromises reading or navigation.
- Do not use the display faces for long prose, controls, badges, or metadata.

## Color roles

- `background` / `foreground`: unbleached herbarium paper and green-black ink.
- `primary`: deep bottle green for active navigation and primary actions.
- `secondary`: pressed sage for supportive states and quiet grouping.
- `accent`: dried ochre for hover, selection, and low-priority emphasis.
- `brand-clay`: decorative brand moments only; never errors or destructive actions.
- `brand-butter` and `brand-sky`: optional illustration and visualization accents.
- `surface-raised` / `surface-sunken`: material hierarchy, not status.
- `destructive`: remains separate from the botanical brand palette.

The light theme is **Herbarium Paper**: warm mounting stock, bottle-green ink,
pressed sage, ochre labels, clay stamps, and a restrained lichen-blue rule. The
dark theme is **Peat & Lantern**: peat-green canvas, moss-raised surfaces,
moonlit linen text, fern actions, and brass-like ochre accents. Dark mode is a
material counterpart with its own green-black foundation, not a dimmed or
inverted version of the light palette.

Feature code should use semantic Tailwind utilities such as `bg-primary`,
`text-muted-foreground`, and `bg-surface-raised`. Raw palette utilities belong
only in the existing POS, morphology, and category systems until those systems
receive their own redesign.

## Surfaces and depth

- The outer canvas, application inset, and semantic material surfaces share a
  visible but low-contrast irregular SVG grain. The canonical scrolling
  notebook sheet adds longer directional fibers and normally places blue-gray
  ruling above them. The Wordbank collection canvas is deliberately plain, with
  no ruling, grid, or texture; its word and reference cards carry the natural
  uncoated-paper texture instead. All decorative treatments disappear when the
  user requests increased contrast.
- The layout lattice starts at the notebook sheet's content-box origin. Its
  base unit is 8px; every fourth unit is a visible 32px rule. Headings and
  major section starts use `data-grid-anchor="rule"`. Cards, decks, filters,
  empty states, and exposed rows use `data-grid-anchor="unit"` where browser
  tests need to enforce alignment.
- The notebook sheet is full-bleed within the main viewport, while the
  foreground notebook content remains centered at a 1280px maximum width.
- Padding, gaps, line heights, bounded rows, and responsive dimensions use 8px
  multiples. The 32px ruling is a baseline rhythm, not a requirement to leave
  32px between every element.
- Feature materials use semantic roles (`word`, `reference`, `meaning`,
  `grammar`, `discovery`, `sentence`, and `related`) through `data-material`.
  They combine a restrained full-surface tint, an organic paper shadow, and a
  stamped icon or mark. Containment may use a neutral inset hairline.
- Wordbank collection cards and reference decks use flat index stock: grain and
  directional fibers sit above their semantic tint, while the outline and
  inset highlight preserve the paper edge without an external drop shadow.
  Reference stock also carries a quiet file-tab strip.
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
- The reference drawer responds to notebook-content width, not viewport width:
  it keeps two columns while the sidebar constrains the sheet and expands to a
  five-compartment row only when every card fits without clipping.
- Saved and pinned word faces remain Danish-only. Saved catalogue cards
  visually expand without reflow: one continuous textured surface grows around
  the original label as it moves and scales into the editorial heading.
  Compact POS badges and lightly ruled translation groups appear around that
  single title. Pinned cards retain their attached hover preview. Their
  field-book character comes from real hierarchy and paper treatment, never
  fabricated catalogue metadata.

## Motion

- Motion explains state: audio uses a sound ring, sense selection changes
  paper depth, generated examples unfold, new variations settle into place,
  saved cards unfold around their title, pinned translations hinge from their
  attached edge, and a supported View Transition connects a collection tile to
  its word page.
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

- [Kew Illustrations and Artefacts Collection](https://www.kew.org/science/collections-and-resources/collections/illustrations-and-artefacts-collection)
- [Biodiversity Heritage Library: Finding Life in Dead Plants](https://blog.biodiversitylibrary.org/2020/01/finding-life-in-dead-plant)
- [Smithsonian Institution Archives: Flattened Between the Pages](https://siarchives.si.edu/blog/flattened-between-pages)
- [Material 3 Expressive research](https://design.google/library/expressive-material-design-google-research)
- [Daylight](https://daylightcomputer.com/)
- [Headspace design](https://developer.apple.com/news/?id=fkfnhq8u)
- [Duolingo art system](https://blog.duolingo.com/shape-language-duolingos-art-style/)
- [Fraunces on Fontsource](https://fontsource.org/fonts/fraunces)
