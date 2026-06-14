# Context Studio

A studio within **Studios** (see [`../CLAUDE.md`](../CLAUDE.md)).
**Infrastructural**: other studios reference an engagement's context by
slug.

The context studio is the orchestration layer over the
[`../tools/`](../tools/) tier — it sequences `notion-sources`,
`source-enrich`, `source-summarise`, `theme-propose`, `theme-cluster`,
`theme-entity`, and `yt-transcript` into a coherent per-engagement context
store. Tools stay studio-free (ADR-004 dumb-tool invariant); this studio
calls them over the CLI boundary.

> **Naming note.** Source lives at `context-studio/` (the top-level
> `context/` directory holds operating-model briefs and is not a studio).
> The slug is `context` everywhere it matters (`studios.yml`, the CLI, the
> slash command).

Three capabilities:

- **`ingest-context`** — pull source material in (Notion DB / URL / file /
  YouTube), enrich, summarise.
- **`map-context`** — propose themes, cluster sources, render per-theme
  dossiers.
- **`extend-context`** — append + incrementally re-process.

Caller-supplied-JSON pattern preserved end-to-end. Pure-Python; no native
deps; each step degrades cleanly if the required tool isn't installed.

Full descriptor: [`CLAUDE.md`](CLAUDE.md). Slash entry:
`/context-studio`. Registered in the root [`studios.yml`](../studios.yml).

## Quickstart

```bash
./install.sh
.venv/bin/context doctor             # tool-bench reachability report

.venv/bin/context engagement new --engagement demo

# ingest
.venv/bin/context ingest --engagement demo --notion-db <id>    # → notion-sources
.venv/bin/context ingest --engagement demo --enrich            # → source-enrich
.venv/bin/context ingest --engagement demo --summarise \
  --summary-json /tmp/summaries.json                            # → source-summarise

# map
.venv/bin/context map --engagement demo --propose --proposal-json /tmp/proposal.json
.venv/bin/context map --engagement demo --cluster --assignments /tmp/themes.json
.venv/bin/context map --engagement demo --entity --spec /tmp/spec.json
```

## Pairs with

- **Principal** — uses the thematic map for client / market mapping.
- **audience** — builds reader models from filed sources.
- **delivery** — checks prior art when planning.
- **architecture** — references prior systems and integrations.
- **tools/** — the actual work happens in the tool CLIs, called over the
  CLI boundary.
