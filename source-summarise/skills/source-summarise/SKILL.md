---
name: source-summarise
description: STUB. Summarise each source in an enriched notion-sources batch — a neutral digest, the author's overall position, the core arguments made, and an assessment of the reaction in the comments section — writing them into each source's front matter + a "## Core summary" section. Use when the user wants to summarise sources, extract each piece's argument/position/stance, assess comment-section reaction, or prepare a source batch for thematic synthesis. The model reads each enriched body (and any captured comments) and returns structured JSON the CLI materialises.
---

# Source Summariser (STUB)

Summarise each source in an **enriched** `notion-sources` batch. Part of the
thematic-evidence-base pipeline: `notion-sources` → `source-enrich` →
**`source-summarise`** → `theme-cluster` → `theme-entity`. See ADR-002.

> **Stub status.** The CLI's mechanical I/O works (it materialises summaries into
> the `.md` files). The *semantic* step — producing the summaries — is the model's
> job: read each enriched source and return the JSON below.

## Procedure
1. Read the batch manifest and the enriched `NNNN-*.md` bodies you want to
   summarise (run `source-enrich` first).
2. For each, compose a neutral, faithful summary as JSON keyed by source
   `id` (or filename / row number):
   ```json
   {
     "<id|file|n>": {
       "summary": "2-4 sentence neutral digest",
       "precis": "one-line precis (optional)",
       "position": "the overall stance the author takes",
       "core_arguments": ["key claim 1", "key claim 2"],
       "comment_reaction": "assessment of the comments — agreement/pushback, themes, notable voices"
     }
   }
   ```
   Base `comment_reaction` only on comment text actually captured in the source
   (LinkedIn/X public renders often include little; note when it's thin rather
   than inventing). Stay neutral — summarise, don't editorialise.
3. Materialise:
   ```bash
   python3 "$CLAUDE_PLUGIN_ROOT/scripts/summarise.py" --batch <batch-dir> --summary-json summaries.json
   ```
   This writes `summary`, `position`, `core_arguments`, `comment_reaction` into
   each source's front matter and a `## Core summary` section, and sets
   `summarised: true` in the manifest.

Run without `--summary-json` to print the schema and a readiness check.

Exit codes: `0` ok · `2` missing batch/manifest · `3` error.
