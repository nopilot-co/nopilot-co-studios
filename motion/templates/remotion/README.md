# Remotion engine (high-fidelity video) — wired (S3)

ADR-002's high-fidelity video engine for the motion studio. `motion produce
--engine remotion` renders this project; the declarative path (animated HTML →
MP4 via Playwright+ffmpeg) remains the default (no Node).

```
templates/remotion/
  package.json           # remotion + @remotion/cli + react
  remotion.config.ts     # jpeg image format, overwrite
  tsconfig.json
  src/
    index.ts             # registerRoot
    Root.tsx             # <Composition id="storyboard"> + calculateMetadata (size/fps/duration from props)
    Storyboard.tsx       # reads inputProps {spec, tokens} → Sequence per scene, layers by region/role
```

## How `produce` uses it (`motion/scripts/motion/produce.py`)

1. `produce(engine="remotion")` normalizes the storyboard + resolves tokens.
2. `_ensure_remotion_install` runs `npm install` here on first use (cached in
   `node_modules/`, gitignored).
3. Writes `{ spec, tokens }` to `<out>/<stem>.props.json`.
4. Runs `npx remotion render src/index.ts storyboard <out>.mp4
   --props=<props.json>` (cwd = this dir). Size/fps/duration come from the
   storyboard via `calculateMetadata`.
5. `_remotion_available()` = `node` present + this `package.json` exists.

The storyboard schema + token contract are identical across engines — only the
renderer changes. **Keep layer/region/role/motion semantics in sync with
`animate.py`** (the declarative renderer).

For server modes, prebuild `node_modules` into the image (it's the heaviest
dependency; ADR-002).
