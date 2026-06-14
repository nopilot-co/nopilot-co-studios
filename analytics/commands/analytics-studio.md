---
description: Produce a structured analysis from a supplied dataset — descriptive stats, identified patterns, named insights with severity + confidence, recommended follow-ups. Caller-supplied JSON; CLI validates the schema and surfaces rollups (insights by severity, sample size, confidence distribution).
argument-hint: <engagement slug> [analysis from <path>] [show]
---

# /analytics-studio

Orchestrate the analytics studio: produce a structured analysis from a
supplied dataset + brief, and surface rollups (insights by severity,
sample size, confidence distribution).

`$ARGUMENTS` names the **engagement slug**; subsequent flags select the
action (materialise, show).

## Pipeline — analyse-data

1. **Scaffold.** `analytics analysis new --engagement <slug>` — opens
   the per-engagement store. Optionally copy in the analytical brief.
2. **Produce the analysis.** The model reads the supplied dataset + brief
   and produces a structured JSON payload conforming to
   `analysis.schema.json`. The payload has 4 sections:
   - `dataset` — source + sample_size + schema summary
   - `descriptive_statistics` — relevant stats, by field
   - `patterns` — named patterns (id, description, confidence, evidence)
   - `insights` — named insights (id, statement, severity, confidence,
     supporting_patterns)
   - `recommendations` — next-step actions (id, title, owner, severity)
3. **Materialise.** Hand to the CLI:
   - `analytics analysis materialise --engagement <slug> --analysis-json <path>`
   The CLI validates the schema, stamps provenance, and derives rollups
   (insight counts by severity / confidence; recommendation owner
   distribution; pattern count).
4. **Hand off.** The Principal grounds value claims with the insights;
   delivery references the recommendations for follow-up phases; design
   renders any viz specs via the planner.

## Conventions

- **Cite or flag.** Every insight names its supporting patterns; every
  pattern names the evidence (rows / fields / dataset slice).
- **Confidence is per-item.** Don't average it for the whole analysis —
  the rollup shows the distribution.
- **Caller-supplied JSON is the contract.** The model produces the
  structured payload; the CLI materialises it.
- **Viz specs, not pixels.** Hand viz intent (chart type + fields +
  caption) to the design studio via the planner; don't render here.
