---
name: planner
description: Plan and assemble a composite document — a reader-facing doc built from several separately-composed sections — over an in-place production docket. Proposes the sections and ordering, researches best-practice references, aligns to the brand's tone of voice and (when bound) a reader model from the audience studio, agrees per-section data sources (md/csv/image) and visualisations, writes discrete briefs for missing sections, tracks completion status, then merges the approved sections into one source.md for the design studio to render. Use when a brief asks for a multi-section document (proposition, prospectus, proposal, report) rather than a single asset.
---

# planner

You plan a **composite document** and assemble it; the **design studio renders
it**. A composite document is several sections, each *composed separately* (by
you, the user, another skill, or a studio), then merged into one `source.md`.
You own the judgment — which sections, in what order, what each needs, when it's
done, and how they synthesise. The `planner` CLI owns the mechanics — the
`composition.json` manifest, the docket, completion tracking, and the merge.

This is the studios invariant: judgment in this skill, mechanics in `scripts/planner/`,
so the result is identical across invocation modes. **You never render** —
rendering is the design studio's `render-asset`; you hand it a merged `source.md`.

## Steps

1. **Intake the objective + the reader.** Read the brief. Capture the document
   **objective** (e.g. "a proposition document for a new business"), the **brand**
   slug, the target **format** (a design `<purpose>-<export>` slug, e.g.
   `proposal-pdf`), and **the reader**. If a specific reader/audience is named or
   implied, bind the document to a **reader model** from the audience studio with
   `--audience <slug>` — this is what makes the document *built for* the reader, not
   just checked against them later. If no model exists yet, have the audience studio
   build one first (`/audience-studio` → `model-audience`), or proceed brand-only and
   note it. Clarify only what blocks planning; infer sensible defaults and state them.
   Then scaffold the composition over the production docket (created in place if it
   doesn't exist yet):
   ```bash
   planner plan new --root <production-docket> --brand <slug> \
     --objective "<text>" --format <design-format-slug> [--audience <reader-slug>]
   ```
   When a reader is bound, `plan new` prints the resolved reader-model path. **Read
   that `_audience.yml`** — its need-state, objections, decision factors, and
   communication preferences drive every step below.

2. **Propose the sections + ordering.** Decide the parts this kind of document
   needs and their order (judgment). When a reader is bound, let their **need-state
   drive it**: cover each critical/high need, lead with what this reader weighs
   most, and pre-empt their objections — not just the generic structure for this
   document type. Persist each:
   ```bash
   planner section add --root <root> --id <kebab-id> --title "<title>" [--after <id>]
   ```
   Reorder anytime with `planner section move --root <root> --id <id> [--after <id>]`.

3. **Research best-practice references.** Use web research to find 2–3 strong
   examples of this document type; note what "good" looks like per section. Pin
   the insight as provenance so later drafting honours it:
   ```bash
   planner section set --root <root> --id <id> --note "<reference insight>"
   ```

4. **Align to brand voice + the reader.** Read the brand's voice
   (`~/context/studios/brand/<slug>/tone-of-voice.md`, falling back to
   `design/resources/brand-voice/brand-voice-default.md`). When a reader is bound,
   also align to the reader model's `communication` block (register, reading level,
   `preferred_evidence`, what to `avoid`) and frame content against their needs and
   objections. Brand voice is *how* it sounds; the reader model is *who* it must
   land for. This conditions every brief and draft — judgment, not a CLI write.

5. **Agree per-section data sources + visualisation.** For each section decide
   which inputs feed it and whether a chart helps. Record the **contract** (paths
   are docket-relative; drop the files under `assets/`):
   ```bash
   planner data add --root <root> --id <section-id> --path assets/<file>.csv --kind csv
   planner viz set  --root <root> --id <section-id> --type bar --x <col> --y <col> \
     --source assets/<file>.csv --caption "<caption>"
   ```
   The viz is a **suggestion** — the design studio's data-viz engine renders the
   actual chart at render time. Agree a clean, stable column contract for any CSV.
   When a reader is bound, favour the evidence they trust (their
   `preferred_evidence`) and the proof their objections demand.

6. **Write discrete briefs for missing sections.** Any section without composed
   content gets a focused brief so it can be produced independently:
   ```bash
   planner brief write --root <root> --id <section-id>
   ```
   This scaffolds `sections/<id>/brief.md` (fill it in) + `content.md` (the draft
   lands here) and marks the section `briefed`. When a reader is bound, the brief
   carries a **Reader fit** section — name the specific needs, objections, and
   decision factors *this* section must satisfy, so whoever composes it writes for
   the reader. When content is drafted, mark it `drafted`.

7. **Gate approval on reader-fit (when a reader is bound).** A section isn't *done*
   until it meets the reader — so before approving, critique its content **as the
   reader** with the audience studio, then record the result:
   ```bash
   # critique sections/<id>/content.md against the reader model (audience studio):
   audience review new --name <id>-fit --audience <reader-slug> --target <root>/sections/<id>/content.md
   #   → audience-critique scores it → audience review score → scorecard.json
   planner section fit --root <root> --id <section-id> --scorecard <…>/review/v1.0.0/scorecard.json
   planner section set  --root <root> --id <section-id> --status approved
   ```
   `section set --status approved` is **gated**: with a reader bound it refuses
   approval until a reader-fit pass is recorded (no must-have/gate need unmet). On a
   fail, loop the strengthening areas back into `content.md` and re-critique. Use
   `--force` only to deliberately override the gate. **No reader bound → no gate**;
   approve by judgment as before:
   ```bash
   planner section set --root <root> --id <section-id> --status approved
   ```
   This per-section gate makes the document *built for* the reader; the audience
   studio's `assess-audience-fit` on the rendered whole (the creative-director's
   review gate) is the final verification.

8. **Track completion.** Show the rollup (per-section status + reader-fit); resolve
   whatever is blocking before assembling:
   ```bash
   planner status --root <root>
   ```

9. **Synthesise, then assemble (handoff).** Do the synthesis judgment **first** —
   read all approved sections, remove duplication, add connective tissue and an
   intro by editing `content.md` (or adding a synthesis section). *Then* merge:
   ```bash
   planner assemble --root <root> --bump minor
   ```
   This writes the merged `<session>/inputs/source.md` and prints the design
   handoff line. Hand that `source.md` + the locked format to the design studio
   (the creative-director chains `design · render-asset`). You do not render.

## Conventions

- **Judgment here, mechanics in the `planner` CLI.** Identical behaviour across
  invocation modes. Don't reimplement merging or manifest logic in prose.
- **Plan + assemble; never render.** Rendering is the design studio's
  `render-asset`; outward delivery is the creative-director's.
- **Operate in place** over the passed `--root` docket. Never write outside it.
  The `sections/<id>/` folders and `composition.json` are the working record.
- **`source.md` is a pure build artifact** — produced by `assemble`, never
  hand-edited. To change the document, edit section `content.md` and re-assemble.
- **Reuse design's formats.** The target format is a design `<purpose>-<export>`
  slug; the planner defines no formats of its own. If the document needs a purpose
  design doesn't have (e.g. `proposition`), that's a design-studio task, not a
  planner one — surface it.
- **One composition per docket** (v1). Each section's `status` drives the rollup;
  `assemble` merges the `approved` ones in order.
- **The reader model is an optional produce-time input.** Bound via `--audience`,
  it's read (not written) by this skill to drive section choice, briefs, and viz —
  the audience studio owns it. Without it, the planner aligns to brand voice only.
- **Reader-fit is gated per section, not just on the whole.** With a reader bound,
  a section can't be `approved` until it passes the audience studio's reader-fit
  critique (recorded via `planner section fit`); the *critique judgment* stays in
  the audience studio (`assess-audience-fit`), the planner only records + gates on
  it. So a composition reaches "ready to assemble" only when every section meets the
  reader. The audience studio's critique of the *rendered* whole (creative-director
  review gate) is the final verification on top.
