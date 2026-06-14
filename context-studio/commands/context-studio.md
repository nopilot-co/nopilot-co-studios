---
description: Orchestrate the tools/ tier (notion-sources, source-enrich, source-summarise, theme-propose, theme-cluster, theme-entity, youtube-transcript) into a per-engagement context store. Three capabilities — ingest, map, extend. Other studios reference the context by slug.
argument-hint: <engagement slug> [ingest from <notion-db|url|file>] [map] [extend with <source>]
---

# /context-studio

Orchestrate the context studio: a per-engagement context store populated by
chaining the tools/ tier. The studio is **infrastructural** — its outputs
seed every other studio (Principal mapping, audience modelling, delivery
prior-art, etc.).

`$ARGUMENTS` names the **engagement slug**; the rest tells the studio what
to do (ingest from a Notion DB or URL, run the map, extend with new
sources).

## Pipeline — ingest (`ingest-context`)

1. **Scaffold the engagement store.**
   - `context engagement new --engagement <slug>`
2. **Pull sources.** Use the existing tool-bench CLIs over the boundary:
   - From Notion: `context ingest --engagement <slug> --notion-db <id>` →
     shells out to `notion-sources --database <id> --out
     <store>/sources/`. (The tool stays studio-free.)
   - From a URL or file: `context ingest --engagement <slug> --source
     <path-or-url>` → adds to `<store>/sources/` and the manifest.
   - YouTube: `context ingest --engagement <slug> --youtube <url>` →
     shells out to `yt-transcript`.
3. **Enrich.** `context ingest --engagement <slug> --enrich` →
   `source-enrich --batch <store>/sources/`.
4. **Summarise.** Caller-supplied-JSON materialiser step — the model
   produces per-source summaries; the CLI hands the JSON to
   `source-summarise --summary-json <path>`:
   - `context ingest --engagement <slug> --summarise --summary-json <path>`

## Pipeline — map (`map-context`)

5. **Propose themes.** `context map --engagement <slug> --propose` →
   `theme-propose --batch <store>/sources/`. Caller supplies the proposal
   JSON.
6. **Cluster.** Caller supplies the theme assignments JSON:
   - `context map --engagement <slug> --cluster --assignments <path>` →
     `theme-cluster --assignments <path>`.
7. **Render theme entities.** Caller supplies per-theme synthesis:
   - `context map --engagement <slug> --entity --spec <path>` →
     `theme-entity --spec <path>`.

## Pipeline — extend (`extend-context`)

8. **Append + re-process.** When a new source arrives:
   - `context extend --engagement <slug> --source <path-or-url>` (appends
     to the manifest, runs incremental enrich + summarise; re-runs map if
     `--remap` is set).

## Conventions

- **You orchestrate; the tools materialise.** The dumb-tool invariant
  (ADR-004) means each tool stays studio-free; this studio chains them
  over the CLI boundary. Don't reimplement tool logic here.
- **The context is reusable.** Once an engagement's context is populated,
  other studios reference it by slug — audience builds reader models from
  it, delivery checks prior art, the Principal uses the thematic map to
  shape scope.
- **Caller-supplied JSON is the contract** at each materialiser stop
  (summarise / propose / cluster / entity). The model produces the JSON;
  the tool materialises it; this studio records what ran with what
  provenance.
- **Tools may be missing.** `context doctor` reports each tool's
  reachability. Steps degrade cleanly with an install hint if a required
  tool is absent.
