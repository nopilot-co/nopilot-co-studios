# Design — data-viz engine (unified SVG: bar, line, pie, scatter, area)

- **Date:** 2026-06-02
- **Status:** approved design → spec
- **Issue:** #20 (data-viz). Sibling of slice 4a (diagrams).
- **Scope:** Layer 3 (rendering) — chart asset `::: chart` rendered to HTML + PDF with true parity via ONE engine.

## Goal

Render data-driven charts (bar, line, pie, scatter, area/stacked) as designed,
on-brand elements in HTML and PDF, from one structured-YAML authoring convention —
with **identical output on both sides** (not two engines approximating each other).

## Spike results (all gating questions answered — do not re-spike)

1. **Mermaid/cetz split fails parity:** Mermaid (HTML) has **no scatter or area**
   chart type, while cetz-plot (PDF) does. A two-engine approach can't give parity
   for 2 of the 5 requested types. → rejected.
2. **Unified SVG works:** matplotlib (one engine) emits SVG for all 5 types.
   - HTML: inline the SVG (native, embed-resources inlines it).
   - PDF: Typst `#image("chart.svg")` — **verified in pixels**: a matplotlib bar
     chart rendered through Typst into PDF with full fidelity (clean axes,
     proportional bars, brand navy, crisp text — Typst's SVG text handling, the
     usual failure mode, held up).
3. **All 5 types** are native matplotlib (bar/line/pie/scatter/stackplot).
4. **Brand-styleable** via matplotlib colour/style args from the resolved tokens.

→ **Decision: one SVG engine (matplotlib), same SVG rendered into both targets.**
True parity, no per-type engine divergence. Cost: one new Python dependency
(matplotlib), handled by the studio's declare/detect/degrade pattern.

## Architecture

### A. New module `studio/charts.py`

- **Input:** the chart class body YAML + the resolved token set.
- **Produces:** an SVG file (matplotlib) styled with brand tokens, returned as a
  path/bytes for the caller to place.
- Chart spec shape (authored as a fenced div `::: chart`):
  ```yaml
  type: bar          # bar | line | pie | scatter | area
  title: Revenue
  x: [Q1, Q2, Q3, Q4]            # categories / x values
  y: [12, 18, 15, 24]           # single series
  # or multi-series:
  series:
    - {name: Plan, y: [10, 14, 12, 20]}
    - {name: Actual, y: [12, 18, 15, 24]}
  ```
  - `bar`/`line`/`area`/`scatter`: `x` + (`y` or `series`).
  - `pie`: `labels` + `values` (or reuse `x`/`y`).
- **Tokenization:** series colours cycle through `[tertiary, primary, secondary,
  surface...]`; title/axis/text use `primary`/`secondary`; figure background
  transparent so it sits on any page. Built from the token dict, no hardcoded hex.
- **Malformed YAML / unknown type:** a visible fallback panel (mirror
  `diagrams._fallback`), never crash the render.

### B. Expansion — `studio/diagrams.py` already owns the preprocess seam

`charts` is a NON-diagram visual that produces an artifact file, so it integrates
at the **same render.py preprocess point** but differently from diagrams (which
emit inline source). Two clean options; the spec picks **B2**:

- B1 (rejected): expand in `diagrams.expand` — but charts emit a *file*, not source
  text, and need a writable dir; conflates two concerns.
- **B2 (chosen): a dedicated `charts.expand(markdown, export, tokens, out_dir)`**
  called in `render.py` right after `diagrams.expand`. It finds `::: chart` divs,
  renders each to `out_dir/_chart-N.svg`, and replaces the div with:
  - HTML: `![](_chart-N.svg)` (Quarto inlines it with embed-resources), or a raw
    `<img>` — whichever embeds cleanly (verify in the task).
  - PDF: a `{=typst}` block `#image("_chart-N.svg", width: 100%)` (or a markdown
    image — verify which Typst path keeps the SVG vector).
  `out_dir` is the render tmp dir (`tmp`), already where source.md is written.

### C. Wiring (`render.py`)

After the `diagrams_mod.expand` line, add:
```python
body = charts_mod.expand(body, sfmt, tok, tmp)
```
(`tmp` is the writable render project dir; charts land beside source.md.)

### D. Dependency declaration (declare/detect/degrade)

- matplotlib is **Python**, so unlike Quarto/Typst it CAN be a normal dep — add to
  `design/scripts/pyproject.toml` dependencies.
- Detected: if import fails, `charts.expand` degrades each chart to the fallback
  panel with an install hint (never crashes). `studio doctor` notes it.
- No native-tool/network concern (unlike fletcher) — it's a wheel.

### E. Asset contract

`design/formats/assets/data-viz.yml` already exists (slice 1). Update its
`authoring.syntax` to the `::: chart` YAML form and `render_notes` to name the
unified SVG engine. Already `buckets: [documents, decks]`, `exports:
[pptx,gslide,html,pdf]` — charts render html/pdf today (pptx/gslide later).

## Testing / verification

- `tests/test_charts.py` (standalone): for each of the 5 types, `charts.render_svg`
  returns valid SVG containing the data/title; brand colour present; multi-series
  handled; bad type → fallback (no exception). `charts.expand` replaces the div per
  export (HTML `<img>`/`![]`, PDF `#image`), writes the SVG file, passes other divs
  through.
- **Pixel verification (the bar):** render a doc with all 5 chart types to BOTH
  `*-pdf` and `*-html` (360 brand), rasterize the PDF + screenshot/inspect, CONFIRM
  each chart reads as a clean, on-brand, correct chart. Not "it compiled."
- All existing suites stay green.

## File manifest

**New:** `design/scripts/studio/charts.py`; `tests/test_charts.py`.
**Edited:** `design/scripts/studio/render.py` (charts.expand call); `design/scripts/pyproject.toml` (+matplotlib); `design/formats/assets/data-viz.yml` (authoring); `design/scripts/studio/cli.py` doctor note (optional); `design/formats/README.md` (chart authoring).

## Out of scope

- Charts in **pptx/gslide** (an editable-chart object is a slice-4b-class problem;
  flat SVG-on-slide could come later, but parity here means html+pdf only now).
- Interactive/animated charts (static SVG only).
- Per-session design-system selection (#21).

## Risks

- **matplotlib font in SVG:** by default matplotlib may embed text as `<text>` (good
  — Typst renders it) OR as paths. Spike used default `<text>` and it rendered; the
  task must keep `svg.fonttype` default (not "path") and verify text stays crisp.
- **embed-resources + external SVG file:** confirm Quarto inlines the `_chart-N.svg`
  into the standalone HTML (it inlines local images; verify in the pixel task — if
  not, base64 data-URI the SVG inline).
- **matplotlib install weight:** ~30MB wheel + numpy. Acceptable as a normal Python
  dep; degrade-on-missing keeps render working without it (charts → fallback panel).
