# Context Studio

One studio within **Studios** (see [`../CLAUDE.md`](../CLAUDE.md) for the
studios model). **Infrastructural** — other studios reference an
engagement's context by slug. The studios invariant applies: skills are
the single source of processing behavior across invocation modes.

Packaged as the Claude Code plugin **`context-studio`**
(`.claude-plugin/plugin.json`). `./install.sh` creates `.venv` and installs
the `context` CLI. Pure-Python; the studio is *orchestration over the
tools/ tier* — every actual file-touching step is one of the tools, called
over the CLI boundary (the dumb-tool invariant, ADR-004, stands).

## Note on the directory name

The studio's source lives at **`context-studio/`** in the repo (the
top-level `context/` directory already holds operating-model briefs and is
not a studio). The studio's **slug is `context`** (in `studios.yml`), the
**CLI is `context`**, and the **plugin name is `context-studio`** — so the
naming is unambiguous everywhere it matters.

## What it does

Three capabilities, each orchestrating a slice of the tool-bench:

- **`ingest-context`** — `notion-sources` → `source-enrich` →
  `source-summarise`. Pull source material into the per-engagement context
  store, populate front matter, summarise.
- **`map-context`** — `theme-propose` → `theme-cluster` → `theme-entity`.
  Derive a thematic map of the ingested sources; render per-theme
  dossiers.
- **`extend-context`** — append sources to the existing store; re-run
  enrich + summarise incrementally; optional remap.

Caller-supplied-JSON materialiser pattern is preserved end-to-end — at
`summarise`, `propose`, `cluster`, and `entity` the caller supplies the
model-produced JSON; the tool materialises it; this studio records what
ran when, with what provenance.

## Two layers (judgment vs. mechanics)

- **Skills** (`skills/<name>/SKILL.md`) — the LLM judgment + the contract.
- **Deterministic glue** (`scripts/context/`, the `context` CLI) — no
  judgment.

| Skill | Drives | Does |
|-------|--------|------|
| `ingest-context` | `context ingest …` | scaffold + chain notion-sources/source-enrich/source-summarise via the bridge |
| `map-context`    | `context map …`    | chain theme-propose/theme-cluster/theme-entity via the bridge |
| `extend-context` | `context extend …` | append sources + incrementally re-run enrich/summarise/map |

## Reuses the tools tier (CLI boundary)

The Context studio holds **zero** tool logic. It calls `notion-sources`,
`source-enrich`, `source-summarise`, `theme-propose`, `theme-cluster`,
`theme-entity`, and `yt-transcript` over the CLI boundary
(`scripts/context/bridge.py` — same pattern as
`audience/scripts/audience/nit_bridge.py`). If a tool is absent,
`context doctor` reports it and the step that needs it fails with an
install hint.

## Data root (outside the repo)

`CONTEXT_STORE_ROOT = ~/context/studios/context/`. Same override chain as
the other studios (`$STUDIOS_DOCKET_ROOT`, etc.).

```
~/context/studios/context/<engagement>/
  manifest.json        # studio-level manifest: which tools ran when, with what args + provenance
  sources/             # the tool-bench batch dir (sources.json + index.md + NNNN-<slug>.md)
  themes/              # theme entity dossiers (one .md per theme)
  themes.json          # output of theme-cluster
  theme-manifest.json  # output of theme-propose --adopt
  version.json         # { engagement, status, created, current, history[] }
```

`manifest.json` is validated against
`scripts/context/schemas/manifest.schema.json`. Slugs are kebab-case.

## CLI

```
context doctor             # tool-bench reachability report

context engagement new     --engagement SLUG
context engagement list
context engagement show    --engagement SLUG

# ingest-context
context ingest --engagement SLUG --notion-db ID                         # → notion-sources
context ingest --engagement SLUG --source PATH_OR_URL                   # add a single source
context ingest --engagement SLUG --youtube URL                          # → yt-transcript
context ingest --engagement SLUG --enrich                               # → source-enrich
context ingest --engagement SLUG --summarise --summary-json PATH        # → source-summarise

# map-context
context map --engagement SLUG --propose                                 # → theme-propose (scan)
context map --engagement SLUG --propose --proposal-json PATH            # → theme-propose --proposal-json
context map --engagement SLUG --adopt PATH                              # → theme-propose --adopt
context map --engagement SLUG --cluster --assignments PATH              # → theme-cluster
context map --engagement SLUG --entity --spec PATH                      # → theme-entity

# extend-context
context extend --engagement SLUG --source PATH_OR_URL [--enrich] [--remap]

context status --engagement SLUG [--set draft|ingesting|mapped|ready]
```

- Entry point: `context = context.cli:main` (`pyproject.toml`).
- Every step records its invocation + tool version + timestamp into
  `manifest.json`, so the chain is auditable and replayable.

## Code map (`scripts/context/`)

| Module | Responsibility |
|--------|----------------|
| `cli.py` | Click entry point `context <command>` |
| `store.py` | Scaffold per-engagement store; manifest CRUD |
| `bridge.py` | Resolve + invoke each tool CLI (PATH + venv fallback); capture stdout / artefacts |
| `pipeline.py` | Sequence steps; record which steps have run; orchestrate ingest + map + extend |
| `deps.py` | `context doctor` — per-tool reachability |
| `schemas/manifest.schema.json` | JSON Schema for `manifest.json` |

## Conventions

- **The tools own the work; the studio orchestrates.** Reimplementing tool
  logic here would violate the brief's reuse-over-CLI-boundary rule.
- **Caller-supplied JSON is preserved.** Each materialiser stop (summarise
  / propose / cluster / entity) consumes a JSON payload from the caller.
- **The context store is reusable.** Audience reads sources for reader
  modelling, Principal references the thematic map for client mapping,
  delivery checks prior art. The slug is the join key.
- **Tools may be missing.** Each step that needs a tool reports an install
  hint cleanly; nothing crashes.
