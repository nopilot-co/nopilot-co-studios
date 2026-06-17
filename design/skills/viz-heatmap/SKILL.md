---
name: viz-heatmap
description: How to execute heatmap / RAG-grid visualisations in the design studio — the rows×cols cell-grid syntax (with an optional `rag: true` flag), current render status (not-yet-built — Phase 2), and the normalised per-cell CSV it ships into the docket today for data editors like nopilot.co. Use when composing source.md with a heatmap or RAG status grid.
---

# viz-heatmap — heatmap · RAG grid

A grid of cells coloured by magnitude (heatmap) or by red/amber/green status
(RAG). Renders via `studio.frameworks` (matplotlib SVG, HTML + PDF) and **also
ships its data as CSV** in the docket.

## When to use
- **heatmap** — magnitude across two categorical axes (intensity).
- **RAG grid** — status across a grid; set `rag: true` so cells are
  red/amber/green statuses rather than numbers.

## Authoring syntax
```markdown
::: heatmap
rows: [Team A, Team B]
cols: [Q1, Q2]
cells:
  - [0.8, 0.3]
  - [0.5, 0.9]
:::

::: heatmap
rag: true
rows: [Team A, Team B]
cols: [Q1, Q2]
cells:
  - [green, red]
  - [amber, green]
:::
```
A `data:` list of `{row, col, value, rag}` also works.

## Engine & tool
`studio.frameworks` (matplotlib) → a coloured cell grid as one brand-styled SVG,
identical in HTML and PDF (`#image()`). Magnitude cells are tinted by value;
`rag: true` maps cells to discrete red/amber/green. **Live** (HTML + PDF;
PPTX-native is a follow-up).

## Normalised CSV (shipped to the docket)
One `<viz-id>.csv`, one row per cell, in `version.json`'s `data[]`:
```
viz_id,type,row,col,value,rag
12-heatmap,heatmap,Team A,Q1,,green
```
With `rag: true` the status lands in `rag` and `value` is blank; otherwise the
magnitude lands in `value`. **nopilot.co** edits the grid directly.

## Cross-studio sources
**delivery** (RAID / RAG status), **nitpicker** / **audience** (scored rubrics →
heatmap), **analytics** (correlation / intensity grids).

## Gotchas
- `cells` is row-major (`cells[r][c]` = row r, col c); ragged rows fill blank.
- `rag: true` switches cell semantics from magnitude to status colour.

## Status
Live (HTML + PDF). CSV sidecar: always.
