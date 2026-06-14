---
description: Motion Studio — turn content/data into an animated/narrated asset (explainer video, animated infographic, or digital-twin presenter).
---

# /motion-studio

Orchestrate the motion studio end to end. Drives the studio's skills over the
`motion` CLI; the skills hold the judgment, the CLI does the mechanics.

> **Status: S0 scaffold.** The pipeline below is the contract; rendering lands in
> later slices (see `motion/CLAUDE.md`). Today `motion doctor` and `motion info`
> are live. Use this command to plan the asset; produce-time steps will activate
> as slices ship.

## Pipeline

1. **content-review** — read the brief + any existing content/data; extract the
   story spine, key beats, and the data worth animating.
2. **ideate** — propose 2–3 concepts (archetype + visual approach + which moments
   move); pick one with the user.
3. **storyboard** — write a scene-by-scene `storyboard.json` (validated).
4. **script** — narration / on-screen copy + caption timing.
5. **produce** — render the locked format (`motion produce`).
6. **visual-qa** — capture keyframes and critique (`motion qa capture`).

For a **digital-twin presenter**, first run **twin-ingest** to register the
consenting person's likeness + voice (`motion twin ingest`), then storyboard a
`presenter` layer.

## Inputs

- A brief, or existing content/data to visualise.
- A brand slug (shared studios-level brand).
- For presenters: a twin slug (with a recorded consent).
- A format slug (`<purpose>-<export>`, e.g. `explainer-mp4`, `pitch-mp4`).

## First, always

Run `motion doctor` to confirm render tools (node, ffmpeg) and, for presenters,
that the avatar/TTS providers are configured.
