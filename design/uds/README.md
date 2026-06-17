# Universal Design System (UDS)

The **UDS** is the **nopilot brand-v3** system, adopted by the studio (ADR-006).
"Universal" means **across output formats, not across brands**: one source renders
consistently to HTML, PDF, GSlide (and PPTX / DOCX / GDoc). Nothing is *translated
between formats* — each is rendered from the tokens + source, so HTML is never a
source for PDF.

## Two halves: values vs. grammar

| Half | Where | What |
|------|-------|------|
| **Token values** (source of truth) | `~/context/studios/brand/<brand>/tokens.yaml` | A **W3C Design Tokens** file: primitive ramps, light/dark semantic sets, type, space, radius, border, shadow. Transformed by **Style Dictionary v4** into CSS vars, Tailwind/shadcn, PDF print styles, and generated PPTX/DOCX/Google themes. *No template carries a hard-coded value.* |
| **Grammar** (this folder) | `design/uds/` | Brand-agnostic: the format set, the cross-format type rule, the aspect classes, and the contract register. Carries no token values. |

The values live in the brand store (graduated there as the single canonical home,
with provenance); the brand-v3 vault is the authoring history. A docket carries a
frozen, hashed snapshot of the tokens — the "onboard traveller".

## Grammar files (one document, authored in three)

| File | Holds |
|------|-------|
| `uds.yml` | `token_format` (W3C) + `transform` (Style Dictionary v4) + `tokens_source`; the **format set** (`composition: html`; `critical: [html, gslide, pdf]`; `full: [html, pdf, pptx, docx, gslide, gdoc]`); the **px→pt type rule**; the register-layer index |
| `aspect-classes.yml` | `screen` (px, fluid → html) · `slide` (pt, 16:9 → gslide/pptx) · `page` (pt, A4 portrait → pdf/docx/gdoc) |
| `archetypes.yml` | the **markdown mapping** (the spine) + the contract register: Layer A (page/block), B (text/house-style), C (application UI, HTML-canonical) |

`studio.uds.load_uds()` merges the three and validates against
`scripts/studio/schemas/uds.schema.json`.

## Data patterns (relationship + wayfinding grammar)

`data-patterns.yml` is a fourth grammar document, but a different *kind* — it sits
**upstream of rendering**. The trio above governs how a construct *looks* across
formats; data patterns govern how content is **structured and traversed**: content
is **nodes**, the relationships between them are **edges**, and a "type of
navigation" is just a constraint on which edges exist and how you move along them
(navigation = traversal). It is brand-agnostic and carries no token values.

- **Two primitives** — `node` (one addressable contenttype instance) and `edge` (a
  relationship between two), where each edge carries `scope` (hard/soft),
  `directed`, `weight`, `role`.
- **Hard vs soft** — a **hard** edge is structural and *within* a space
  (constitutive — it makes the space its shape: a doc's sequence, `lister.item`
  containment); a **soft** edge is associative and *across* spaces (connective —
  `card.links_to`, tags, citations, similarity). Hard edges are the rails; soft
  edges are opt-in surfaces (see-also, backlinks) and carry the "lost in
  hyperspace" risk. The hard/soft cut is **relative to the container and nests**,
  which is what makes content a *graph-of-graphs*.
- **Wayfinding topologies** — `linear` (1D, a path → `page`), `planar` (2D, a
  lattice → `slide`), `spatial` (3D, reserved), `graph` (n-D, arbitrary → `screen`).
  The first three are the full graph *restricted to a spatial embedding*; the graph
  is the general case. The register already speaks this grammar:
  `lister --item--> card --links_to--> detail` is a hard edge (containment) plus a
  soft edge (reference), and a "guided tour" is just a precomputed linear path over
  the graph.

Unlike the trio, it is **not yet merged by `load_uds()` nor validated by the
schema** — it is the canonical reference, and wiring it in (a `data_patterns`
schema property + resolver merge + cross-reference checks) is a later slice once an
engine consumes it.

## Resolving for a brand

```python
from studio import uds
u = uds.resolve_uds("nopilot")
# u["semantic"]["light"]["primary"] == "#C3094A"   (crimson.600)
# u["semantic"]["light"]["on-active"] == "#1C2022"  (ink on yellow — never white)
# u["type"]["body"] == {"px": "16px", "pt": "11pt", "family_role": "body", "family": "Inter, …"}
# u["dataviz"][0] == "#E11A57"                       (chart leads with the brand colour)
```

`resolve_tokens` dereferences the W3C `{a.b.c}` references and flattens the
light/dark semantic sets; `resolve_uds` pairs each web px size with its document pt
(the cross-format type rule) and binds the face per `design.md` (Newsreader =
headings/cover, Inter = body/UI, Geist Mono = the instrument layer).

## The two load-bearing rules (design.md)

- **Two signals, never swapped.** Crimson = action (CTA, brand mark, link); yellow
  = attention (focus ring, selected, live data point). **Yellow is a fill, never a
  text colour** — `on-active` puts ink on yellow.
- **One source, six formats.** A value is written once in `tokens.yaml`; every
  format reads it. A change here is a change everywhere.

## Status (Slice 0, epic #123)

Slice 0 ships the grammar + the W3C resolver **render-inert** — nothing in
`render.py` / `components.py` reads it yet. Next: Style Dictionary artifact
generation + wiring (Slice 1), the contract register into the `:::` engines
(Slice 2), sealed aspect/type rules (Slice 3), the docket → parallel-render
inversion with the frozen token snapshot (Slice 4), sideways render (Slice 5), the
nopilot-co-www save fan-out (Slice 6), and the 360 refactor (Slice 7). The first
cross-format proof is the **cover sheet across HTML + GSlide + PDF**.

`data-patterns.yml` (the relationship + wayfinding grammar) is authored as a
standalone grammar doc, **render- and grammar-inert** — not yet merged by
`load_uds()` nor in the schema. Wiring it in (schema property + resolver merge +
cross-reference checks) is its own later slice, due when a nav/IA engine consumes
it (a natural companion to the 360 refactor, Slice 7).
