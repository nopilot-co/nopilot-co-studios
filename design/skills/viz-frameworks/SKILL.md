---
name: viz-frameworks
description: How to execute strategic framework visualisations in the design studio — bullseye (concentric priorities), 2x2 matrix (quadrants), and funnel — their `::: ` authoring syntax, current render status (not-yet-built — Phase 2), and the normalised CSV each ships into the docket today for data editors like nopilot.co. Use when composing source.md with a bullseye, matrix, or funnel.
---

# viz-frameworks — bullseye · matrix · funnel

Strategy / marketing frameworks. **All three renderers are NOT-YET-BUILT**
(Phase 2): they show a visible fallback panel today, but **ship their data as
CSV now** — so author them and the numbers are captured and editable downstream.

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
**NOT-YET-BUILT** — Phase 2 will add `frameworks.py` (bullseye rings, 2×2
scatter-on-quadrants, stacked funnel → SVG / native PPTX). Until then each
renders a visible fallback panel; the CSV sidecar ships regardless.

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
- These do not render yet — set expectations; the CSV is the deliverable today.
- `bullseye` accepts `rings: [{ring, items}]` or a flat `items: [{label, ring}]`;
  `matrix` accepts `items: [...]` or `quadrants: [{quadrant, items}]`.

## Status
CSV-only (renderer Phase 2).
