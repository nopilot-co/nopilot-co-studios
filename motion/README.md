# Motion Studio

The **`motion-studio`** Claude Code plugin — the animator/visualiser studio.
Turns a brief or existing content/data into **animated, narrated assets that
tell the story**: explainer videos, animated (Remotion-style) infographics,
embeddable animated SVG / interactive HTML / Lottie, and photorealistic
**digital-twin** face-to-camera presenters (elevator pitches, explainers).

One studio within **Studios** — see [`../CLAUDE.md`](../CLAUDE.md) for the
studios model and the three invocation modes, and
[`CLAUDE.md`](CLAUDE.md) for this studio's architecture and build sequence.

## Status

**S0 — scaffold.** The contract surface exists (plugin, `studio.yaml`, the
`motion` CLI with a live `doctor`/`info`, and skill stubs). Rendering lands in
later slices; see the build sequence in [`CLAUDE.md`](CLAUDE.md). Tracked in
issue #42; engine decision in
[`../docs/architecture/DECISIONS.md`](../docs/architecture/DECISIONS.md) (ADR-002).

## Quick check

```bash
./install.sh          # symlink plugin + workspace + editable install + dep check
motion doctor         # render tools (node, ffmpeg) + provider configuration
motion info           # studio identity + where outputs land
```

## Two layers (judgment vs mechanics)

- **Skills** (`skills/<name>/SKILL.md`) — the LLM judgment and the contract:
  `content-review` → `ideate` → `storyboard` → `script` → `produce` →
  `visual-qa`, plus `twin-ingest` for the presenter archetype.
- **Deterministic glue** (`scripts/motion/`, the `motion` CLI) — storyboard
  validation, render orchestration (Remotion / declarative SVG / providers),
  versioning, rasterization. No judgment here.

The same skills run whether invoked as a local plugin, via CLI from a server, or
server-side — only the trigger and LLM host change.
