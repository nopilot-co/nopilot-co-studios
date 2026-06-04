# Motion systems — library

A **motion system** is the time-domain counterpart to a design system: the
reusable rules for *how things move* — easing curves, default durations, the
transition vocabulary, and overall pacing. Each lives as one markdown file here,
referenced by its slug. A render locks **one** motion system (`--motion-system`),
layered like the design tokens: **defaults → motion-system → brand**.

## Canonical file format (planned, S1)

YAML front-matter (the normalised motion tokens) + a prose body (the rationale
and rules) — the same shape as `resources/design-systems/`:

```yaml
---
version: alpha
name: Calm Brief
description: One line, evocative.
easing:                 # named curves used by enter/emphasis/exit
  standard:   "cubic-bezier(0.4, 0.0, 0.2, 1)"
  decelerate: "cubic-bezier(0.0, 0.0, 0.2, 1)"
duration:               # token durations (ms) referenced by scenes/layers
  fast: 200
  base: 400
  slow: 800
transitions: [cut, fade, slide, wipe]   # the allowed transition vocabulary
pacing:
  default_scene_seconds: 4
  words_per_minute: 150   # narration pacing → caption timing
---
## Overview     — what the system is for
## Motion       — how each easing/duration role is used; the restraint rules
## Do's and Don'ts — load-bearing rules a renderer must respect
```

Colour, type, spacing, and radius are **not** redefined here — they come from the
locked **design system** (`resources/design-systems/`) so motion and static
assets stay visually identical.

> No systems shipped yet — added in S1 alongside the token resolver.
