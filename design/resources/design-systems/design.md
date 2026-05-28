# Design systems — library

A **design system** is a reusable visual language: color, typography, spacing,
radius, elevation, and component styling. Each lives as one markdown file in this
folder and is referenced by its slug (the filename without `.md`). A design picks
**one** design system; swapping the slug re-skins the design.

## Canonical file format

A design-system file is **YAML front-matter (the normalised tokens) + a prose
body (the rationale and rules).** New files must follow this shape so every
system is expressed the same way.

```yaml
---
version: alpha
name: Yacht Club                 # display name
description: One line, evocative.
colors:
  primary: "#F7F0DE"             # headlines / core text
  secondary: "#B4A88A"           # borders, captions, metadata
  tertiary: "#C42C2C"            # the single interaction accent — reserve it
  neutral: "#0B2440"             # page foundation
  surface: "#142F54"             # cards, panels
  on-primary: "#F7F0DE"          # text on accent fills
typography:
  display: { fontFamily: Playfair Display, fontSize: 4.5rem, fontWeight: 600, letterSpacing: "-0.01em" }
  h1:      { fontFamily: Playfair Display, fontSize: 2.3rem, fontWeight: 600 }
  body:    { fontFamily: Inter, fontSize: 1rem, lineHeight: 1.65 }
  label:   { fontFamily: Inter, fontSize: 0.72rem, fontWeight: 600, letterSpacing: "0.18em" }
rounded: { sm: 2px, md: 3px, lg: 5px }
spacing: { sm: 8px, md: 16px, lg: 32px }
components:                       # component styles reference tokens via {dot.path}
  button-primary: { backgroundColor: "{colors.tertiary}", textColor: "{colors.on-primary}", rounded: "{rounded.md}", padding: 12px 20px }
  card:           { backgroundColor: "{colors.surface}", textColor: "{colors.primary}", rounded: "{rounded.lg}", padding: 24px }
---
## Overview        — what the system is for, in two or three sentences
## Colors          — what each role is for; the single-accent rule
## Typography       — the editorial/functional pairing and sizes
## Do's and Don'ts  — the load-bearing rules a renderer must respect
```

Token references like `{colors.tertiary}` resolve against the front-matter, so a
component never hard-codes a value.

## Available systems (in this folder)

| Slug | Name | Register |
|------|------|----------|
| `design-yacht-club` | Yacht Club | Regatta: navy, rope cream, single signal-red accent; editorial serif. |
| `design-zed` | Zed Dev | Editor-dark, warm near-black, cyan accent, mono-everywhere. |
| `design-pulse` | PulsePoint | Clinical dark-mode for dense data/vitals dashboards; alert-hierarchy first. |

> `design-pulse.md` predates this schema and is written as long-form prose
> (richer, but without the normalised front-matter). Bring it into the canonical
> shape when next touched so the library is fully normalised.

## Source library (to author new systems)

When building a new design system, draw concrete choices from these. They are
*sources*, not systems themselves — distil them into a canonical file above.
(Curated from [bradtraversy/design-resources-for-developers](https://github.com/bradtraversy/design-resources-for-developers).)

**Design systems / UI kits** — reference token sets and component conventions:
Material UI (material-ui.com), Ant Design (ant.design), shadcn/ui (ui.shadcn.com),
Radix UI (radix-ui.com), Chakra UI (chakra-ui.com), Headless UI (headlessui.dev),
Flowbite (flowbite.com), daisyUI (daisyui.com), Mantine (mantine.dev).

**CSS frameworks** — spacing/typography scales worth borrowing: Tailwind CSS
(tailwindcss.com), Bootstrap (getbootstrap.com), Bulma (bulma.io), Pico.css
(picocss.com), Open Props (open-props.style).

**Color tools** — palettes, contrast, scales: Coolors (coolors.co), Adobe Color
(color.adobe.com), Happy Hues (happyhues.co), uicolors.app (Tailwind scales),
Khroma (khroma.co), ColorSpace (mycolor.space).

**Fonts / typography** — pairings and licensing: Google Fonts (fonts.google.com),
Fontshare (fontshare.com), Fontpair (fontpair.co), Fontjoy (fontjoy.com), Bunny
Fonts (fonts.bunny.net). Prefer fonts the renderer can fetch (Quarto pulls Google
fonts; otherwise vendor the files into a brand's `assets/fonts/`).
