---
name: extend-context
description: Append additional sources to an engagement's context store and re-run enrich + summarise incrementally; optional remap. Caller-supplied JSON at the summarise / cluster / entity materialiser stops. Use when new source material arrives mid-engagement (a fresh article, a transcript, a competitor announcement) and the existing context store needs to absorb it without rebuilding from scratch.
---

# extend-context

You are the **extender**: judgment in deciding what to ingest next, when
to remap (the new source shifts the thematic frame), and what to flag
back to the Principal. The CLI does the deterministic part (append the
manifest, run incremental enrich + summarise, optionally re-trigger map).

## Steps

1. **Append the source.** Notion-style stub or full file / URL:
   - `context extend --engagement <slug> --source <path-or-url> [--kind notion|url|file|youtube]`
   The CLI appends to `sources.json` (or via `notion-sources` if the
   source is a Notion row id) and records the invocation in
   `manifest.json`.
2. **Enrich incrementally.** Only new sources are processed:
   - `context extend --engagement <slug> --enrich`
3. **Summarise** (caller-supplied JSON stop). Hand the model-produced
   summaries for the new sources only:
   - `context extend --engagement <slug> --summarise --summary-json <path>`
4. **(Optional) Remap.** If the new sources materially shift the
   thematic frame, re-run map-context — propose → cluster → entity — over
   the full updated batch:
   - `context extend --engagement <slug> --remap` (then follow the
     map-context pipeline with fresh caller-supplied JSON).

## Conventions

- **Incremental by default.** Don't re-enrich already-enriched sources
  unless the underlying source changed.
- **Caller-supplied JSON for the new slice.** The summariser step
  consumes JSON keyed by the new source ids only.
- **Remap is a deliberate choice.** Don't trigger it on every extend —
  surface to the Principal that the new sources shift the framework and
  get a confirm.
