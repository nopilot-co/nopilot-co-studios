---
description: Produce a structured architecture spec for an engagement — systems, data flows, integration points, and ADR-style decision records. Caller-supplied JSON materialiser; deterministic invariant checks; optional diagram render via the design studio.
argument-hint: <engagement slug> [spec from <path>] [render] [adr <title>]
---

# /architecture-studio

Orchestrate the architecture studio end to end: produce a structured
architecture spec, maintain decision records, and (optionally) render
diagrams via the design studio. The studio **specifies and surfaces**; it
never deploys or changes the architecture externally — that's downstream of
the Producer.

`$ARGUMENTS` names the **engagement slug** and optionally a spec JSON to
materialise or an ADR title to record.

## Pipeline — produce the spec (`design-architecture`)

1. **Scaffold.** `arch spec new --engagement <slug>` — opens the per-
   engagement store. Optionally copy in the shaped engagement brief.
2. **Propose the structure.** Draft systems (each with role, owner,
   technology, status, criticality), data flows (between systems, with
   direction, frequency, payload shape, SLA), integration points (technology,
   contract, auth model, error handling). This is judgment — produce a
   structured JSON payload conforming to `architecture.schema.json`.
3. **Materialise.** Hand the JSON to the CLI. It validates the schema, runs
   the invariant checks (every flow's `from`/`to` references existing systems;
   every integration references an existing flow), stamps provenance, and
   writes `_architecture.yml`.
   - `arch spec materialise --engagement <slug> --spec-json <path>`
4. **Record decisions.** Load-bearing architecture choices get ADR-style
   records (status, context, decision, consequences, alternatives).
   - `arch adr add --engagement <slug> --title "..." [--status proposed|accepted|deprecated]`
   - `arch adr show --engagement <slug>`
5. **(Optional) Render diagrams.** When the design studio is installed,
   `arch render --engagement <slug>` hands the spec to the design studio
   over the CLI boundary; the design studio renders one or more diagrams
   from the systems + flows. Degrades cleanly with an install hint when
   design isn't installed.
6. **Hand to delivery.** The spec's systems + integrations shape the
   delivery plan's swimlanes + dependencies. Surface the high-leverage
   constraints (single points of failure, integration risks) as RAID
   entries in the delivery studio.

## Conventions

- **Spec, then decide.** The spec is the structured truth; ADRs are the
  *why* behind contentious choices. Don't bury rationale in the spec body —
  it lives in ADRs.
- **Invariants matter.** A flow that references a system that doesn't exist
  is a CI failure, not a stylistic nit. The CLI rejects materialise.
- **Caller-supplied JSON is the contract.** Produce the structured payload;
  the CLI materialises. Same skill across invocation modes.
- **Diagrams are an output, not a source.** They render from the spec —
  never hand-edited. Re-render after every spec change.
