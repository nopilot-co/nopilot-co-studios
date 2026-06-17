---
name: viz-tables
description: How to execute data tables in the design studio — when a table beats a chart, the markdown pipe-table syntax, the native HTML / PDF / PPTX table renderer, and the verbatim CSV every table ships into the docket for data editors like nopilot.co. Use when composing source.md that contains a table.
---

# viz-tables — data table

Exact values, lookups, or many dimensions that resist a chart.

## When to use
Reach for a table when the reader needs **precise figures** or row-by-row
comparison; reach for a chart (`viz-charts`) when the *shape* of the data is the
message.

## Authoring syntax
A standard GitHub-flavoured markdown pipe table — no fenced div:
```markdown
| Region | Q1  | Q2  |
|--------|-----|-----|
| EMEA   | 120 | 140 |
| AMER   | 90  | 160 |
```

## Engine & tool
Quarto styles it as a `.data-table` for HTML / PDF; `studio.pptx_render` builds a
**native editable PowerPoint table**. **Status: live.**

## Normalised CSV (shipped to the docket)
`studio render` writes `outputs/<session>/data/<viz-id>.csv` **verbatim** — the
header row + data rows exactly as authored — and records it in `version.json`'s
`data[]`. A data editor (**nopilot.co**) edits the CSV directly; re-rendering the
edited table is a downstream step.

## Cross-studio sources
Any studio's tabular output — analytics rollups, commercial rate cards, delivery
RAID registers — can be authored as a table here so its data round-trips as CSV.

## Gotchas
- Keep one header row + a `|---|` separator line; cells are split on `|` as-is.
- A pipe table inside a ``` code fence is treated as an example and **not**
  exported (so doc samples don't leak into the docket).

## Status
Live. CSV sidecar: always (verbatim).
