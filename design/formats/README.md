# Formats

A **format** is a canonical design-studio entity: a *purpose* (what the asset is
for) crossed with an *export* (the asset type it ships as). It is named by a slug
`<purpose>-<export>` — e.g. `pitch-pdf`, `pitch-html`, `proposal-pdf`.

The point is to **centralise intent and vary output**: the `pitch` purpose owns
the style guide, execution brief, and ruleset once; each export (`pdf`, `html`,
`pptx`, …) layers on only what differs about shipping that asset type.

## Layout

```
formats/
  purposes/<purpose>.yml   # core intent: style_guide, execution_brief, ruleset
  exports/<export>.yml     # asset-type specifics: render config + style/ruleset deltas
  <purpose>-<export>.yml   # a format contract: composes the two + optional overrides
```

## Composition

A format slug resolves by deep-merging, in order:

1. `purposes/<extends>.yml`  (base — the first key in the slug)
2. `exports/<export>.yml`    (overlay — the second key)
3. the slug file's `overrides:` block (top)

Rule: dictionaries merge recursively; scalars and lists from a later layer
replace earlier ones. Resolution and validation live in
`../scripts/studio/formats.py`; the resolved shape is validated against
`../scripts/studio/schemas/format.schema.json`.

```yaml
# pitch-pdf.yml
extends: pitch
export: pdf
overrides:
  ruleset:
    max_pages: 12
```

## The three components

- **style_guide** — how it should look and read (voice, density, layout).
- **execution_brief** — what it must accomplish (objective, audience, the
  `required_sections` it must contain).
- **ruleset** — the enforceable constraints (`required_sections`, `max_pages`,
  `max_slides`, `must_include_cta`, …). Count-based rules (`max_pages`,
  `max_slides`) are checked deterministically at render time; the rest are
  enforced by the `visual-qa` skill against the resolved contract.

## Lifecycle

Every design session **locks in exactly one format slug** at `session-init`
(`studio session init --format <slug>`, stored in `version.json`). `render`
derives the single export to produce from that slug and enforces the count
rules; `visual-qa` critiques the output against the full resolved contract.
One session = one format = one asset. Want the same pitch as both PDF and HTML?
That's two sessions: `pitch-pdf` and `pitch-html`.

## CLI

```
studio formats list
studio formats show --format pitch-pdf      # the resolved contract
studio formats validate --format pitch-pdf
```

## Status

`pdf`, `html`, `pptx`, and `revealjs` exports are renderable today. `glide`
(`asset_type: app`) is a canonical contract only — `studio render` refuses it
until a Glide export pipeline exists.

## Buckets

Formats are organised into three buckets by audience and output shape:

- **A · Editorial** — short-form publishing. Purposes: `post`, `article`.
  Exports: `html`.
- **B · Documents** — long-form written deliverables. Purposes: `proposal`,
  `whitepaper`, `sow`. Exports: `html`, `pdf`.
- **C · Decks** — visual presentations. Purposes: `pitch`, `presentation`,
  `report`, `status`, `approach`. Exports: `pptx`, `gslide`, `html`, `pdf`.
  Note: `gslide` is a contract-only export — rendering is not yet built.

## Asset library

Assets live in `formats/assets/<slug>.yml` (one file per asset type — e.g.
`pullquote`, `cover`, `data-table`). Key properties:

- **Token-referenced** — values such as `{colors.tertiary}` resolve against the
  active design-system at render time.
- **Authored in Markdown** — as Quarto fenced divs (e.g. `::: pullquote`).
- **Scoped to buckets and exports** — each asset declares which buckets and
  exports it supports; a format may only reference an asset that supports its
  export.
- **Referenced by format** — a format lists the assets it may include via its
  `assets:` key; `validate_asset_refs` checks these at validation time.

List and inspect assets with `studio formats assets`. Validate a format's asset
references with `studio formats validate --format <slug>`.

### Diagrams

Five diagram classes are available: `flow`, `process`, `timeline`, `hierarchy`,
and `org`. Each is authored as a fenced div whose body is structured YAML —
not raw Mermaid or Typst. The engine (`studio.diagrams`) expands the YAML per
the session's locked export: **Mermaid** for HTML exports, **Typst fletcher**
for PDF exports. Node and edge styles resolve against the active design-system
tokens (`{colors.*}`) so diagrams stay brand-consistent automatically.

```markdown
::: flow
nodes: [Brief, Plan, Render, Review]
:::

::: timeline
events:
  - {at: Q1, label: Kickoff}
  - {at: Q2, label: Beta}
  - {at: Q3, label: GA}
:::

::: hierarchy
root: Strategy
children:
  - root: Pillar A
    children: [Initiative 1, Initiative 2]
  - Pillar B
:::
```

`flow` and `process` generate left-to-right node chains; `timeline` generates
a horizontal axis with period markers; `hierarchy` and `org` generate top-down
trees with computed coordinates.

### Charts (data-viz)

Charts are authored as `::: chart` fenced divs whose body is structured YAML.
`type` must be one of `bar`, `line`, `pie`, `scatter`, or `area`. Supply either
`x`/`y` arrays for a single series, or a `series:` list for multi-series data.
`title` is optional.

```markdown
::: chart
type: bar
x: [Q1, Q2, Q3, Q4]
y: [12, 18, 15, 24]
:::

::: chart
type: line
title: Monthly revenue
series:
  - {label: Product, y: [10, 14, 18, 22]}
  - {label: Services, y: [5, 7, 6, 9]}
x: [Q1, Q2, Q3, Q4]
:::
```

`studio.charts` renders the YAML to a single **matplotlib SVG**. HTML exports
embed it inline; PDF exports place it via Typst `#image()`. Both sides produce
identical output — no per-export branching.

### Visualisation catalogue

Every canonical visualisation has a how-to skill in `../skills/viz-<family>/` —
when to use each type, the exact `::: ` syntax, the engine, and the CSV it ships:

| Family | Types | Skill | Engine today |
|--------|-------|-------|--------------|
| Charts | bar, line, pie, scatter, area | `viz-charts` | live (matplotlib · native PPTX) |
| Tables | data table | `viz-tables` | live (Quarto · native PPTX) |
| Process-flow | flow, process, timeline, swimlane\*, decision-tree\* | `viz-process-flow` | flow/process/timeline live; \* Phase 2 |
| Hierarchy | hierarchy, org | `viz-hierarchy` | live |
| Frameworks | bullseye\*, matrix\*, funnel\* | `viz-frameworks` | \* Phase 2 |
| Heatmap | heatmap / RAG\* | `viz-heatmap` | \* Phase 2 |

`*` = authoring + CSV ship today; the renderer is Phase 2 (a visible fallback
panel renders until then). Each asset's machine contract lives in
`assets/<type>.yml`.

### Data export (normalised CSV)

Whatever the studio draws, `studio render` also writes the **underlying data as a
normalised (tidy / long-form) CSV** into the docket —
`outputs/<session>/data/<viz-id>.csv` (diagrams: `<viz-id>.nodes.csv` +
`.edges.csv`) — and records a manifest in `version.json`'s `data[]`
(`{viz_id, type, family, files, rows, page_key, engine, rendered}`). This lets a
downstream **data editor (nopilot.co)** pick up and edit the numbers behind any
visualisation. The CSV is emitted from the authored YAML on **every export**
(html / pdf / pptx / revealjs) and even for the Phase-2 types that don't render
yet (`rendered: false`). The pass never fails a render. Source:
`scripts/studio/viz_data.py`; schema: `scripts/studio/schemas/viz-data.schema.json`.

### PPTX (native editable decks)

`pptx` exports do **not** go through Quarto. `studio.pptx_render` builds the deck
shape-by-shape into a real `.pptx` of **native, editable PowerPoint objects** —
not flat images — from the same `::: ` block source:

- A `#`/`##` heading or a `::: cover-slide` / `::: section-slide` block starts a
  new slide; content accumulates onto the current slide.
- `::: kpi` / `::: panel` / `::: highlight` / `::: stat-panel` → branded
  autoshapes; markdown tables → **native tables**; `::: chart` → a **native
  editable chart**; `::: flow` / `process` / `timeline` / `hierarchy` / `org` →
  native autoshapes + connectors (shared layout with the HTML/PDF diagram engine).

Every shape is brand-tokenized, so a user can open the deck and move/recolour/edit
it. `gslide` (Google Slides import of the PPTX) is a separate, not-yet-wired step.

## Output-folder convention

Docket render outputs flatten to `outputs/<primary>/<file>` — there is no
redundant `<format>/` sub-folder. The format is already encoded in the filename
(e.g. `client-proposition-pitch-pdf-v1.0.0.pdf`), so adding a folder layer
would be redundant.
