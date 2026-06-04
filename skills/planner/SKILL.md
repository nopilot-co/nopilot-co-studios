---
name: planner
description: Plan and assemble a composite document — a reader-facing doc built from several separately-composed sections — over an in-place production docket. Proposes the sections and ordering, researches best-practice references, aligns to the brand's tone of voice, agrees per-section data sources (md/csv/image) and visualisations, writes discrete briefs for missing sections, tracks completion status, then merges the approved sections into one source.md for the design studio to render. Use when a brief asks for a multi-section document (proposition, prospectus, proposal, report) rather than a single asset.
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

1. **Intake the objective.** Read the brief. Capture the document **objective**
   (e.g. "a proposition document for a new business"), the **brand** slug, the
   target **format** (a design `<purpose>-<export>` slug, e.g. `proposal-pdf`),
   and the audience. Clarify only what blocks planning; infer sensible defaults
   and state them. Then scaffold the composition over the production docket
   (created in place if it doesn't exist yet):
   ```bash
   planner plan new --root <production-docket> --brand <slug> \
     --objective "<text>" --format <design-format-slug>
   ```

2. **Propose the sections + ordering.** Decide the parts this kind of document
   needs and their order (judgment). Persist each:
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

4. **Align to brand tone of voice.** Read the brand's voice
   (`~/context/studios/brand/<slug>/tone-of-voice.md`, falling back to
   `design/resources/brand-voice/brand-voice-default.md`). This conditions every
   brief and draft — it's judgment, not a CLI write.

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

6. **Write discrete briefs for missing sections.** Any section without composed
   content gets a focused brief so it can be produced independently:
   ```bash
   planner brief write --root <root> --id <section-id>
   ```
   This scaffolds `sections/<id>/brief.md` (fill it in) + `content.md` (the draft
   lands here) and marks the section `briefed`. When content is drafted, mark it
   `drafted`; when it's good, `approved`:
   ```bash
   planner section set --root <root> --id <section-id> --status approved
   ```

7. **Track completion.** Show the rollup; resolve whatever is blocking before
   assembling:
   ```bash
   planner status --root <root>
   ```

8. **Synthesise, then assemble (handoff).** Do the synthesis judgment **first** —
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
