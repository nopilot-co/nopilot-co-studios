---
name: storyboard
description: Turn the chosen concept into a scene-by-scene storyboard.json — the single source of truth for a motion render — with per-scene layers, motions, durations and transitions, then validate it. Third step of the motion pipeline.
---

# storyboard

**Purpose.** Author the **`storyboard.json`** — the spec every renderer consumes.
Each scene declares its purpose, duration, on-screen layers
(`text|shape|image|icon|chart|presenter`), enter/emphasis/exit motions
(referencing easing + duration tokens from the locked motion-system), and the
transition to the next scene. Globals set aspect, fps, brand, motion-system, and
captions.

**Output.** A `storyboard.json` written to the session, validated against the
schema.

**Drives.** `motion storyboard validate --file storyboard.json`.

> Status: planned (schema + validator land in S1). See `motion/CLAUDE.md`.
