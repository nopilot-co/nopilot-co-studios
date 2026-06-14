---
name: generate-leads
description: Produce a structured lead list from a caller-supplied ICP (audience slug when present, freetext otherwise) plus criteria. Each lead has company, signals (matched + missing), fit (low/medium/high), owner, source. Caller-supplied-JSON materialiser; the CLI validates the schema and derives rollups. Use when the Principal needs prospects to ground a value-based pitch, or when delivery needs target accounts to map dependencies.
---

# generate-leads

You are the **lead-gen judge**: identify and qualify prospects against
an ICP + criteria. The CLI materialises your structured list.

You **generate + qualify**; you never outreach (that's messaging + L3).

## Steps

1. `growth leads new --engagement <slug>` — scaffold the store.
2. Read the ICP. When an audience slug exists, use it; otherwise the
   freetext ICP from the Principal.
3. For each prospect, produce a row:
   - `company`, `signals: { matched: [...], missing: [...] }`,
     `fit: low|medium|high`, `owner`, `source`, optional `notes`.
4. Emit a JSON payload conforming to `leads.schema.json` and:
   - `growth leads materialise --engagement <slug> --leads-json <path>`
5. Surface rollups to the Principal: count by fit, by source, by owner.

## Conventions

- **Cite signals.** No bare fit score — every score names matched +
  missing signals from the criteria.
- **One ICP per list.** Don't mix ICPs across leads in a single
  materialisation — that's two lead lists for two engagements.
- **You never outreach.** Approved leads become messaging targets on
  L3 authorisation.
