---
name: visual-qa
description: Eyes-on-pixels QA for a rendered motion asset — sample keyframes and a contact sheet, then critique timing, legibility at target size, brand-token usage, lip-sync and caption sync against the motion rubric. Final step of the motion pipeline.
---

# visual-qa

**Purpose.** Verify the *rendered* asset, not that it "compiled." Capture
keyframes + a contact sheet (and, for presenters, a short audio probe), then
critique: pacing/timing, legibility at the target size, brand-token usage,
transition quality, lip-sync drift, and caption sync. Also enforce the format
ruleset (duration, aspect, fps).

**Output.** `qa/v<version>/` keyframes + `findings.md` with a verdict.

**Drives.** `motion qa capture --session <path>`.

> Status: planned (keyframe capture lands in S2). See `motion/CLAUDE.md`.
