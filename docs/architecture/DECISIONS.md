# Architecture Decision Records

Chronological ADRs for the Studios monorepo. One entry per significant,
hard-to-reverse decision. Link back from the issue that prompted it.

> ADR-001 (server surfaces — modes 2–3: runner, transport, gatekeeper) is
> introduced by #23 on the `docs/23-server-modes-spec` branch; it merges into
> this file when that work lands.

---

## ADR-002 — Motion Studio rendering: Remotion + declarative hybrid; provider-agnostic avatar/TTS

- **Status:** accepted (2026-06-04)
- **Issue:** #42 (Motion Studio)
- **Context.** The motion studio must produce animated video, embeddable web
  motion, *and* photorealistic talking-head presenters — all on-brand,
  reproducible, and identical across the three invocation modes (local plugin,
  CLI-from-server, server-side). No single renderer covers cinematic video,
  lightweight embeds, and a digital twin at once, and the talking-head path needs
  capabilities that only exist as cloud services today.

- **Decision.**
  1. **Hybrid render engine.** **Remotion** (React/Node, via `npx`) for video and
     animated infographics; a **declarative SVG/CSS** path for self-contained
     animated HTML and **Lottie** (needs no node); **Playwright** capture →
     **ffmpeg** as a fallback and for GIF/keyframes.
  2. **Provider-agnostic adapter** for the digital-twin presenter: avatar
     (**D-ID** first) and TTS (**ElevenLabs** first, for a cloned twin voice),
     behind one interface, with an optional **local low-fidelity** avatar fallback.
  3. **`storyboard.json` is the single source of truth** — one spec, many exports.
     Brand colour/type tokens are **reused** from the design studio's token layer;
     motion tokens (easing/duration/transitions) come from a locked
     **motion-system**. Nothing is re-declared.
  4. **External renders are render-time, not delivery.** Avatar/TTS calls are part
     of `produce`, distinct from the Producer's delivery externals. Keys
     come from the **environment**, never the docket. Results are **cached by
     `hash(twin + script + provider + params)`** and stored as versioned session
     inputs, so re-composites are reproducible and free.
  5. **Consent gate.** No avatar render without a recorded consent in the twin's
     `presenter.yaml`; third-party twins require explicit recorded consent.

- **Consequences.**
  - Node/Remotion is the heaviest server-image dependency — isolated behind the
    declare/detect/degrade deps model (`motion doctor` / `Brewfile`); the
    declarative path is the no-Node fallback.
  - The presenter archetype depends on external services + credits + consent
    gating — the first studio capability that is not fully local. The invariant
    becomes "same skills + same provider adapter across modes."
  - Determinism of video requires pinned fps, embedded fonts, and seeded
    randomness.
  - Static "infographics" are produced as a storyboard's frame-0/poster, keeping
    one pipeline and avoiding overlap with the design studio.

- **Alternatives considered.**
  - *Single code engine (Remotion-only, or Manim-only).* Rejected: misses
    lightweight embeds/Lottie (Remotion) or general branded motion (Manim), and
    over-weights the server image.
  - *External-tool orchestration only (Gamma/Canva/cloud).* Rejected: breaks the
    local-render invariant and cedes brand-token control.
  - *Single avatar provider, hard-wired.* Rejected: cost/lock-in and no offline
    dev path; the adapter keeps providers swappable.
