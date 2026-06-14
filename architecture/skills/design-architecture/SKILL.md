---
name: design-architecture
description: Produce a structured architecture spec for an engagement — systems, data flows, integration points, and ADR-style decision records — from a shaped engagement brief + supplied system context. Caller-supplied-JSON materialiser; the CLI validates the schema and runs invariant checks (referential integrity across systems / flows / integrations); optional diagram render via the design studio (reuse over the CLI boundary). Use when the Principal needs technical truth for L2 scoping, or when the Producer needs system context to sequence the cast.
---

# design-architecture

You are the **architect**: judgment that turns an engagement brief into a
structured architecture spec — systems, data flows, integrations — and
records the load-bearing decisions as ADRs. The CLI does the deterministic
part (schema validation, referential-integrity invariants, provenance,
optional render via the design studio).

You **specify and surface**; you never deploy or change the running
architecture externally. Implementation is the cast's job, downstream.

## Steps

1. **Ingest the brief + system context.** Read the Principal's shaped
   engagement brief and any supplied system context (existing systems, owned
   vs third-party, known constraints). If critical context is missing,
   raise it as a Question (§8).
   - `arch spec new --engagement <slug> [--brief <path>]`

2. **Identify the systems.** Each system has:
   - `id` (kebab-case, stable),
   - `name` + `role` (one sentence: what it does in this engagement),
   - `owner` (team / vendor),
   - `technology` (stack / runtime / persistence),
   - `status` (`existing`, `new`, `evolving`, `retiring`),
   - `criticality` (`low` | `medium` | `high` | `critical`).
   Cover internal + third-party. Be precise: don't conflate "the API" with
   "the integration to it".

3. **Specify the data flows.** Each flow has:
   - `id`,
   - `from` (system id) + `to` (system id) — **both must exist as systems**,
   - `direction` (`one-way` | `bidirectional`),
   - `frequency` (`realtime` | `batch` | `on-event` | `scheduled`),
   - `payload` (one-line shape — names a type or schema),
   - `sla` (when relevant: latency / volume / availability targets),
   - `criticality`.

4. **Specify the integration points.** Each integration has:
   - `id`,
   - `flow` (flow id) — **must reference an existing flow**,
   - `technology` (REST / gRPC / event bus / file transfer / …),
   - `contract` (named schema / proto / OpenAPI ref),
   - `auth` (mTLS / OAuth client-credentials / API key / etc.),
   - `error_handling` (idempotency / retries / DLQ / circuit-breaker).

5. **Materialise.** Produce the structured JSON conforming to
   `architecture.schema.json`. Then:
   - `arch spec materialise --engagement <slug> --spec-json <path>`
   The CLI validates the schema **and** runs the invariants
   (`flow.from / to` exist as systems; `integration.flow` exists as a flow;
   system / flow / integration ids are unique). Materialise rejects on
   invariant breach with a clear list of offenders.

6. **Record decisions.** Every load-bearing architectural choice gets an
   ADR-style record. The minimal shape:
   - `arch adr add --engagement <slug> --title "event bus over REST" --status proposed`
   - then fill in `context`, `decision`, `consequences`, `alternatives`
     (the CLI templates these into the ADR markdown).
   Don't add ADRs for trivial choices. Add one for anything you'd want a
   future engineer to be able to *replay* the reasoning of.

7. **(Optional) Render diagrams.** When the design studio is installed:
   - `arch render --engagement <slug> [--format pdf|html|svg]`
   The bridge sends the spec to the design studio's `render-asset` over the
   CLI boundary; one diagram per cohesive subsystem (or one whole-context
   diagram, depending on scale). Diagrams are an output of the spec, never
   a source of it.

8. **Hand to delivery.** The spec's systems + integrations shape the
   delivery plan's swimlanes (each long-lived system / vendor is a candidate
   swimlane) and the phase dependencies (a flow whose `from` isn't built
   yet is a dependency on the phase that builds it). Surface integration
   risks (third-party vendor, novel protocol) as RAID entries in the
   delivery studio.

## Conventions

- **You specify; you don't deploy.** No "go live" decisions. The spec + ADRs
  are the contract; implementation is downstream.
- **Invariants are CI rules, not stylistic.** A flow referencing a missing
  system is a CI failure. Don't try to talk past it — fix the spec.
- **Caller-supplied JSON is the contract.** Produce the structured payload;
  the CLI materialises. Same skill across invocation modes.
- **One ADR per consequential decision.** Replayable reasoning lives in
  ADRs. Don't bury rationale in the spec body.
- **Diagrams render from the spec.** Never hand-edited. Re-render after
  every spec change.
- **Cite or flag.** Any system claim that's a guess (vendor's SLA,
  third-party throughput) → flagged as `confidence: low` or raised as a
  RAID assumption.
