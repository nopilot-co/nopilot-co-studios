---
name: map-context
description: Derive a thematic map of the ingested sources for an engagement by orchestrating the theme tools (theme-propose, theme-cluster, theme-entity). Caller-supplied-JSON pattern at the propose / cluster / entity materialiser stops. Use after ingest-context has filled sources/ — produces themes.json + per-theme dossiers that the Principal uses for client/market mapping and downstream studios use for shape.
---

# map-context

You are the **mapper**: judgment in deciding the theme framework and the
per-theme synthesis, materialised via the theme tools over the CLI
boundary. The `context map` CLI sequences the steps + records the chain;
you supply the JSON payloads at each materialiser stop.

## Steps

1. **Scan + propose.** Non-destructive first pass — let `theme-propose`
   produce a context digest; read it; propose the theme framework as a
   JSON payload conforming to `theme-propose --proposal-json`.
   - `context map --engagement <slug> --propose` (scan)
   - `context map --engagement <slug> --propose --proposal-json <path>`
     (materialise the proposal)
2. **Adopt.** Once you and the Principal agree on the framework:
   - `context map --engagement <slug> --adopt <theme-manifest-json>`
3. **Cluster** (caller-supplied JSON stop). Produce theme assignments per
   source as JSON conforming to `theme-cluster --assignments`:
   - `context map --engagement <slug> --cluster --assignments <path>`
4. **Render theme entities** (caller-supplied JSON stop). Produce
   per-theme synthesis as JSON conforming to `theme-entity --spec`:
   - `context map --engagement <slug> --entity --spec <path>`

## Conventions

- **You map; the tools render.** No tag-writing or markdown generation in
  the skill — the tools do that deterministically.
- **Caller-supplied JSON at every materialiser stop.** Propose, cluster,
  and entity each take a model-produced JSON payload.
- **The map is reusable.** Once `themes.json` + `themes/` are populated,
  the Principal uses them for client mapping; audience can reference
  themes by id in reader models; delivery can reference them for prior
  art.
- **Re-adopt rather than rewrite.** When the framework changes, run
  `--adopt` with the new manifest; don't hand-edit `theme-manifest.json`.
