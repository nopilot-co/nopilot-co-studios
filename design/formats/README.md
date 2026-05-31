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

## Output-folder convention

Docket render outputs flatten to `outputs/<primary>/<file>` — there is no
redundant `<format>/` sub-folder. The format is already encoded in the filename
(e.g. `client-proposition-pitch-pdf-v1.0.0.pdf`), so adding a folder layer
would be redundant.
