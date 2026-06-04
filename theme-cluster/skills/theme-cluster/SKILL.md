---
name: theme-cluster
description: STUB. Group sources in a notion-sources batch into themes — "contributions to a consistent core discussion thread" — producing a themes.json (theme id/label/description + member sources) and optionally tagging each source's front matter with its theme(s). Use when the user wants to cluster/group sources by topic or discussion thread, identify the core conversations across a source set, or organise a batch into themes before synthesis. The model decides the clusters; the CLI materialises them.
---

# Theme Clusterer (STUB)

Group an enriched/summarised `notion-sources` batch into **themes** — each a
consistent core discussion thread that multiple sources contribute to. Part of
the pipeline: `source-enrich` → `source-summarise` → **`theme-cluster`** →
`theme-entity`. See ADR-002.

> **Stub status.** The CLI materialises a model-produced clustering. The
> *semantic* step — deciding which sources belong to the same thread — is the
> model's job.

## Procedure
1. Read the manifest (and ideally the `## Core summary` of each source from
   `source-summarise`) to understand what each source argues.
2. Propose themes as JSON — group sources that are genuinely part of one
   discussion thread (not just sharing a keyword):
   ```json
   {
     "themes": [
       { "id": "agentic-gtm", "label": "Agentic GTM",
         "description": "Whether AI agents reshape go-to-market motion",
         "members": ["<id|file|n>", "<id|file|n>"] }
     ]
   }
   ```
   A source may appear in more than one theme. Leave genuinely off-topic sources
   unassigned.
3. Materialise:
   ```bash
   python3 "$CLAUDE_PLUGIN_ROOT/scripts/cluster.py" --batch <batch-dir> \
     --assignments themes.json --write-tags
   ```
   Writes `themes.json` (each theme with resolved member metadata + counts) into
   the batch, and with `--write-tags` adds `themes: [...]` to each source's front
   matter. `theme-entity` consumes this `themes.json`.

Run without `--assignments` to print the schema and a readiness check.

Exit codes: `0` ok · `2` missing batch/manifest · `3` error.
