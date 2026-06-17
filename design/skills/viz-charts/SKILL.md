---
name: viz-charts
description: How to execute the statistical charts (bar, line, pie, scatter, area) in the design studio — when to use each, the exact `::: chart` authoring syntax, the matplotlib / native-PPTX engine that renders them, and the normalised long-form CSV every chart ships into the docket for data editors like nopilot.co. Use when composing source.md that contains a chart.
---

# viz-charts — bar · line · pie · scatter · area

Quantitative comparisons, authored as a `::: chart` fenced div (structured YAML,
never raw matplotlib). One engine and one CSV schema serve all five.

## When to use which
- **bar** — compare a value across categories; multi-series → grouped bars.
- **line** — a trend over an ordered x (time, stages).
- **area** — a line whose volume/magnitude matters (filled).
- **pie** — parts of a whole (≤ 6 slices; prefer bar otherwise).
- **scatter** — relationship between two numeric series / a distribution.

## Authoring syntax
```markdown
::: chart
type: bar            # bar | line | pie | scatter | area
title: Revenue
x: [Q1, Q2, Q3, Q4]
y: [12, 18, 15, 24]
:::

::: chart
type: line
title: Monthly revenue
x: [Q1, Q2, Q3, Q4]
series:
  - {name: Product, y: [10, 14, 18, 22]}
  - {name: Services, y: [5, 7, 6, 9]}
:::

::: chart
type: pie
labels: [A, B, C]
values: [30, 50, 20]
:::
```

## Engine & tool
`studio.charts` → one brand-styled **matplotlib SVG**, identical in HTML and PDF;
PPTX builds a **native editable chart** via `studio.pptx_render`. Brand tokens
colour the series automatically — never hand-set colours. **Status: live.**

## Normalised CSV (shipped to the docket)
`studio render` writes `outputs/<session>/data/<viz-id>.csv` in **long / tidy
form** — one row per (series, x-point) — and records it in `version.json`'s
`data[]`:

```
viz_id,type,series,x,y
01-bar,bar,Plan,Q1,10
01-bar,bar,Actual,Q1,12
```

Pie folds into the same columns (`series` = `x` = slice label, `y` = value);
multi-series is native (a block of rows per series). This is exactly what a data
editor like **nopilot.co** loads to edit the numbers behind the chart. You never
write the CSV by hand — it is emitted from the authored YAML on **every export**.

## Cross-studio sources
The **analytics** studio emits viz specs (chart type + fields + caption) and the
**planner** hands them to design; author the `::: chart` from that spec.

## Gotchas
- The multi-series key is **`name`**, not `label` — `{name: Product, y: [...]}`.
  A `label:` is silently dropped by the engine and lands as an empty series in
  the CSV.
- `scatter` has no real x unless you supply numeric `x`; otherwise the CSV `x` is
  the ordinal index. Keep each series the same length as `x`.

## Status
Live (renders today). CSV sidecar: always.
