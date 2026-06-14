# Brief 02 — Consolidate `nopilot-co-utilities` → `nopilot-co-studios/tools`

**Status:** proposed (plan only — no code moved yet)
**Scope:** land `nopilot-co-utilities` as a discoverable, standalone-usable, *dumb*
tool-bench inside `nopilot-co-studios`. The `research-studio` that will orchestrate
these tools is the downstream consumer and is **explicitly out of scope** here.

---

## 1. Goals & invariants

- **Standalone-first.** Every tool installs and runs by itself (`<cli> …` on PATH)
  with *zero* studios present. A user, a cron job, or any project calls it identically.
- **Discoverable & invokable.** A studio process/agent reads one index, finds a
  tool's actions, and invokes them from the manifest alone — no tribal knowledge.
- **Dumb tools (hard invariant).** A tool has **no operational, functional, or
  contextual reliance on any studio**: no imports of studio code, no reading of studio
  context/session state, no assumption a director exists. All input via flags / env /
  JSON; all output to a caller-specified location. Enforced in CI.
- **Extensible.** Adding a tool = drop a dir + a `tool.yaml` + one registry line →
  instantly discoverable and invokable, with no change to studios or the director
  (mirrors how `studios.yml` makes a studio routable).

## 2. Target structure

```
nopilot-co-studios/
  .claude-plugin/marketplace.json     # studios + tool plugins (one marketplace)
  studios.yml                         # maker studios + orchestrators (unchanged)
  tools.yml                           # NEW — tool-bench discovery index
  install.sh                          # installs studios + all tool CLIs
  design/ messaging/ nitpicker/ audience/ motion/   # studios (unchanged)
  skills/creative-director  skills/planner  commands/studio.md
  tools/                              # NEW tier (the ex-utilities, verbatim logic)
    notion-sources/  source-enrich/  youtube-transcript/
    source-summarise/  theme-propose/  theme-cluster/  theme-entity/
      .claude-plugin/plugin.json      # installable standalone plugin
      tool.yaml                       # NEW — capability manifest
      install.sh  requirements.txt  scripts/<cli>.py  skills/<name>/SKILL.md
  tests/  docs/architecture/DECISIONS.md  pyproject.toml  …
```

Tools keep their current internals **unchanged** (the logic is already deterministic).
What's added is the `tool.yaml` manifest and registry wiring.

## 3. Discovery + invocation contract (the core)

**`tools.yml`** — the index a studio agent loads first (mirrors `studios.yml`):

```yaml
# Tool-bench registry. Tools are DUMB: no studio dependency, structured in/out.
# Add a tool here with a tool.yaml and it is discoverable + invokable immediately.
tools:
  - slug: notion-sources
    path: tools/notion-sources
    manifest: tools/notion-sources/tool.yaml
    summary: Extract a Notion database into a per-source .md batch + manifest.
    cli: notion-sources
    actions: [extract]
    standalone: true
    status: active
  # … source-enrich, source-summarise, theme-propose, theme-cluster,
  #   theme-entity, youtube-transcript
```

**`tool.yaml`** — per-tool capability manifest (mirrors `studio.yaml`, no orchestrator
entrypoint):

```yaml
tool: notion-sources
name: Notion Sources
summary: Extract a Notion DB to a per-source .md batch + manifest.
plugin: notion-sources           # installable standalone
cli: notion-sources              # command on PATH after install.sh
depends_on_studio: false         # INVARIANT — asserted in CI
actions:
  - id: extract
    description: Extract a Notion database to a per-source .md batch + manifest.
    invoke: "notion-sources --database <id> --out <dir> [--env-file <path>]"
    inputs:  { database: "id or env NOPILOT_NOTION_SOURCE_DATABASE_ID", out: "output dir" }
    outputs: { batch_dir: "sources.json + index.md + NNNN-<slug>.md" }
    exit_codes: { 0: ok, 2: auth/bad-invocation, 3: error }
    idempotent: true             # re-run appends only new rows
    side_effects: "writes under --out only; never writes to a studio/context path"
install: { script: tools/notion-sources/install.sh, cli: ~/.local/bin/notion-sources, deps: [] }
```

- **Discovery**: agent reads `tools.yml` → picks a tool/action → reads `tool.yaml` for
  the `invoke` template, IO shape, and exit codes.
- **Invocation**: run the CLI per `invoke` with structured args; consume
  files / stdout / exit-code. This *is* the function-schema agents need — deterministic,
  idempotent where marked. (Can later be generated into MCP/tool schemas; not in scope.)
- The existing **mechanical-CLI + caller-supplied-JSON** pattern (`--summary-json`,
  `--assignments`, `--spec`, `--html-file`) is exactly the dumb-tool contract — the
  caller supplies intelligence, the tool materialises it. We drop the "STUB" framing:
  these are **complete deterministic tools**, not stubs.

## 4. Enforcing the dumb-tool invariant

Add `scripts/check_tools_standalone.py` to CI that fails if any `tools/*/scripts/*`:

- imports a studio module, references `studios.yml` / `creative-director` / `planner`, or
- hardcodes a studio/context path (e.g. `~/context/studios/…`), or
- a `tool.yaml` is missing or has `depends_on_studio: true`.

Plus a smoke test: each tool installs and runs in a clean temp dir with **no studios on
disk**.

## 5. Standalone usability (preserved)

- Each tool's `install.sh` links its CLI to `~/.local/bin` (already true) → direct shell use.
- Tools remain **installable Claude plugins** via the merged marketplace
  (`claude plugin install notion-sources@nopilot-co-studios`) — keeps the thin skill for
  natural-language discovery. The skill describes *how to invoke the action*; it contains
  no studio orchestration.
- Root `install.sh` gains a "tools" pass; README gains a **Tools** section (port the
  current per-utility usage docs verbatim).

## 6. Conventions reconciliation (and the free wins)

- **Adopt studios' tooling** for the tools tier: `pyproject.toml`, `pre-commit`,
  `yamllint`, `prettier` — and **tests** (studios has 14; utilities has 0). Closes the
  test gap as part of the move.
- Add focused tests for the highest-risk tool logic we already had bugs in: Notion
  id/url parsing, `tidy_author`, PDF/control-char handling, the
  `--summary-json`/`--assignments`/`--spec` materialisers, dedupe/append.
- Reconcile **CLAUDE.md**: add a "Tools tier" section (the dumb-tool invariant + the
  *Adding a tool* build guide, ported from the utilities README/CLAUDE.md).
- **CI (`validate.yml`)**: extend to validate `tool.yaml ↔ plugin.json ↔
  marketplace.json` name/version consistency, the standalone invariant, and run tool tests.
- Migrate **ADR-001..003** into `docs/architecture/DECISIONS.md`; add **ADR-004** (this
  consolidation).

## 7. Migration phases (ordered, reversible — all on a branch)

- **P0 — Decide**: land this as **ADR-004** + a tracking issue. No code yet.
- **P1 — Scaffold**: on a branch in studios, create `tools/`, empty `tools.yml`, the CI
  invariant check, and marketplace/install wiring.
- **P2 — Move tools**: bring the 7 dirs into `tools/<name>` **preserving git history**
  via `git subtree add` (then `git mv` into place) — fall back to copy + history note if
  subtree is messy. Add each `tool.yaml`. Update `plugin.json` homepages →
  `…/nopilot-co-studios/tree/main/tools/<name>`. Drop STUB framing.
- **P3 — Wire**: marketplace.json entries (`source: ./tools/<name>`, category `tools`),
  `tools.yml` registry, root `install.sh`, README Tools section.
- **P4 — Harden**: adopt pyproject/pre-commit; add the focused tests; CI invariant +
  consistency checks green.
- **P5 — Verify**: `bash -n` + `py_compile` all; run every `install.sh`; run each CLI
  **end-to-end standalone in a studios-free temp dir**; do an agent
  **discover-and-invoke dry-run** purely from `tools.yml`/`tool.yaml`; marketplace
  version-consistency.
- **P6 — Cutover**: open PR, merge. Archive `nopilot-co-utilities` → README pointer
  "moved to nopilot-co-studios/tools", repo read-only. Re-point any
  `@nopilot-co-utilities` installs.
- **P7 — (separate effort)** build `research-studio` that orchestrates these tools via
  the manifest contract — *out of scope for this brief*, listed so the boundary is explicit.

## 8. Decisions to confirm before P1

1. **History**: preserve via `git subtree` (heavier, full history under `tools/`) vs.
   copy + archive old repo for history (simpler). Lean: **subtree**.
2. **Tool plugin names**: keep as-is (`notion-sources`, …) — no `-studio` suffix, since
   they're tools, not studios. (Recommended.)
3. **Discovery file**: a **separate `tools.yml`** (clean tier separation; recommended)
   vs. a `tools:` section inside `studios.yml`.
4. **Skill retention**: keep each tool's thin skill (natural-language discoverability) —
   yes, recommended; it stays studio-free.

## 9. Acceptance criteria

- Every tool installs + runs **with no studios on disk**.
- An agent can discover and invoke **any** tool action from `tools.yml` + `tool.yaml` alone.
- CI passes: structure + name/version consistency + **standalone invariant** + tests.
- A studio orchestrator can invoke ≥1 tool action purely through the manifest contract
  (validated in P7).
- `nopilot-co-utilities` archived with a redirect; no functionality lost.

---

## Appendix — current tools to migrate

| Tool | CLI | What it does (deterministic) |
|---|---|---|
| `notion-sources` | `notion-sources` | Notion DB → per-source `.md` batch + manifest (schema-agnostic, append/dedupe) |
| `source-enrich` | `source-enrich` | Fetch each source → fill front matter, extract body (HTML/PDF/plaintext) + assets → Appendix; tidy bylines |
| `source-summarise` | `source-summarise` | Materialise caller-supplied per-source summaries (`--summary-json`) into front matter + Core summary |
| `theme-propose` | `theme-propose` | Non-destructive scan → context digest; materialise proposal; adopt → `theme-manifest.json` |
| `theme-cluster` | `theme-cluster` | Materialise caller-supplied theme assignments (`--assignments`) → `themes.json` + tag sources |
| `theme-entity` | `theme-entity` | Render theme dossiers from `themes.json` + caller-supplied synthesis (`--spec`); backlinks by author + timeline |
| `youtube-transcript` | `yt-transcript` | YouTube → transcript `.txt`/`.md` (captions fast-path + Whisper fallback) |

Provenance: utilities currently in `nopilot-co-utilities` (ADR-001 enrich; ADR-002
thematic pipeline; ADR-003 theme manifest). This brief = ADR-004.
