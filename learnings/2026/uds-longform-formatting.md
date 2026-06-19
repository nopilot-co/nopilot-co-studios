# UDS longform formatting — a reading posture across slide AND doc

Distilled from the KMS/360 → GSlide work (#129). The core learning: a proposal /
proposition is a **reading document**, not a projected deck — but "longform" is a
**posture, not a format**. The same UDS source must move freely between a longform
**slide** (GSlide) and a longform **doc** (GDoc / HTML→PDF). Neither is "the default";
the posture is **selected per render** (per Ted — keep the flexibility).

## The two postures (UDS render profiles — `design/uds/uds.yml` → `profiles`)
- **`presentation`** — projected, one idea per view. 1 column; type from the aspect scale.
- **`proposal`** (longform / reading) — a document on the same canvas. **2 columns**; small
  absolute reading sizes that override the aspect scale.

| role | presentation | proposal (longform) |
|---|---|---|
| eyebrow | 11pt | **12pt** |
| title | 33pt | **16pt** |
| body | 15pt | **8pt** |
| cover-title | 56pt | 30pt |
| section-title | 50pt | 22pt |

The proposal sizes are absolute pt overrides (brand-independent); presentation sizes come
from the aspect `type_scale`.

## The KMS learning, stated as rules
- **Reading ≠ presentation.** KMS→GSlide first rendered at presentation sizes (title 33 /
  body 15) — it read as a projection, not a proposal. Apply the `proposal` profile for
  reading docs; the gslide path otherwise defaults to presentation sizing.
- **Density is the point.** 2-column body, `lines_per_slide` 12, dense tables
  (`table_size` 6), grouped lead-in prose (`group_lead` 3) — a reading doc fills the page;
  it does not breathe like a slide.
- **Never truncate.** Tables paginate (header repeats); cards / flow / swimlane wrap;
  long bodies continue. Already baked into gslide.
- **One source, both postures.** The deck and the doc are *translations* of the same UDS
  source, not separate authoring. Switch the **profile + export**, never the content.

## Flexibility, not a default (per Ted)
Do **not** hard-wire `proposal` as the default for any purpose. Keep the posture
**explicit and selectable** so a proposition renders as a longform doc *or* a longform
deck from one source, on demand. The render call (or the chosen export) carries the
choice — e.g. `build_requests(..., profile="proposal")` for a longform slide.

## Apply across the format set
`uds.yml formats.full = [html, pdf, pptx, docx, gslide, gdoc]`. Longform is a property of
the *render*, used wherever a reading output is wanted:
- **GSlide (longform slide)** — `profile="proposal"`. ✅ working + live-verified (#129).
- **GDoc / HTML→PDF (longform doc)** — the reading-document surface (engine status tracked
  in `render.py` / `uds-pdf-bake-ins.md`).

## Open / follow-ups
- **Frame roles follow the profile; archetype-internal text does not.** Card / table / flow
  internal sizes are hardcoded in `gslide.py`; parameterise them by profile so a longform
  deck is *fully* small, not just its frame. (GSlide-agent follow-up.)
- **Profile selection at the CLI / render dispatch** — surface `--profile` / a format→profile
  hint so a render picks the posture without hand-passing it, while staying **selectable,
  not defaulted**.
- **Brand:** the 360 is an **npt (nopilot)** project — render with the npt brand, not Coherence.
