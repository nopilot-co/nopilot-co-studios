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
)[
  #set text(fill: ds.color.on_surface)
  #body
]

#let c_ds_callout(body) = block(
  width: 100%, fill: ds.color.accent_tint, inset: ds.space.md, radius: ds.radius.sm,
  above: ds.space.md, below: ds.space.md, stroke: (left: _rule),
)[
  #set text(fill: ds.color.on_surface)
  #body
]

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
  #set text(size: 0.9em, fill: ds.color.on_surface)
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
  // Force on-primary on text AND headings — Quarto's brand layer colours headings
  // its own way, which is invisible on the dark cover fill without this override.
  #set text(fill: ds.color.on_primary)
  #show heading: set text(fill: ds.color.on_primary)
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
  #show heading: set text(fill: ds.color.on_primary)
  #body
]

#let c_section_slide(body) = block(
  width: 100%, fill: ds.color.surface, inset: ds.space.lg, radius: ds.radius.md,
  above: ds.space.lg, below: ds.space.lg,
)[
  #set text(size: 1.6em, weight: "bold", fill: ds.color.primary)
  #body
]

// Document chrome (issue #38) — applied to a WHOLE document, not a `:::` block:
//   #show: doc_chrome.with(logo: "/assets/logo.svg")
// Carries the running header (logo + accent hairline) and footer (page number),
// a comfortable measure + leading so body copy stops crowding, and brand-spent
// headings (H1 title rule, H2 accent tab). Parity with the CSS in components.css.
// `logo` is a project-root path string (e.g. "/assets/logo.svg") or none.
// `title` / `standfirst` (strings or none) render a full-page cover up front.
#let doc_chrome(logo: none, title: none, standfirst: none, doc) = {
  set par(leading: 0.72em, spacing: 1.05em)

  // Cover page (#38): a light field with a bold tertiary accent band — the
  // "coloured block" — so the logo and title stay legible whatever the brand
  // logo's ink (a full coloured field would hide a dark wordmark). Its own
  // page, no running header/footer.
  if title != none {
    page(
      fill: ds.color.background, margin: 0pt,
      background: none, header: none, footer: none,
    )[
      #block(width: 100%, height: 0.4in, fill: ds.color.tertiary)
      #block(
        width: 100%,
        inset: (left: 1.25in, right: 1.25in, top: 1.1in, bottom: 1.25in),
      )[
        #if logo != none { box(image(logo, height: 0.55in)) }
        #v(2.2in)
        #text(size: 2.8em, weight: "bold", fill: ds.color.primary)[#title]
        #v(0.4em)
        #box(width: 2.6in, height: 3pt, fill: ds.color.tertiary)
        #if standfirst != none {
          v(0.85em)
          block(width: 82%)[
            #text(size: 1.2em, fill: ds.color.secondary)[#standfirst]
          ]
        }
      ]
    ]
  }

  set page(
    margin: (x: 1.25in, top: 1.1in, bottom: 1in),
    // Clear Quarto's auto brand-logo page background (a 1.5in top-left overlay
    // it injects from _brand.yml `logo`, on every page). We place the logo in
    // the running header instead, for parity with the HTML header (#38).
    background: none,
    header: {
      set text(size: 8pt, fill: ds.color.secondary)
      if logo != none {
        box(image(logo, height: 0.28in))
        v(4pt)
      }
      line(length: 100%, stroke: 0.5pt + ds.color.secondary)
    },
    footer: {
      line(length: 100%, stroke: 0.5pt + ds.color.secondary)
      v(3pt)
      set text(size: 8pt, fill: ds.color.secondary)
      align(right)[#context counter(page).display()]
    },
  )
  // H1 title zone: primary text + a short tertiary rule beneath it.
  show heading.where(level: 1): it => [
    #set text(fill: ds.color.primary)
    #block(below: 4pt)[#it]
    #line(length: 2.2in, stroke: 3pt + ds.color.tertiary)
    #v(ds.space.sm)
  ]
  // H2 section headers: a short tertiary accent tab above the heading.
  show heading.where(level: 2): it => [
    #v(ds.space.md)
    #box(fill: ds.color.tertiary, width: 0.32in, height: 3pt, radius: 1pt)
    #v(5pt)
    #set text(fill: ds.color.primary)
    #it
  ]
  show heading.where(level: 3): it => [
    #set text(fill: ds.color.primary)
    #it
  ]
  doc
}
