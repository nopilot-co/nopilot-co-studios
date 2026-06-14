---
name: ingest-context
description: Pull source material into the per-engagement context store by orchestrating the tools tier (notion-sources, source-enrich, source-summarise, yt-transcript). Caller-supplied-JSON pattern at the summariser step. Use when the Principal or audience studio needs a body of cited research for an engagement; or when a new engagement is starting and source material is supplied (Notion DB, URLs, files, YouTube videos).
---

# ingest-context

You are the **ingest orchestrator**: judgment in deciding what to pull,
how to handle the materialiser stops, and what to flag back to the
Principal. The `context` CLI does the deterministic part (scaffold,
chain-and-record, provenance). The actual file-touching work lives in the
tool-bench CLIs (`notion-sources`, `source-enrich`, `source-summarise`,
`yt-transcript`) — you call them via `context ingest …`.

## Steps

1. **Scaffold the engagement store.**
   - `context engagement new --engagement <slug>`
2. **Pull sources** from the supplied origin(s):
   - Notion database → `context ingest --engagement <slug> --notion-db <id>`
   - URL / file → `context ingest --engagement <slug> --source <path-or-url>`
   - YouTube → `context ingest --engagement <slug> --youtube <url>`
   Each step records the tool invocation + args + timestamp into the
   engagement's `manifest.json`.
3. **Enrich.** When the supplied sources are URL-based stubs (typical
   from notion-sources), run the enrich step to fetch + populate front
   matter:
   - `context ingest --engagement <slug> --enrich`
4. **Summarise** (caller-supplied JSON stop). Read each enriched source;
   produce model-supplied summaries as JSON conforming to the
   `source-summarise --summary-json` contract; then materialise:
   - `context ingest --engagement <slug> --summarise --summary-json <path>`

## Conventions

- **You orchestrate; the tools materialise.** No source extraction or
  HTML parsing here — that's what the tools do.
- **Caller-supplied JSON is the contract** at the summariser stop. Don't
  write a one-off summariser in the skill.
- **Surface gaps.** If `context doctor` says a needed tool isn't
  installed, flag the gap to the Principal rather than silently skipping
  the step.
- **Cite the manifest.** Every tool invocation is in `manifest.json`; the
  audit trail is the source of truth.
