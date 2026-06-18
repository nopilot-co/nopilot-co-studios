# UDS → PDF: what to bake into the studio

Translation of the KMS/Indicia cowork learnings ([`kms-cowork-learnings.md`](kms-cowork-learnings.md))
into concrete studio bake-ins. That proposal was rendered **outside** the studio
because the studio has no UDS-HTML → PDF step yet. The UDS promise is "one source
(`tokens.yaml`) renders consistently across six formats" (`design/uds/uds.yml`) —
so these are **PDF-aspect contract properties**, not one-off fixes.

State of play on `feat/uds-360-rebuild` (#123): the *pagination / no-truncate*
family is already baked into the **gslide** (Google Slides API) surface
(`scripts/studio/gslide.py` — native card-grid, feature-panel, process/flow,
swimlane, bar-chart; table pagination with repeating header; `group_lead`). The
PDF surface has **not** had the same treatment, and `uds/ui/uds-doc.css` has zero
`@page` / `@media print` rules.

## Group 1 — The missing surface: a real UDS → PDF engine
- **Gap:** `scripts/studio/render.py` makes PDF only via Quarto + Typst (the
  "linear-engine" documents path). The rich UDS document (`scripts/studio/uds_html.py`
  — pill header, cover, contents, section covers) has no PDF path. So UDS→PDF was
  a manual Playwright print in the KMS run.
- **Bake-in:** add a deterministic PDF engine for the UDS surface — a sibling to
  `gslide.py` — that drives Playwright `page.pdf(...)` over the UDS-HTML with the
  proven settings:
  - `displayHeaderFooter: true` + `headerTemplate` / `footerTemplate` (logo,
    confidentiality, company details, page numbers). **Native margin-box reserves
    the margin and never overlaps body** — a `position:fixed`/`sticky` header
    overlaps continuation pages.
  - `printBackground: true`; explicit `@page { size: <landscape>; margin: <bands> }`.
  - Wire as the `pdf` engine for UDS formats; flip the export contract
    `status`/`supported` (`formats/exports/gslide.yml` etc. still say `planned` /
    `supported: false`). Makes mode-2/3 parity real — same skill/CLI, no manual step.

## Group 2 — A UDS print stylesheet (`uds/ui/uds-doc.css` → add `@media print`)
- `.doc-header { position: static }` in print — kill the sticky pill; running
  header/footer comes from the Playwright margin-box, not the DOM.
- **Break per topic, flow within, keep blocks whole:** `break-before: page` on the
  section covers / topic starts that should begin fresh; `break-inside: avoid` on
  `.uds-card`, `.uds-panel`, KPI/stat blocks, `.uds-pull-quote`, table rows; let
  `.doc-prose` flow. (Beats one-panel-per-page, which leaves sparse + cramped pages.)
- **Cover = dedicated page:** replace `min-height: 80vh` (unreliable in print) with
  a fixed first page + `break-after: page`; swap `clamp(..vw..)` display sizes for
  the `type_px_to_pt` pt values UDS already defines (`uds.yml`).
- **Drop `backdrop-filter: blur`** in print (Chromium rasterises it poorly).
- **No inline bleed for wide elements:** never burst wider than the column —
  transform and negative-margin both collapse Chrome's print pagination (KMS run:
  25pp → 16pp). Wide diagrams = fit-to-column SVG or a dedicated full-bleed page
  (`break-before/after: page`).
- **Logo flex fix:** any logo in a flex row → `height: …; width: auto;
  align-self: flex-start` (never default `align-items: stretch`, which stretches it).

## Group 3 — One directive vocabulary across html / pdf / gslide
- KMS "outstanding": source drifted to `:::cards` / `:::flow` the renderer couldn't
  process. Already being closed for gslide on this branch.
- **Bake-in:** the UDS-HTML→PDF surface consumes the **same** `:::` archetype set
  already in the formats catalogue (flow/process/timeline/swimlane/decision-tree,
  card-grid, panel, chart, table). One source → six formats, no per-surface
  shorthand drift. Update `formats/README.md` (still says gslide "not yet built").

## Group 4 — Front-load the assumptions (the real-story learning)
The costly lesson was non-technical: **the brief is shaped, not handed over.**
Audience, brand and voice were assumptions until corrected, each wrong one a rebuild
(template green; pitched at KMS not Indicia; brand wrong twice before Guidelines v1.2;
tone several passes). Move these to the front, as gates before any render:
- **Brand-authority gate** (`brand-ingest`): `_brand.yml` carries provenance + a
  confidence/authority flag; a template-default or low-confidence ingest must be
  confirmed before render. Extract logos crisp from the guidelines PDF, not the
  low-res asset — make it ingest policy.
- **Recipient confirmation** in the Principal's L2 sign-off: who is this addressed to
  (the lead agency Indicia, not the end client KMS), stated and confirmed.
- **Voice lock:** tone confirmed up front as a named `brand-voice/` resource (plain
  consultative British English; no dashes/slogans/inflation), enforced by message-QA.
- **PDF is the master; never patch the print-ready file** — already the studio
  invariant (immutable sessions, render from `source.md`, version bumps). Make
  explicit in render/QA docs. DOCX/gdoc are low-fidelity for UDS (CSS doesn't
  survive) — if a Word artefact is needed it's a separate, flagged low-fi format.

## Parallel-safety (running alongside the GSlide agent)
PDF and GSlide are two serialisers off one source and share almost no files, so
they parallelise. **Disjoint:** PDF owns `uds_pdf.py` (new) + `@media print` in
`uds/ui/uds-doc.css`; GSlide owns `gslide.py` + `gslide.yml` + the v13 payload.
**Shared, read-only:** `uds_html.py` `_FENCE` is the canonical `:::` vocabulary —
GSlide mirrors it, PDF prints it; *freeze the vocabulary during the window* (no
renamed or removed fence kinds). **Shared, additive:** both add an engine branch
to `render.py` (and a `format=` case to the www `export/route.ts`) — agree the
engine key names once. **Defer** the shared source→IR parser (one vocabulary
instead of `_FENCE` vs `_flat_blocks`) to a follow-up once both surfaces work —
doing it now puts both agents in the same file. PDF work runs on its own
branch/worktree (`feat/uds-pdf`) off `feat/uds-360-rebuild`.

## Status (2026-06-18)
**Shipped + merged** into `feat/uds-360-rebuild` (merge `8f311de`): Group 1 (the
`uds_pdf.py` Chromium engine, `uds-pdf-engine` in `render.py`, the `uds` layout +
`proposal-uds-pdf` slug) and Group 2 (the `@media print` block). Verified end to
end: nopilot + coherence brands and the real 41-topic 360 docket (112 pp) all
render; native header/footer correct on cover + continuation pages; cards / quotes
/ callouts kept whole; `studio formats validate proposal-uds-pdf` green.
- **Theming:** `uds_pdf` auto-generates a missing `theme-<brand>.css` on demand,
  writing only that file — *not* `hydrate.write_themes`, which clobbers the shared
  single-brand `uds-ui.lock.json`. `theme-360` still can't generate: the 360 brand's
  `tokens.yaml` isn't graduated into the studios brand store (it's in context-message-360).
- **Group 3 (one vocabulary):** PDF prints the same `_FENCE` set; gslide convergence
  continues on its own branch. Unchanged.
- **2-column proposal profile — OPEN, and confirmed a `uds_html` job.** A print-only
  `@media print` multicol was tried and **reverted**: per-topic multicol orphaned
  headings and produced near-empty pages (117 pp > 112 pp single-col). Continuous
  2-column flow needs `uds_html` to emit the profile at the document level.

## Diagrams & viz on the PDF path (open — all in `uds_html`, not the engine)
The `uds_pdf` engine is done; **every remaining PDF-track item is in the shared
`uds_html` mapper** (the convergence surface with gslide).

- **Current state:** `uds_html` renders natively only stat-panel, pullquote,
  callout-panel, process, cta, **bar** chart, flow, cards, swimlane/timeline.
  Everything else → `[unsupported block]`. The docket path (`_doc_topic`) defers
  **all** `topic.viz` to `[figure: … — viz port pending]`. So on the 360 proposal
  the dartboard/bullseye, model, swimlanes, pillars, economics, financials
  diagrams currently print as placeholders.
- **The renderers already exist:** `frameworks.py` (bullseye, matrix, funnel,
  heatmap, decision-tree), `charts.py` (bar/line/pie/scatter/area), `diagrams.py`
  (flow/process/timeline/hierarchy/org) all emit brand-styled SVG — but they are
  wired to the Quarto *linear-engine*, not to `uds_html`. This is **wiring, not
  new rendering**.
- **Handle, two tiers:** (A, quick) teach `uds_html._doc_topic` to **inline the
  docket's pre-rendered SVGs** (`dartboard.svg`, `model.svg`, …) instead of the
  port-pending placeholder — unblocks the 360 proposal PDF immediately; (B,
  proper / Group 3) wire `uds_html` to reuse `frameworks`/`charts`/`diagrams` for
  authored `:::bullseye|matrix|funnel|heatmap|chart|hierarchy` blocks so
  HTML/PDF/gslide draw from one engine (shared `uds_html` edit — coordinate with
  the gslide agent).
- **hype-cycle / market-landscape curve:** **no studio archetype exists.** The
  360 docket keeps a **bespoke** hype-cycle renderer (manifest J-003: the studio
  `timeline` block is a flat strip with no curve — strictly less informative).
  Handle via Tier A (embed the bespoke SVG); only build a `hype-cycle` archetype
  in `frameworks.py` if it's wanted as reusable.
- **Also open:** 2-column proposal profile (above); `theme-360` (graduate the 360
  brand tokens into the store); optional webfont bundling (print currently fetches
  Google Fonts at render time).
