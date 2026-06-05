# Motion Studio

One studio within **Studios** (see [`../CLAUDE.md`](../CLAUDE.md) for the studios
model and the three invocation modes). The studios invariant applies: **this
studio's skills are the single source of processing behavior** — the same skills
run whether invoked as a local plugin, via CLI from a server, or programmatically
server-side. Only the trigger and LLM host change.

Packaged as the Claude Code plugin **`motion-studio`** (`v0.1.0`; manifest at
`.claude-plugin/plugin.json`). `./install.sh` symlinks this directory to
`~/.claude/plugins/motion-studio`, creates the workspace root, checks runtime
deps, and installs the `motion` Python package (editable).

> **Status: S3.** Both render engines are now live for the *same* storyboard
> (ADR-002): the **declarative** path (animated HTML → MP4 via Playwright+ffmpeg,
> default, no Node) and the **Remotion** high-fidelity path
> (`motion produce --engine remotion` — React/Node project under
> `templates/remotion/`; node_modules installed on first use and cached). `motion
> qa capture` pulls a keyframe per scene + a contact sheet. **Lottie export**
> (`motion produce --lottie`) emits an embeddable vector animation. **S3
> complete.** Tracked in issue #42; engine decision in
> [`../docs/architecture/DECISIONS.md`](../docs/architecture/DECISIONS.md)
> (ADR-002).

## What it does

Turns a brief or existing content/data into **animated, narrated assets that
tell the story**:

- **Explainer videos** (MP4 / WebM / GIF) — Remotion / React.
- **Animated, Remotion-style infographics** — data / process motion.
- **Embeddable web** — self-contained animated SVG / interactive HTML, and
  **Lottie** JSON.
- **Static infographic** — the poster / frame-0 of a storyboard (one pipeline).
- **Digital-twin presenters** — photorealistic face-to-camera explainers /
  elevator pitches: `script → TTS → avatar lip-sync → composite`.

Positioning vs the **design studio**: *doesn't move → design (static documents);
moves or is narrated → motion.* Stills here are just a storyboard's frame-0, so
there's one pipeline, not two.

## Two layers (judgment vs mechanics)

- **Skills** (`skills/<name>/SKILL.md`) — the LLM judgment and the contract.
- **Deterministic glue** (`scripts/motion/`, the `motion` CLI) — no judgment.

Each skill drives its matching `motion` command; the `/motion-studio` command
(`commands/motion-studio.md`) orchestrates the pipeline end to end.

| Skill | Drives | Does |
|-------|--------|------|
| `content-review` | (analysis) | read existing content/data; extract the story spine + key beats |
| `ideate` | (analysis) | propose 2–3 visualisation concepts; pick an archetype + approach |
| `storyboard` | `motion storyboard validate \| board` | scene-by-scene plan → validated `storyboard.json` + a pictorial board preview |
| `script` | (analysis) | narration/VO + on-screen copy + caption timing (SRT/VTT) |
| `produce` | `motion produce` | render the locked format from the storyboard |
| `visual-qa` | `motion qa capture` | sample keyframes; critique timing/legibility/brand/caption-sync |
| `twin-ingest` | `motion twin ingest` | register a consenting person's likeness + voice (presenter) |

## Source of truth — `storyboard.json`

A render is driven by one storyboard spec (validated against
`scripts/motion/schemas/storyboard.schema.json`):

```
scenes[] { id, duration, layers[] (text|shape|image|icon|chart|presenter),
           region, role, enter/emphasis/exit motions, transition;
           chart layers: chart (bar|kpi) + data ([{label,value}] | number) }
global   { brand, title, aspect, fps, motion_system, captions, twin? }
```

One spec → many exports (the studios invariant). Brand colour/type come from the
shared `_brand.yml` via the design studio's token layer (reused, never copied);
motion tokens (easing, durations, transitions) come from a locked motion-system.

**Preview before producing.** `motion storyboard board --file <spec>` renders the
spec to a **pictorial board** (self-contained HTML + a PNG via Playwright) — one
panel per scene with the layer layout in a target-aspect mini-frame, the
narration, the motion notes, and timing, all in the brand's colours. It's the
cheap, no-engine "see it before it's built" step; the eyes-on-pixels bar, applied
to the plan. An optional **concept-frame provider** (image-gen — see ADR-002 /
the providers seam) can later replace each wireframe panel with an AI still.

## Engine (ADR-002)

Hybrid, declared per export and detected by `motion doctor`:

- **Declarative SVG/CSS** → animated HTML (`animate.py`), recorded to **MP4** via
  Playwright + **ffmpeg** (`capture.html_to_video`). **Wired (S2)** — needs no
  node, only what `motion doctor` finds. Also the embeddable preview and the
  source for QA keyframes.
- **Lottie** (`lottie.py`, `motion produce --lottie`) → an embeddable vector
  animation JSON (Bodymovin), hand-built so it's dependency-free and portable to
  any Lottie player. **Wired (S3)**, semantics in sync with `animate.py`. (Known
  limit: Lottie text layers don't auto-wrap; long lines should be pre-wrapped —
  a follow-up refinement.)
- **Remotion** (React/Node, via `npx`) → MP4 for high-fidelity explainers +
  animated infographics. **Wired (S3)** — `motion produce --engine remotion`
  renders the project under `templates/remotion/` (the `<Storyboard>` composition
  reads `{spec, tokens}` as inputProps; layer/region/role semantics kept in sync
  with `animate.py`). `node_modules` installs on first use and caches there
  (gitignored). `--engine auto` keeps the declarative default; ask for `remotion`
  explicitly. Needs `node` (`motion doctor`).
- **Playwright capture** → frames → **ffmpeg** — also encodes GIF and extracts QA
  keyframes (`qa.py`).
- **Providers** (render-time external services, swappable adapter, keyed via env,
  never the docket): **D-ID** (avatar lip-sync), **ElevenLabs** (TTS / cloned
  twin voice). Optional local low-fi avatar fallback. External renders are cached
  by `hash(twin + script + provider + params)` and stored as versioned session
  inputs, so re-renders are reproducible and free.

## Consent (load-bearing)

The presenter archetype generates a person's face + voice. The `twin` entity
**requires a consent record** in `presenter.yaml` before any avatar render; the
skill refuses a third-party twin without explicit recorded consent. Legitimate
use = your own twin, or a consenting subject.

## Resources (canonical, by slug)

`resources/` must represent 100% of the design choices the studio can make.

- `motion-systems/` — motion design systems (easing / duration / transition
  tokens + prose), same front-matter shape as the design studio's
  `design-systems/`. Layered: defaults → motion-system → brand.
- `design-systems/`, `iconography/`, `brand-voice/` — **reused** from the design
  studio's resource model (colour/type tokens, icon sets, script tone).
- `archetypes/` — scene templates per visualisation type (explainer, infographic,
  flow, timeline, presenter).

## Data root (outside the repo)

```
~/context/studios/brand/<slug>/    # shared brand store (studios-level)
~/context/studios/twin/<slug>/     # digital-twin: portrait/clip, voice ref, presenter.yaml (consent)
~/context/studios/motion/<slug>/outputs/<session>/
  inputs/                 # source content/data; cached provider clips
  storyboard.json         # the spec
  script/                 # VO text + captions (SRT/VTT)
  outputs/                # <stem>.vX.Y.Z.mp4 / .webm / .html / .lottie.json (semver)
  qa/v<version>/          # keyframe PNGs, contact-sheet, findings.md
  version.json            # { brand, twin?, session, format, source_filename, created, current, history[] }
```

Docket support via `$STUDIOS_DOCKET_ROOT` (+ `$STUDIOS_DOCKET_SESSION`), mirroring
the design studio.

## Build sequence (each slice shippable + eyes-on-pixels verified)

- **S0** ✅ scaffold: plugin.json, `studio.yaml`, `studios.yml` entry, package
  skeleton, `doctor`/`info`, Brewfile, skill stubs, ADR-002.
- **S1** ✅ storyboard schema + validator + token / motion-system resolution +
  **pictorial board preview** (`motion storyboard board`).
- **S2** ✅ first moving output: `produce` → animated HTML preview + **MP4**
  (declarative path); `qa capture` → keyframes + contact sheet. Remotion path
  scaffolded behind detection. (Reordered from the original "Remotion →
  explainer-mp4" so the no-Node path ships first; ADR-002.)
- **S3** ✅ Remotion high-fidelity engine wired (`templates/remotion/`,
  `--engine remotion`) + **Lottie** export (`--lottie`).
- **S3.5** digital-twin presenter: D-ID adapter + ElevenLabs TTS + `twin` entity
  + consent gate + `presenter` layer + compositing → `pitch-mp4`.
- **S4** ✅ animated infographics: `chart` layers (`chart: bar` growing bars,
  `chart: kpi` count-up) with inline `data`, token-coloured. Declarative path
  (`animate.py`); Lottie/Remotion chart parity is a follow-up. (Deeper reuse of
  the design chart engine — more chart types — also a follow-up.)
- **S3.5** digital-twin presenter (D-ID + ElevenLabs) — backlogged in #61
  (needs API keys + twin assets).
- **S5** flow / timeline archetypes; captions; optional more TTS voices.
- **S6** creative-director routing + chaining (embed an explainer in design-studio
  HTML; animate a deck section).
- **Modes 2/3** the same skills run server-side; the Brewfile + provider env are
  the server-image contract.

## Verification bar

Eyes-on-pixels extends to motion: render → extract keyframes / contact sheet →
look. Check timing, legibility at target size, brand-token usage, and caption
sync. Plus deterministic ruleset checks (duration, aspect, fps) like the design
studio's `max_pages`.

## Conventions

- Keep all judgment in skills and all mechanics in `scripts/motion/` — this is
  what makes the studio behave identically across invocation modes.
- The `storyboard.json` is the only source of truth for a render; never hand-edit
  generated outputs.
- Brand / design-system tokens are **reused** from the design studio's layer —
  never re-declared here.
- Provider keys come from the environment, never the docket. No avatar render
  without a consent-recorded twin.
- One brand × one format slug per session, locked at session init.
