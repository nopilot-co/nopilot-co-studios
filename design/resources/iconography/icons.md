# Iconography — library

**Interchangeable SVG icon sets** for use in studio designs. A design picks
**one** set so its icons stay visually consistent; because every set is
referenced by the same icon *names* where possible, swapping sets is mechanical.

## Convention (how a set is used and replicated)

1. A design references an icon set by slug (e.g. `lucide`).
2. To make a set usable offline and reproducible, **vendor it** into its own
   folder here:
   ```
   iconography/<set>/
     icons/<name>.svg     # the SVG files, named by the set's canonical names
     SOURCE.md            # upstream URL, version/commit, license, how it was pulled
   ```
3. Designs embed icons by `<set>/<name>` (e.g. `lucide/arrow-right`). Re-skinning
   to another set is renaming the prefix — same names, different art.

> Only the catalog (this file) is committed by default. Vendor a set's SVGs when
> a design actually needs them, recording provenance in `SOURCE.md` so the choice
> is 100% replicable.

## Recommended default

**Lucide** — open-source, ~1,368 icons, clean/consistent/lightweight, 24px grid,
distributed as SVGs and npm packages. The community fork of Feather; the safest
neutral default for documents, decks, and web. Source: https://lucide.dev

## Brand locks

A brand may **canonically lock** its icon set so it is no longer a per-design
choice. The lock lives in the brand's `tokens.yaml` `icon` group (`set`, `stroke`,
`size`) — the single source of truth — not here; this is the human cross-reference.

| Brand | Set | Stroke | Source of truth |
|-------|-----|--------|-----------------|
| nopilot | `lucide` | 1.5px (to match the altimeter) | `~/context/studios/brand/nopilot/tokens.yaml` → `icon` |

## Catalog (open-source SVG sets, interchangeable)

Prefer permissively licensed sets (MIT / ISC / open source) for embedding.
(Curated from [Untitled UI — free icon sets](https://www.untitledui.com/blog/free-icon-sets).)

| Set | Slug | Icons | License | Style | Source |
|-----|------|-------|---------|-------|--------|
| Lucide | `lucide` | ~1,368 | ISC (open) | Clean, consistent, lightweight | lucide.dev |
| Feather | `feather` | 287 | MIT | Minimal, light stroke | feathericons.com |
| Heroicons v2 | `heroicons` | 1,152 | MIT | Outline / solid / mini | heroicons.com |
| Phosphor | `phosphor` | 7,488 | MIT | 6 weights: thin→fill, duotone | phosphoricons.com |
| Tabler | `tabler` | 4,900+ | MIT | Variable stroke, broad coverage | tabler.io/icons |
| Radix Icons | `radix` | 333 | MIT | Sharp, 15×15 UI-optimized | radix-ui.com/icons |
| Iconoir | `iconoir` | 1,544 | MIT | Pared-back, super minimal | iconoir.com |
| Remix Icon | `remix` | 2,700+ | Apache-2.0 | Line + solid, neutral | remixicon.com |
| Bootstrap Icons | `bootstrap` | 1,800+ | MIT | General-purpose UI | icons.getbootstrap.com |
| Material Symbols | `material` | 2,500+ | Apache-2.0 | Variable, Google system | fonts.google.com/icons |
| Ionicons | `ionicons` | 1,300+ | MIT | Outline / filled / sharp | ionic.io/ionicons |
| Simple Icons | `simple` | 3,000+ | CC0 | Brand/logo glyphs | simpleicons.org |

Specialty / non-MIT (use deliberately, check terms): Untitled UI Icons (CC,
1,100+), Majesticons (MIT, 720), MingCute (open, 2,212), Eva (open, 480),
Doodle Icons (CC, hand-drawn).

## Choosing a set

- **Documents / decks / proposals:** Lucide or Heroicons — neutral and legible at
  print sizes.
- **Dense dashboards / UI mockups:** Tabler or Radix — tight, UI-tuned.
- **Expressive / multiple weights:** Phosphor — six weights from one family.
- **Brand/logo marks:** Simple Icons.

Keep one set per design. Mixing sets breaks the consistency this folder exists to
guarantee.
