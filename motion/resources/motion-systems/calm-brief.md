---
version: alpha
name: Calm Brief
description: Unhurried, confident motion for explainers and pitches — nothing flashy.
easing:
  standard:   "cubic-bezier(0.4, 0.0, 0.2, 1)"
  decelerate: "cubic-bezier(0.0, 0.0, 0.2, 1)"
  accelerate: "cubic-bezier(0.4, 0.0, 1, 1)"
duration:
  fast: 250
  base: 500
  slow: 900
transitions: [cut, fade, slide]
pacing:
  default_scene_seconds: 5
  words_per_minute: 145
---
## Overview

Calm Brief is the default motion system: measured pacing, soft easing, and a
restrained transition set. It suits explainer videos and elevator pitches where
the message — not the motion — is the point. Pairs with any design system for
colour and type.

## Motion

- **Easing** — `standard` for most moves; `decelerate` for entrances (things
  settle in); `accelerate` for exits (things leave with intent). Avoid linear.
- **Duration** — `base` (500ms) for element entrances; `fast` for emphasis;
  `slow` for scene transitions and hero reveals.
- **Pacing** — ~5s per scene, ~145 wpm narration, so on-screen text has time to
  be read before it moves.

## Do's and Don'ts

- **Do** animate one idea at a time; let it land before the next enters.
- **Do** reserve the accent colour for the single thing each scene is about.
- **Don't** bounce, spin, or overshoot — Calm Brief never draws attention to the
  animation itself.
- **Don't** transition faster than `slow`; hard cuts are fine, fast wipes aren't.
