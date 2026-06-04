# Remotion engine (high-fidelity video) — scaffold

ADR-002 names **Remotion** as the high-fidelity video engine for the motion
studio. It is **not wired yet** — S2 ships the declarative path (animated HTML →
MP4 via Playwright + ffmpeg), which needs only what `motion doctor` already finds
(no Node). This directory is the placeholder for the Remotion project that a
later slice fills in.

## Intended shape (when wired)

```
templates/remotion/
  package.json           # remotion + @remotion/cli + react
  remotion.config.ts
  src/
    index.ts             # registerRoot
    Root.tsx             # <Composition id="storyboard" component={Storyboard} .../>
    Storyboard.tsx       # reads inputProps: { spec, tokens } → renders scenes/layers
    components/          # Text, Shape, Chart, Presenter layers (token-driven)
```

## How `produce` will use it

1. `produce(engine="remotion")` resolves tokens + normalizes the storyboard.
2. Writes `{ spec, tokens }` as Remotion **inputProps** (JSON).
3. Runs `npx remotion render src/index.ts storyboard out.mp4 --props=props.json
   --fps=<fps> --height/--width` in a materialized copy of this project.
4. `produce._remotion_available()` flips to `True` when `node` + an installed
   project are detected (declare/detect/degrade); `engine="auto"` then prefers it,
   else falls back to the declarative path.

The storyboard schema and token contract are identical across engines — only the
renderer changes. Keep all layer/motion semantics in sync with `animate.py`.
