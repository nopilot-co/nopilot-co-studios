---
name: viz-frameworks
description: How to execute strategic framework visualisations in the design studio — bullseye (concentric priorities), 2x2 matrix (quadrants), and funnel — their `::: ` authoring syntax, current render status (not-yet-built — Phase 2), and the normalised CSV each ships into the docket today for data editors like nopilot.co. Use when composing source.md with a bullseye, matrix, or funnel.
---

# viz-frameworks — bullseye · matrix · funnel

Strategy / marketing frameworks. All three render via `studio.frameworks`
(matplotlib SVG, HTML + PDF) and **also ship their data as CSV** in the docket.

## When to use which
- **bullseye** — rank items by priority / proximity in concentric rings (core →
  adjacent → future).
- **matrix** — place items on two axes into four quadrants (e.g. effort × impact).
- **funnel** — ordered stages that narrow (pipeline / conversion).

## Authoring syntax
```markdown
::: bullseye
rings:
  - {ring: core, items: [Beachhead segment]}
  - {ring: adjacent, items: [Secondary segment]}
:::

::: matrix
axes: {x: Effort, y: Impact}
items:
  - {label: Quick win, x: low, y: high, quadrant: Do now}
:::

::: funnel
stages:
  - {stage: Visitors, value: 10000}
  - {stage: Signups, value: 1200}
:::
```

## Engine & tool
`studio.frameworks` (matplotlib) → one brand-styled SVG, identical in HTML and
PDF (`#image()`): bullseye = concentric rings, matrix = points on two axes split
into quadrants, funnel = centred bars narrowing by value. **Live.** PPTX-native
shapes are a follow-up; the CSV sidecar ships on every export regardless.

## Normalised CSV (shipped to the docket)
One `<viz-id>.csv` each, long form, in `version.json`'s `data[]`:

| type | columns |
|------|---------|
| bullseye | `viz_id, type, item, ring, value` |
| matrix | `viz_id, type, item, x_axis, y_axis, quadrant, value` |
| funnel | `viz_id, type, stage, order, value` |

**nopilot.co** edits these directly — the data is usable before the picture
exists.

## Cross-studio sources
**commercial** (opportunity sizing → funnel), **growth** (positioning →
matrix / bullseye), **principal** (scoping priorities → bullseye).

## Gotchas
- HTML + PDF render today; PPTX-native shapes are a follow-up.
- `bullseye` accepts `rings: [{ring, items}]` or a flat `items: [{label, ring}]`
  (first ring = centre); `matrix` accepts `items: [...]` or
  `quadrants: [{quadrant, items}]`; matrix x/y take `low`/`med`/`high` or a 0–1 number.

## Status
Live (HTML + PDF). CSV sidecar: always.
