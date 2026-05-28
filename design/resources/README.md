# Resources

The **canonical location for template assets used to create designs.** Every
design choice the studio can make — and therefore every choice it must be able to
*replicate* — lives here. If a design uses it, it comes from `resources/`.

## Aim

Design choices should be **normalised, interchangeable, extensible, and
consistent**:

- **Normalised** — each category has one canonical file format, so choices are
  expressed the same way every time.
- **Interchangeable** — a design references a resource *by name* (a design-system
  slug, an icon set, a voice file). Swap the reference and the design re-skins
  without rewriting content.
- **Extensible** — drop a new file into a category folder to add a choice; add a
  new folder to add a whole category. These folders grow as user-defined policy.
- **Consistent** — because the resource is the single source, the same input plus
  the same resources reproduces the same design, on laptop or on a server.

> **The 100% rule:** these folders must represent *all* design choices that get
> made. If a design depends on something not captured here, it cannot be
> faithfully replicated — so capture it here first.

## Categories

| Folder | Choice it owns | Canonical file | Catalog |
|--------|----------------|----------------|---------|
| `design-systems/` | Visual system: color, type, spacing, radius, components | `<slug>.md` (YAML front-matter tokens + prose) | [`design-systems/design.md`](design-systems/design.md) |
| `iconography/` | Interchangeable SVG icon set | `<set>/` of SVGs + a manifest | [`iconography/icons.md`](iconography/icons.md) |
| `brand-voice/` | Tone-of-voice / writing principles | `<slug>.md` | `brand-voice/brand-voice-default.md` |

## How resources relate to the rest of the studio

- A **brand** (`_brand.yml`) is a specific instantiation — it should be derivable
  from / consistent with a chosen design-system, icon set, and voice file.
- A **format** (`pitch-pdf`, …) decides *what* the asset is and its ruleset;
  resources decide *how it looks and sounds*.
- Keeping the two separated is what makes outputs interchangeable: the same
  `pitch-pdf` content re-rendered against a different design-system is a re-skin,
  not a rewrite.

## Adding to a category

1. Copy the canonical file shape for that category (see its catalog file).
2. Give it a kebab-case slug filename.
3. Add a one-line entry to the category's catalog so it is discoverable.
4. Nothing else should hard-code the choice — reference the slug.
