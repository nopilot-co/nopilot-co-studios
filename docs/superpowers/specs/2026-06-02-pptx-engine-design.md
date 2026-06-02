# Design — editable PPTX engine (parallel render path, native shapes)

- **Date:** 2026-06-02
- **Status:** approved design → spec
- **Issue:** #19 (slice 4b). Closes the slice-4 umbrella (#17) when landed.
- **Scope:** A parallel python-pptx render path for the `pptx` (and later `gslide`) export — native **editable** shapes, not flat images.

## Goal

Render the SAME `::: ` block source (components, charts, diagrams) to a `.pptx`
where every element is a **native, editable PowerPoint object** (text boxes,
native charts, native tables, autoshapes + connectors) — brand-tokenized — so a
user can open the deck and move/recolour/edit shapes. Honours the studios
invariant: same source, different render host.

## Spike results (proven — do not re-spike)

- python-pptx 1.0.2 (already a dependency) builds **native chart objects**
  (`MSO_SHAPE_TYPE.CHART`, editable — verified, not a picture), **native tables**,
  **autoshapes** (rectangles/etc.), and styled **text boxes**.
- libreoffice (already present, used for QA) renders the PPTX → PDF correctly
  (verified in pixels: native column chart + table on a 16:9 slide).
- → The architecture is viable. The only "hard tier" is diagrams as native shapes
  (boxes + connectors with computed layout), addressed last.

## Architecture

### A. Parallel render path in `render.py`

Today `render()` always drives Quarto. Add a fork **before** the Quarto project
materialization:
```python
if sfmt == "pptx":   # (gslide later, via pptx then import)
    return pptx_render.render(session_path, slug, tok, new_version, ...)
# else: existing Quarto path (html/pdf/revealjs)
```
The pptx path reads the SAME `inputs/source.md` (after `metacontent.strip` — but
NOT `diagrams.expand`/`charts.expand`, which emit Quarto/Typst/Mermaid; the pptx
engine consumes the raw `::: ` blocks itself), versions the output identically,
and records to `version.json` the same way. So sessions, versioning, brand import,
and the count ruleset (`max_slides`) all work unchanged.

### B. New module `studio/pptx_render.py`

A deterministic Markdown→PPTX builder:

- **Parse** `source.md` into a slide list. Convention: a top-level `#`/`##` heading
  or a `::: cover-slide` / `::: section-slide` block starts a new slide; content
  between starts accumulates onto the current slide. (A simple, documented slide-
  splitting rule — decks are low-density, one idea per slide.)
- **Block → native shape** dispatch (mirrors the component vocabulary):
  | `::: ` block / element | PPTX native shape |
  |---|---|
  | `cover-slide` | full-bleed neutral rectangle + title/subtitle text boxes |
  | `section-slide` | surface rectangle + title text box |
  | `kpi` | surface rounded rectangle + large accent figure text |
  | `pullquote` / `callout` / `highlight` / `panel` | rounded rectangle (fill/accent per type) + text |
  | `stat-panel` | surface tile + figure text |
  | Markdown table | **native table** (`add_table`), branded header row |
  | `::: chart` (YAML) | **native chart** (`add_chart`) — reuse the chart spec parser from `charts.py`, brand colours via chart format |
  | `::: flow`/`process`/`timeline`/`hierarchy`/`org` | **autoshapes + connectors** using the computed layout from `diagrams.py` (`_flatten_tree` etc.) — hardest tier, last |
  | headings / paragraphs / bullets | title placeholder + body text frame with bullet levels |
- **Brand tokens:** a small `_pptx_tokens` adapter turns the resolved token dict
  into `RGBColor`s + point sizes; every shape fill/text uses them (no hardcoded
  hex). Reuse `tokens.resolve(slug)`.
- **Reuse, don't duplicate:** import `charts._series`/spec parsing and
  `diagrams._flatten_tree` so chart/diagram *data parsing + layout* is shared; only
  the *emission* (native shapes vs SVG/Mermaid) is new.

### C. Slides + layout

- 16:9 (`Inches(13.333) x Inches(7.5)`), blank layout (`slide_layouts[6]`) so we
  place shapes deterministically (no template placeholder fighting).
- A reference.pptx (brand master) is already copied into sessions; v1 uses the
  blank layout + token styling. (Using the brand master's theme is a later
  refinement.)

### D. gslide (deferred within this issue or a fast-follow)

`gslide` = produce the PPTX, then import to Google Slides (Slides API / Drive
import). The PPTX engine is the prerequisite; the import is a separate, auth-bound
step. This spec delivers **pptx**; gslide flips on once the engine is solid
(noted, not faked — `gslide` stays `studio_format: null/planned` until then).

## Implementation tiers (each pixel-verified before the next)

1. **Foundation:** the render fork + slide splitting + text (headings/bullets) +
   cover-slide/section-slide. Verify a basic branded deck.
2. **Tiles & panels:** kpi, stat-panel, pullquote/callout/highlight/panel, native
   table. Verify.
3. **Native chart:** `::: chart` → `add_chart`, brand-coloured. Verify.
4. **Diagrams (hard tier):** flow/process/timeline/hierarchy/org as autoshapes +
   connectors via the shared layout. Verify — **if this proves too deep for one
   pass, ship tiers 1–3 and split tier 4 into a follow-up issue (logged, not
   faked).**

## Testing / verification

- `tests/test_pptx.py` (standalone): build a deck from a sample `source.md`; assert
  the `.pptx` has the expected slide count, that a chart slide has a NATIVE chart
  object (`shape.has_chart`), a table slide a native table, and panels are
  autoshapes (not pictures); brand colour present on a shape fill; bad chart YAML →
  the slide still builds (degrade, no crash).
- **Pixel verification (the bar):** render the deck to `.pptx`, convert via
  libreoffice → PDF, rasterize, inspect each tier's slides — confirm native,
  on-brand, correct. Not "it saved".
- All existing suites stay green; the html/pdf path is untouched.

## File manifest

**New:** `design/scripts/studio/pptx_render.py`; `tests/test_pptx.py`.
**Edited:** `design/scripts/studio/render.py` (the pptx fork); `design/formats/README.md` (pptx authoring note); possibly small `charts.py`/`diagrams.py` refactors to export the shared parse/layout helpers cleanly.

## Out of scope

- **gslide import** (separate auth-bound step; pptx is the deliverable).
- Animations/transitions, speaker notes styling, master-theme inheritance (v1 uses
  blank layout + tokens).
- Editable-in-Slides fidelity beyond what PPTX import gives.

## Risks

- **Slide-splitting heuristic** can mis-group dense source. Mitigation: a clear,
  documented rule (heading/cover/section starts a slide); decks are low-density by
  contract (`max_words_per_view`).
- **Diagrams as native shapes (tier 4)** is the real unknown — connector routing
  and tree layout in EMU coordinates. The tiered plan isolates it; honest split if
  it resists.
- **libreoffice theme colours** in the QA PDF differ slightly from PowerPoint's
  native rendering — acceptable (QA is for layout/branding sanity, the .pptx is the
  deliverable).
