---
name: script
description: Write the narration/voiceover and on-screen copy for the storyboard in the brand voice, with per-scene timing and a caption track (SRT/VTT), TTS-ready. Fourth step of the motion pipeline.
---

# script

**Purpose.** Write what is said and shown. Narration / VO copy (TTS-ready, with
SSML hints), on-screen text, and per-scene timing that lines up with the
storyboard. Emits a **caption track** (SRT/VTT). Tone follows the brand voice
(`resources/brand-voice/`).

**Output.** Script + captions written to `script/` in the session; VO timing fed
back into the storyboard.

**Drives.** Nothing deterministic in S0; in the presenter path it feeds
`produce` (TTS → avatar).

> Status: planned (contract only in S0). See `motion/CLAUDE.md` build sequence.
