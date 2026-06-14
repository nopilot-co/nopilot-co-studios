---
name: produce
description: Render the session's locked format from its storyboard.json — Remotion for video/infographics, declarative SVG/HTML/Lottie for embeds, providers for the digital-twin presenter — emitting a versioned asset. Fifth step of the motion pipeline.
---

# produce

**Purpose.** Drive the deterministic render of the locked format. The engine is
chosen by the export (ADR-002): Remotion (MP4/WebM), declarative SVG/HTML/Lottie
(embeds), or the presenter path (`script → TTS → avatar → composite`). External
provider clips are cached and stored as versioned session inputs so re-renders
are reproducible.

**Output.** A versioned file under `outputs/`.

**Drives.** `motion produce --session <path>`.

> Status: planned (first export `explainer-mp4` lands in S2). See `motion/CLAUDE.md`.
