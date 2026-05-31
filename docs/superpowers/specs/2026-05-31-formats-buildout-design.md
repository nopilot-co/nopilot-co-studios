# Design — Formats build-out (slice 1 of the format/design program)

- **Date:** 2026-05-31
- **Status:** approved design → spec
- **Scope:** Layer 1 (format **contracts**) only. Rendering (CSS/Typst/PPTX) is slices 2–4.

## Goal

Build out `design/formats/` so the studio offers a rich, intentional set of
formats organised into three **buckets**, each carrying a tokenized **asset-type
vocabulary** (pullquotes, panels, covers, diagrams, …) and a per-bucket design
language. This is the contract every downstream layer (skills + renderer) targets.
Two existing blemishes are addressed: the filename version-compounding bug is fixed
in code; the redundant output-folder depth is recorded as a convention (no
committed code does that consolidation yet).

## The program this belongs to (context, not this spec)

The user chose a full build (contracts + rendering of every asset type across all
buckets in HTML/PDF/PPTX/gslide). That is a multi-session program, decomposed into
ordered slices. **This spec is slice 1 only.**

| # | Slice | Layer |
|---|---|---|
| **1** | **Formats build-out** (this spec) | Contracts |
| 2 | Rendering foundation — wire `design-systems` tokens → CSS+Typst; core shared components in HTML+PDF | Render |
| 3 | Buckets A & B components fully rendered (editorial + documents), print-clean | Render |
| 4 | Bucket C visual + **editable PPTX/gslide blocks**, diagrams/timelines/organigrams/data-viz | Render |

Slice 1 is self-contained: it adds/edits YAML contracts + a schema + two small CLI
cleanups. It introduces **no rendering risk** — every new asset type is a contract
the later slices implement.

---

## Architecture

### A. Buckets → format × export matrix

New purposes in **bold**. Slugs are `<purpose>-<export>`.

| Bucket | Purposes | Exports | Character |
|---|---|---|---|
| **A · Editorial** | **post**, **article** | `html` | Plainest. Inherited CSS (LinkedIn/blog). Typographic POV only; light inline assets. |
| **B · Documents** | proposal, **whitepaper**, **sow** | `html`, `pdf` (portrait) | Tokenized hierarchy; full document asset set; print-clean; page-break discipline. |
| **C · Decks** | pitch, **presentation**, **report**, **status**, **approach** | `pptx`, **`gslide`**, `html`, `pdf` | Low word-count; visual asset set; cross-export consistency; editable native blocks. |

**Full slug list (slice 1 authors/edits all of these):**

- A: `post-html`, `article-html`
- B: `proposal-html`*, `proposal-pdf`*, `whitepaper-html`, `whitepaper-pdf`, `sow-html`, `sow-pdf`
- C: `pitch-pptx`*, `pitch-gslide`, `pitch-html`*, `pitch-pdf`*; and `{presentation,report,status,approach}-{pptx,gslide,html,pdf}` (16)

`*` = exists today (enrich in place). Existing `pitch-revealjs` / `pitch-glide`
remain untouched as legacy pitch extras (`glide` = the Glide app builder, **not**
Google Slides). New export file: `exports/gslide.yml`.

### B. Purposes — per-bucket design language (`design/formats/purposes/<purpose>.yml`)

Each purpose centralises **intent + design language** (deep-merged under the
export). Beyond today's `style_guide` / `execution_brief` / `ruleset`, purposes
gain an `assets:` list (the asset types this purpose may use) and a richer
`style_guide` shaped to the bucket:

- **Bucket A (post, article):** an editorial **POV** block — `paragraph_length`,
  `bullets` (when/how), `punctuation`, `newline_usage`, `target_length`,
  `tone` (per-medium variation: post = punchy/first-person; article = considered),
  and `rhetoric` (licensed emphatic/rhetorical forms). Assets limited to the light
  inline set.
- **Bucket B (proposal, whitepaper, sow):** a tokenized **hierarchy** block
  (`h1..h4`, body, lists), `page_discipline` (keep-together / orphan-control /
  section grouping), `print` (clean print-from-HTML intent), and the full document
  asset set. `whitepaper` = authoritative/evidenced; `sow` = precise/contractual;
  `proposal` = persuasive/structured.
- **Bucket C (pitch, presentation, report, status, approach):** a `visual` block
  (one-idea-per-view, very low `max_words_per_view`), `consistency` (pptx ↔ gslide
  ↔ html ↔ pdf parity intent), and the visual asset set. Per-purpose intent:
  pitch = win a yes; presentation = inform/persuade a room; report = findings;
  status = where things stand; approach = how we'll do it.

### C. Exports (`design/formats/exports/<export>.yml`)

- `html`*, `pdf`* — enriched only where the bucket needs (portrait note for B).
- `pptx`* — note editable-block intent (slice 4).
- **`gslide`** (new) — `asset_type: deck`. Slice 1 mirrors `glide`'s
  not-renderable signalling exactly so it lists without pretending to render:
  `render.engine: gslide`, `render.studio_format: null`, `render.status: planned`,
  `ruleset.supported: false` (so `is_renderable()` returns false). Slice 4 flips it
  to a PPTX-backed path (`studio_format: pptx`, `supported: true`) that imports to
  Google Slides.

### D. Asset library — `design/formats/assets/<asset>.yml` (the novel core)

A **normalized catalog** of asset types, one file per asset, slug-referenced
(same pattern as `resources/design-systems/`). Formats declare `assets: [slug, …]`;
the vocabulary is defined once and never duplicated. Each asset file:

```yaml
asset: pullquote
name: Pull quote
description: A short extract lifted from the body for rhythm and a visual anchor.
buckets: [editorial, documents, decks]      # which buckets may use it
exports: [html, pdf, pptx, gslide]          # where it can render
style:                                       # token-referenced (resolved in slice 2+)
  typography: "{typography.h3}"
  accent: "{colors.tertiary}"
  rule: "left-border 3px {colors.tertiary}"
  spacing: "{spacing.lg}"
authoring:                                   # how an author invokes it in markdown
  syntax: |
    ::: pullquote
    The line worth lifting.
    — Attribution
    :::
  notes: Quarto fenced div with class `pullquote`.
render_notes:                                # contract for slices 2–4
  html: "<blockquote class='pullquote'>"
  pdf: "Typst #pullquote() block"
  pptx: "styled text box"
```

Style values reference `design-systems` tokens via `{dot.path}` exactly like
`design.md` components, so an asset never hard-codes a value. **Authoring
convention = Quarto fenced divs** (`::: <asset-class>`), which Quarto already maps
to HTML divs and which slices 2–4 map to Typst/PPTX.

**Asset catalog (slice 1 defines all as contracts):**

- *Editorial / light (A, also usable in B/C):* `precis`, `pullquote`,
  `stat-panel`, `author-attribution`.
- *Document (B):* `cover`, `section-interstitial`, `contents`, `highlight-panel`,
  `callout-panel`, `general-panel`, `data-table`, `figure-caption`,
  `source-reference`, `anchor-link`, `cta`, `author-bio`, `header-footer`.
- *Deck / visual (C):* `cover-slide`, `section-slide`, `kpi-tile`,
  `flow-diagram`, `timeline`, `process`, `hierarchy-diagram`, `organigram`,
  `data-viz`, `asset-embed`.

(Shared assets — pullquote, stat-panel, data-table, cta, caption — are single
files declaring multiple `buckets`/`exports`; not duplicated per bucket.)

### E. Format slug files (`design/formats/<slug>.yml`)

Unchanged shape: `extends: <purpose>`, `export: <export>`, optional `overrides`,
plus an optional `assets:` add/remove relative to the purpose default. Thin.

### F. Schema changes

- `design/scripts/studio/schemas/format.schema.json`: add optional `assets`
  (array of strings) to the resolved contract; allow the richer `style_guide`
  sub-blocks (kept as free `object`); add `gslide` to any export enum if present.
- New `design/scripts/studio/schemas/asset.schema.json`: validates an asset-library
  file (`asset`, `name`, `description`, `buckets`, `exports`, `style`, `authoring`,
  `render_notes`).
- `formats.py`: load + expose `assets` on the resolved contract; a new
  `assets.py` (or functions in `formats.py`) to list/validate the asset library;
  CLI `studio formats assets` (list) and validation folded into `studio formats validate`.

### G. Cleanups (small, included here)

1. **Filename version compounding.** `render.py` builds the output stem from
   `version.json.source_filename`; when content files already carry a `-v<semver>`
   label (the docket convention), the output becomes `…-v1.0.0.v1.1.0.pdf`. Fix:
   strip a trailing `-v<semver>` from the stem before stamping the render version,
   so output is `…-v1.1.0.pdf`. (Regex `-v\d+\.\d+\.\d+$` on the stem.)
2. **Redundant output folder depth.** The 360 backfill consolidated to
   `outputs/<primary>/<format>/<file>`; the `<format>` dir is redundant (format is
   in the filename). **No committed studio code does this consolidation today** (it
   was in a throwaway orchestrator), so slice 1 makes **no code change** for this —
   it only **records the convention** (flatten to `outputs/<primary>/<file>`) in
   `formats/README.md` / docket conventions, to be honoured wherever docket output
   consolidation is implemented (slice 2+). Only cleanup #1 is a committed-code fix
   in slice 1.

---

## Out of scope (explicitly)

- Any CSS/Typst/PPTX **rendering** of the new asset types (slices 2–4).
- Wiring `design-systems` token resolution into the render pipeline (slice 2).
- Per-session design-system selection (separate, pre-existing backlog item).

## Testing / validation

- Every new/edited format slug **resolves** (`studio formats list`) and
  **validates** against `format.schema.json` (`studio formats validate`).
- Every asset-library file validates against `asset.schema.json`.
- `assets:` references on every format resolve to an existing asset file, and each
  asset's declared `exports` is a superset of the formats that use it (no format
  claims an asset that can't target its export).
- The two cleanups get unit coverage: stem de-versioning in `render`; the flattened
  output path.
- Extend `tests/` with `test_formats.py` (standalone, design venv) covering the
  above.

## File manifest

**New:** `exports/gslide.yml`; `purposes/{post,article,whitepaper,sow,presentation,report,status,approach}.yml`;
`assets/<~27 files>.yml`; slug files for every new combination listed in §A;
`schemas/asset.schema.json`; `tests/test_formats.py`.
**Edited:** `purposes/{pitch,proposal}.yml`; `exports/{html,pdf,pptx}.yml`;
existing slug files; `schemas/format.schema.json`; `scripts/studio/formats.py`
(+ maybe `assets.py`); `scripts/studio/cli.py` (formats subcommands); `render.py`
(stem de-versioning); `design/formats/README.md` (document buckets + asset library).

## Risks / notes

- **Volume:** ~27 asset files + ~30 slug files + 10 purposes. Mitigation: the
  normalized library means assets are written once; slug files are 3-line stubs;
  implementation can fan out per bucket.
- **`gslide` renderability:** flagged `status: planned` in slice 1 so it lists but
  doesn't pretend to render; slice 4 implements the PPTX→Google Slides path.
- **Token references** in asset `style` are inert strings until slice 2 resolves
  them; slice 1 only guarantees they're well-formed `{dot.path}` against the
  `design.md` token shape.
