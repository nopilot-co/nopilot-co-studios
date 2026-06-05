---
name: theme-entity
description: STUB. Build a theme entity document per theme — the thematic sourced evidence base. Renders themes/<slug>.md with summary, precis, notable contributions, key disagreements, an assessment of the comment reaction, and backlinks to contributing sources grouped by author and by timeline. Use when the user wants to synthesise a theme/discussion-thread into an evidence base, create a thematic dossier with sourced backlinks, or assemble a thought-leadership conversation map. The CLI assembles the mechanical structure (backlinks, author grouping, timeline); the model supplies the synthesis.
---

# Theme Entity Builder (STUB)

Synthesise each theme into a **theme entity** document — the thematic sourced
evidence base for a thought-leadership conversation. Final stage of the pipeline:
`source-enrich` → `source-summarise` → `theme-cluster` → **`theme-entity`**.
See ADR-002.

> **Stub status.** The CLI builds the mechanical scaffold from `themes.json`:
> per-author grouping, a timeline, and backlinks to every contributing source.
> The *semantic* sections (summary, precis, notable contributions, key
> disagreements, comment-reaction assessment) are the model's job, supplied via
> `--spec`; without it they render as `_TODO_` placeholders.

> **Follow the manifest.** If `theme-manifest.json` exists (from `theme-propose`),
> write each theme's `--spec` in line with that theme's agreed `editorial_approach`
> and the overall `editorial` voice — so the dossiers match the agreed framework.

## Procedure
1. Ensure `theme-cluster` produced `themes.json` in the batch.
2. Build the scaffolds (safe to run first to see structure + TODOs):
   ```bash
   python3 "$CLAUDE_PLUGIN_ROOT/scripts/build.py" --batch <batch-dir>
   ```
   This writes `<batch>/themes/<slug>.md` per theme with front matter
   (`id, label, source_count, authors, date_range`), **Contributing sources — by
   author**, and a **Timeline**, all backlinked to the source `.md` files.
3. For each theme, read its members' `## Core summary` blocks and compose the
   synthesis as JSON keyed by theme id:
   ```json
   {
     "<theme id>": {
       "summary": "what this conversation is about and where it nets out",
       "precis": "one-line precis",
       "notable": ["standout contribution + who made it"],
       "disagreements": ["the key fault lines and who's on each side"],
       "comment_assessment": "how audiences reacted across the comment sections"
     }
   }
   ```
   Ground every claim in the contributing sources; the backlinks are the evidence
   trail. Stay faithful — represent disagreement fairly.
4. Fill the sections:
   ```bash
   python3 "$CLAUDE_PLUGIN_ROOT/scripts/build.py" --batch <batch-dir> --spec spec.json
   ```

Exit codes: `0` ok · `2` missing themes.json (run theme-cluster) · `3` error.
