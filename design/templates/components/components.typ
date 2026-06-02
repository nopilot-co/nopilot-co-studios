// design-studio Typst component library.
//
// Static component functions, invoked by the Lua bridge (`#c_<class>[ ... ]`).
// They read design tokens from `ds`, a dict injected ABOVE this file at render
// time (see studio.components.typ_tokens) — so the same components re-skin per
// brand without edits here. Keep in visual parity with components.css.

#let _rule = 3pt + ds.color.tertiary

#let c_precis(body) = block(width: 100%, below: ds.space.md)[
  #set text(size: 1.15em, fill: ds.color.secondary)
  #body
]

#let c_pullquote(body) = block(
  width: 100%,
  inset: (left: ds.space.md, top: ds.space.sm, bottom: ds.space.sm),
  above: ds.space.md, below: ds.space.md,
  stroke: (left: _rule),
)[
  #set text(size: 1.3em, style: "italic", fill: ds.color.primary)
  #body
]

#let c_stat_panel(body) = block(
  width: 100%, fill: ds.color.surface, inset: ds.space.md, radius: ds.radius.md,
  above: ds.space.md, below: ds.space.md,
)[
  #set par(leading: 0.4em)
  #set text(fill: ds.color.tertiary)
  #body
]

#let c_highlight(body) = block(
  width: 100%, fill: ds.color.surface, inset: ds.space.md, radius: ds.radius.lg,
  above: ds.space.md, below: ds.space.md,
)[#body]

#let c_ds_callout(body) = block(
  width: 100%, fill: ds.color.surface, inset: ds.space.md, radius: ds.radius.sm,
  above: ds.space.md, below: ds.space.md, stroke: (left: _rule),
)[#body]

#let c_panel(body) = block(
  width: 100%, inset: ds.space.md, radius: ds.radius.md,
  above: ds.space.md, below: ds.space.md, stroke: 0.75pt + ds.color.secondary,
)[#body]

#let c_cta(body) = block(
  width: 100%, fill: ds.color.tertiary, inset: ds.space.md, radius: ds.radius.md,
  above: ds.space.md, below: ds.space.md,
)[
  #set text(fill: ds.color.on_primary, weight: "bold")
  #body
]

#let c_bio(body) = block(
  width: 100%, fill: ds.color.surface, inset: ds.space.md, radius: ds.radius.md,
  above: ds.space.md, below: ds.space.md,
)[
  #set text(size: 0.9em)
  #body
]

#let c_byline(body) = block(width: 100%, above: ds.space.sm, below: ds.space.md)[
  #set text(size: 0.85em, fill: ds.color.secondary)
  #smallcaps[#body]
]

#let c_reference(body) = block(width: 100%, above: ds.space.sm)[
  #set text(size: 0.8em, fill: ds.color.secondary)
  #body
]

// figure: an image/diagram with its caption. Author puts the image (markdown
// image) then a caption paragraph inside the div; the caption gets label styling.
#let c_figure(body) = block(width: 100%, above: ds.space.md, below: ds.space.md)[
  #set align(center)
  #set text(size: 0.82em, fill: ds.color.secondary)
  #body
]

// embed: a placeholder frame for an embedded asset (video/interactive) that can't
// live in a static PDF — renders a labelled surface block so the slot is visible.
#let c_embed(body) = block(
  width: 100%, fill: ds.color.surface, inset: ds.space.md, radius: ds.radius.md,
  above: ds.space.md, below: ds.space.md, stroke: (paint: ds.color.secondary, dash: "dashed"),
)[
  #set text(size: 0.85em, fill: ds.color.secondary)
  #body
]

#let c_contents(body) = block(
  width: 100%, inset: (y: ds.space.sm), above: ds.space.md, below: ds.space.md,
)[#body]

#let c_section(body) = block(
  width: 100%, inset: ds.space.lg, fill: ds.color.surface, radius: ds.radius.md,
  above: ds.space.lg, below: ds.space.lg,
)[
  #set text(size: 1.5em, weight: "bold", fill: ds.color.primary)
  #body
]

// "cover" used inline acts as a strong banner block (a true full-bleed cover
// page is a slice-4 concern); still visibly branded.
#let c_cover(body) = block(
  width: 100%, fill: ds.color.neutral, inset: ds.space.lg, radius: ds.radius.lg,
  above: ds.space.md, below: ds.space.lg,
)[
  #set text(fill: ds.color.on_primary)
  #body
]

// Deck-visual components (slice 4a). Proportioned for slides but valid inline.
#let c_kpi(body) = block(
  width: 100%, fill: ds.color.surface, inset: ds.space.lg, radius: ds.radius.lg,
  above: ds.space.md, below: ds.space.md,
)[
  #set text(fill: ds.color.tertiary, size: 2.2em, weight: "bold")
  #body
]

#let c_cover_slide(body) = block(
  width: 100%, fill: ds.color.neutral, inset: ds.space.lg, radius: ds.radius.lg,
  above: ds.space.md, below: ds.space.lg,
)[
  #set text(fill: ds.color.on_primary)
  #body
]

#let c_section_slide(body) = block(
  width: 100%, fill: ds.color.surface, inset: ds.space.lg, radius: ds.radius.md,
  above: ds.space.lg, below: ds.space.lg,
)[
  #set text(size: 1.6em, weight: "bold", fill: ds.color.primary)
  #body
]
