# Design — Slice 4a: structured-diagram engine + deck-visual components

- **Date:** 2026-06-01
- **Status:** approved design → spec
- **Scope:** Layer 3 (rendering), decks bucket — diagrams + deck-visual components in **HTML + PDF**. Editable PPTX/gslide is **slice 4b** (separate engine, not here).

## Goal

Render the decks bucket's visual asset types as **designed, on-brand** elements in HTML and PDF, from one structured authoring convention — completing the rendering program for HTML/PDF across all three buckets. The hard part is diagrams (flow/timeline/process/hierarchy/organigram), which need structured input and different engines per target.

## Spike result (already proven)

- **PDF:** Typst **fletcher** (`@preview/fletcher`) renders a branded flow diagram (navy nodes, red arrows, rounded) — pixels verified. Network fetch of the package works.
- **HTML:** Quarto renders **Mermaid** fenced blocks to inline SVG natively (no external deps; needs `.qmd`-style executable handling, which Quarto does inside a project).
- **Conclusion:** parity is achievable, but the two engines take different input languages, so a thin Lua wrapper (slice-2 model) won't do. Use a **target-aware Python expansion** instead.

## Architecture

### The insight: expand at preprocess time, not Quarto time

`render.py` already knows the **single locked export** for the session (pdf | html). So diagram generation happens in Python, before Quarto runs, targeting the known export:

- `::: flow` + YAML  →  **HTML target:** a ` ```mermaid ` block  ·  **PDF target:** a ` ```{=typst} ` block of fletcher code.

This is clean, unit-testable Python (no Lua YAML parsing), and reuses the existing preprocess pipeline (`metacontent.strip` already rewrites `source.md` before render).

### A. New module `studio/diagrams.py`

- **Input:** the stripped source markdown + the target export (`"html"` | `"pdf"`) + the resolved token set (for brand colours).
- **Finds** fenced divs of the diagram classes and parses their YAML body.
- **Emits**, per target, the engine block that replaces the div.
- Diagram classes + their YAML shape:
  - `flow` — `{nodes: [A, B, C], style: linear|branch}` → Mermaid `flowchart LR`; fletcher linear chain.
  - `timeline` — `{events: [{at: "Q1", label: "..."}]}` → Mermaid `timeline`; fletcher horizontal axis with markers.
  - `process` — `{steps: [..]}` → numbered sequence (Mermaid flowchart; fletcher numbered nodes).
  - `hierarchy` / `org` — `{root: X, children: [...]}` (nestable) → Mermaid `flowchart TD`; fletcher tree.
- **Tokens:** node fill = `{colors.neutral/surface}`, edge/marker = `{colors.tertiary}`, text = on-colour — passed into both Mermaid `%%{init}%%` theme vars and fletcher colour args, so diagrams are brand-styled on both sides.
- **Unknown/malformed YAML:** emit a visible `::: panel` fallback with the raw text + a warning comment (never silently drop, never crash the render).

### B. Deck-visual *components* (non-diagram) — extend the slice-2 pattern

These are prose-wrapped blocks, so they use the **existing** Lua-bridge + token component pattern (add to `components.lua` / `components.typ` / `components.css`):

- `kpi` (KPI tile) — big figure + label, accent colour. (stat-panel's deck cousin.)
- `cover-slide` — full-bleed branded cover (title/subtitle), neutral background.
- `section-slide` — section divider, surface background.
- `asset-embed` already exists (`embed`); reuse.

(`cover`/`section` document variants already exist from slice 2; the `-slide` variants are deck-proportioned.)

### C. Wiring (`render.py`)

1. After `metacontent.strip`, call `diagrams.expand(text, export, tokens)` → writes the target-specific `source.md`.
2. Diagram packages: fletcher is fetched by Typst on first compile (network). Add a `studio doctor`/dep note that PDF diagrams need network on first use (cached after). Mermaid is bundled with Quarto.
3. No quarto.yml change needed for HTML (Mermaid is native); the `{=typst}` raw blocks already flow through the existing typst path.

### D. CLI / contracts

- The asset files (`flow-diagram.yml`, `timeline.yml`, etc.) already exist (slice 1) — update their `authoring.syntax` to the structured-YAML form and `render_notes` to name the engines. No new formats.

## Testing / verification

- `tests/test_diagrams.py` (standalone): for each diagram type, `expand()` with `export="html"` contains the right Mermaid directive; with `export="pdf"` contains the fletcher import + nodes; tokens appear in both; malformed YAML → fallback panel, no exception.
- **Pixel verification (the real bar):** render a deck-style doc containing every diagram + kpi/cover-slide/section-slide to **both** `*-pdf` and `*-html`, rasterize, and inspect — each diagram must read as a clean, on-brand visual. Not "it compiled."
- All existing suites stay green.

## File manifest

**New:** `design/scripts/studio/diagrams.py`; `tests/test_diagrams.py`.
**Edited:** `design/scripts/studio/render.py` (preprocess call); `design/templates/components/{components.lua,components.typ,components.css}` (kpi / cover-slide / section-slide); diagram asset YAMLs (`flow-diagram`, `timeline`, `process`, `hierarchy-diagram`, `organigram` authoring + render_notes); `design/formats/README.md` (diagram authoring); `design/scripts/studio/deps.py` or doctor note (fletcher network-on-first-use).

## Out of scope (explicit)

- **Editable native PPTX / Google-Slides** (slice 4b) — needs a python-pptx shape backend; separate spec.
- **data-viz** (charts from data) — defer with 4b decks, or its own slice; flagged not-done, not faked. (Diagram set above does NOT include chart rendering.)
- Per-session design-system selection (separate backlog item).

## Risks

- **fletcher network fetch** on first PDF-with-diagram render. Mitigation: it caches; document it; (optional later) vendor the package into the Typst local cache for offline/sandbox parity — relevant to the cowork/mode-1 story.
- **Mermaid theming depth** — `%%{init}%%` covers colours; exotic per-node styling may be limited. Acceptable: brand colours + clean layout is the bar, not arbitrary art.
- **Tree layout in fletcher** (hierarchy/org) is more code than linear flow; if it gets heavy, ship flow/timeline/process first and split hierarchy/org into a follow-up (log it, don't fake).
