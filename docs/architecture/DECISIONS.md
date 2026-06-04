# Architecture Decision Records

ADRs for nopilot-co-utilities. Newest first.

---

## ADR-002 — Thematic evidence-base pipeline (`source-summarise`, `theme-cluster`, `theme-entity`)

- **Date:** 2026-06-04
- **Status:** Accepted (stubs)
- **Issue:** [#7](https://github.com/nopilot-co/nopilot-co-utilities/issues/7)
- **Builds on:** ADR-001 (`source-enrich`)

### Context

The aim is a **thematic sourced evidence base for a thought-leadership
conversation**: take the enriched source batch and turn it into themed dossiers
that show what each contributor argued, where they agree/disagree, how audiences
reacted, and a sourced trail back to every contribution.

### Decision

Three utilities extend the pipeline, each shipped first as a **stub**:

```
notion-sources → source-enrich → source-summarise → theme-cluster → theme-entity
```

1. **source-summarise** — per source: neutral summary, overall `position`,
   `core_arguments`, and `comment_reaction`.
2. **theme-cluster** — group sources into themes (consistent core discussion
   threads) → `themes.json` (+ optional `themes:` front-matter tags).
3. **theme-entity** — render a theme entity doc per theme: summary, precis,
   notable contributions, key disagreements, comment-reaction assessment, and
   backlinks to contributing sources **grouped by author and by timeline**.

**Mechanical-CLI + model-supplied-JSON split** (consistent with ADR-001's
`--html-file` and youtube-transcript's `--chapters-json`): the standalone CLI
does all deterministic work — manifest I/O, member resolution, backlink paths,
author/timeline grouping, Markdown/front-matter rendering — and the skill drives
the semantic work (summarising, theming, synthesis), feeding results back as
JSON (`--summary-json`, `--assignments`, `--spec`). This preserves the
standalone-first marketplace rule while keeping LLM judgement where it belongs.
Running any CLI with no JSON prints its schema + a readiness check.

### Consequences

- Standalone-first holds: no utility hard-depends on an LLM; a future version may
  add an optional direct-API engine or a deterministic clustering baseline.
- Theme docs are an auditable evidence base — every synthesised claim backlinks to
  source `.md` files, grouped by author and ordered on a timeline.
- Stubs render semantic sections as `_TODO_` placeholders until wired; versions
  start at `0.0.1`.

---

## ADR-001 — `source-enrich` enrichment approach (tiered fetch, in-place, polite escalation)

- **Date:** 2026-06-04
- **Status:** Accepted
- **Issue:** [#3](https://github.com/nopilot-co/nopilot-co-utilities/issues/3)
- **Relates to:** `notion-sources` (produces the batch this consumes) — [#2](https://github.com/nopilot-co/nopilot-co-utilities/issues/2)

### Context

`notion-sources` emits a batch of per-source `.md` stubs + a `sources.json`
manifest. The next step is to enrich each source: fully populate its front
matter, extract the article body, download attached assets, and append an
Appendix. The batch is **~70% LinkedIn post URLs** (plus X, Google Forms,
YouTube, blogs/Substack/Medium). LinkedIn and X are auth-walled and
anti-scraping, so a plain HTTP fetch returns a login wall, not the content.

### Decision

Build `source-enrich` as a self-contained marketplace utility with these locked
requirements:

1. **Tiered fetch engine.**
   - Python core (`trafilatura`) fetches + extracts normal pages to Markdown
     with metadata. Runs standalone, no external service.
   - YouTube URLs reuse the `youtube-transcript` utility for the body.
   - Pages the core can't crack (login wall / JS shell / empty) are flagged
     **`blocked`** rather than producing garbage.

2. **Escalation is explicit, opt-in, and polite — never auth-bypassing.**
   - Blocked sources are escalated only through **the user's own logged-in
     browser session** (`connect-chrome`, using the user's cookies) or a
     stealth fetch service (Firecrawl). We do **not** scrape around LinkedIn/X
     authentication or impersonate logged-in APIs.
   - The CLI accepts pre-fetched content via `--html-file` / `--md-file`, so the
     skill (or the user) supplies the rendered HTML and the CLI runs the same
     extraction/asset/appendix path. Logic stays in the CLI; orchestration in
     the skill.
   - Default politeness: realistic browser UA, inter-request `--delay`, request
     timeout, optional `--respect-robots`. This is personal research over
     links the user already captured.

3. **Enrich in place.** Rewrite each `NNNN-<slug>.md`: fill null front-matter
   fields, replace the stub body with the extracted article, append a
   `## Appendix — Assets` section, and record an `enrich_status`
   (`enriched | partial | blocked | error`) **without** overwriting the Notion
   `status` field. The run is **resumable** (skips already-enriched unless
   `--reenrich`). The manifest entry is updated.

4. **Assets: images + documents.** Download inline content images and linked
   documents (pdf/doc/ppt/xls/csv/zip…) into `assets/<slug>/`, size-capped
   (`--max-asset-mb`), deduped by content hash; rewrite body image refs to local
   paths. The Appendix lists Images / Downloads / Catalogued-not-downloaded with
   local path + source URL + size.

### Consequences

- Clean blogs/news/Substack/Medium/YouTube enrich fully and unattended.
- LinkedIn/X enrich **only** when the user has connected a logged-in browser
  session; otherwise they remain honestly flagged `blocked` — no fabricated or
  partial-garbage bodies.
- One new third-party dependency (`trafilatura`, plus `PyYAML` for safe
  front-matter round-tripping); installed by the utility's `install.sh`.
- The `--html-file` ingest contract keeps the CLI standalone while allowing
  model/browser-driven escalation, satisfying the marketplace standalone-first
  rule.
