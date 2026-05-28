# Resources

The **canonical location for template assets used to compose communications.**
Every reusable choice the messaging studio can make — and therefore every choice
it must be able to *replicate* — lives here. If a message uses it, it comes from
`resources/`. This is the messaging counterpart of the design studio's
`resources/` (see `../../design/resources/README.md`).

## Aim

Communication choices should be **normalised, interchangeable, extensible, and
consistent**:

- **Normalised** — each category has one canonical file shape, so choices are
  expressed the same way every time.
- **Interchangeable** — a message references a resource *by slug* (a template, a
  subject-line pattern, a CTA, a sequence). Swap the reference and the message
  re-skins without rewriting intent.
- **Extensible** — drop a new file into a category folder to add a choice; add a
  new folder to add a whole category. These folders grow as user-defined policy.
- **Consistent** — because the resource is the single source, the same brief plus
  the same resources reproduces the same message, on laptop or on a server.

> **The 100% rule:** these folders must represent *all* the reusable comms
> choices that get made. If a message depends on something not captured here, it
> cannot be faithfully replicated — so capture it here first.

## Categories

| Folder | Choice it owns | Canonical file |
|--------|----------------|----------------|
| `message-templates/` | Reusable per-format skeletons (front-matter + sections) | `<format-slug>.md` |
| `subject-lines/` | Email subject-line patterns and a starter library | `subject-lines.md` |
| `ctas/` | Approved call-to-action phrasings | `ctas.md` |
| `sequences/` | Multi-step sequence templates (cadence + per-step intent) | `<slug>.md` |

## How they're used

- The `compose` skill pulls a `message-templates/<format>.md` skeleton, a subject
  pattern, and an approved CTA, then writes in the brand's voice
  (`brand-voice/`, shared with design).
- The `sequence` skill pulls a `sequences/<slug>.md` template to set the number of
  steps, their formats, and the cadence before composing each step.
- **Voice** is *not* duplicated here — it is the shared
  `../../design/resources/brand-voice/` library (brand is a studios-level entity).

## Conventions

- Reference resources by slug, never by hard-coded content.
- Keep judgment in the skills; these files are inert templates/libraries, not
  logic. Mechanics (format resolution, lint, render) stay in `scripts/message/`.
