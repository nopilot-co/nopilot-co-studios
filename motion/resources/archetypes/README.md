# Archetypes — scene templates

An **archetype** is a reusable scene structure for a kind of visualisation. The
`ideate` skill picks one; `storyboard` instantiates it into a concrete
`storyboard.json`. Each archetype is referenced by slug and is brand/motion-token
driven, so the same archetype re-skins per brand.

Planned archetypes (filled in across the build slices):

| Slug | What it is | Slice |
|------|------------|-------|
| `explainer`   | Narrated multi-scene explainer (the default) | S2 |
| `infographic` | Animated, Remotion-style data/process infographic | S4 |
| `flow`        | Build-on / step-reveal over a flow or architecture diagram | S5 |
| `timeline`    | Sequential reveal of stages/events with narration timing | S5 |
| `presenter`   | Digital-twin face-to-camera (explainer / elevator pitch) | S3.5 |

> No templates shipped yet — each lands with its slice. See `motion/CLAUDE.md`.
