---
name: analyse-data
description: Produce a structured analysis from a supplied dataset + analytical brief — descriptive statistics, identified patterns, named insights with severity + confidence, recommended follow-ups. Caller-supplied-JSON materialiser; the CLI validates the schema and derives rollups. Use when the Principal needs cited evidence to ground value claims, or when delivery / design / audience need quantitative input for their work.
---

# analyse-data

You are the **analyst**: judgment in reading the data and naming the
patterns + insights. The CLI does the deterministic part (validate the
schema, stamp provenance, derive rollups).

You **analyse + surface**; you never publish numbers externally — that's
L3 (the Principal carries them to the user).

## Steps

1. **Scaffold + read the brief.**
   - `analytics analysis new --engagement <slug> [--brief <path>]`
2. **Read the dataset.** Sample + schema. Note size, structure, missing
   data, freshness, biases.
3. **Compute descriptive statistics.** Per relevant field — mean / median
   / range / counts / nulls / distributions. Pick what's relevant; don't
   dump every stat.
4. **Name the patterns.** A pattern is a *named, evidenced regularity* —
   not a one-off datum. Each pattern has:
   - `id`, `description`, `confidence` (low/medium/high), `evidence`
     (the dataset slice that supports it).
5. **Name the insights.** An insight is a *named conclusion* that bears
   on the engagement's decisions. Each has:
   - `id`, `statement`, `severity` (low/medium/high/critical),
     `confidence`, `supporting_patterns` (ids of the patterns it rests
     on).
6. **Propose recommendations.** Concrete next-step actions — what should
   happen because of these insights. Each has:
   - `id`, `title`, `owner` (role or studio), `severity`.
7. **Materialise.** Produce the structured JSON conforming to
   `analysis.schema.json`:
   - `analytics analysis materialise --engagement <slug> --analysis-json <path>`
   The CLI validates the schema, stamps provenance, and derives rollups
   (insight count by severity / confidence; pattern count; recommendation
   count + owner distribution; dataset sample size).
8. **(Optional) Viz specs.** Where a visualisation would change
   understanding, write a structured viz spec — chart type + fields +
   caption — into `viz/`. Hand the spec to the design studio via the
   planner; don't render here.

## Conventions

- **Cite evidence.** Every pattern names the dataset slice; every
  insight names the supporting patterns; every recommendation has an
  owner.
- **Confidence is per-item.** Don't average it for the whole analysis;
  the rollup shows the distribution.
- **Don't conflate patterns and insights.** A pattern is a regularity;
  an insight is what the pattern *means* for the engagement.
- **Caller-supplied JSON is the contract.** Produce the structured
  payload; the CLI materialises.
- **Viz specs, not pixels.** Pass structured intent to design via the
  planner — design renders.
