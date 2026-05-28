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
