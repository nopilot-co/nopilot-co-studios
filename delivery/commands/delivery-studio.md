---
description: Turn a shaped engagement brief into a structured delivery plan — swimlanes, phased work with entry/exit criteria, per-phase resourcing + contingency, and a first-class RAID register. Caller-supplied-JSON materialiser; the CLI does the deterministic rollups.
argument-hint: <engagement slug> [plan from <path>] [raid <kind> <title>]
---

# /delivery-studio

Orchestrate the delivery studio end to end: produce a structured plan
(swimlanes + phases + resourcing + contingency) and maintain a live RAID
register against an engagement. The studio **plans and surfaces; it never
commits dates or resources externally** — that's L3 (the Principal carries
commitments to the user).

`$ARGUMENTS` names the **engagement slug** and optionally a plan JSON to
materialise or a RAID entry to add.

## Pipeline — produce the plan (`plan-delivery`)

1. **Ingest the brief.** Read the Principal's shaped engagement brief —
   objective, cast, scope, dates / constraints, open Questions. If a brief
   file is supplied, copy it into the engagement's store.
   - `delivery plan new --engagement <slug>` (scaffolds the store)
2. **Propose the structure.** Draft the swimlanes (parallel workstreams keyed
   to cast roles or studios), the phases (sequenced, with entry + exit
   criteria and dependencies), the per-phase resourcing (day-count by role),
   and the contingency posture (per-phase buffer + an explicit pool). This
   is **judgment** — your output is a structured JSON payload conforming to
   `plan.schema.json`.
3. **Materialise.** Hand the JSON to the CLI; it validates the schema,
   stamps provenance + skill version, derives rollups (total days, phase
   durations, contingency %, by-role totals), and writes `_plan.yml`.
   - `delivery plan materialise --engagement <slug> --plan-json <path>`
4. **Maintain the RAID register.** Risks / Assumptions / Issues /
   Dependencies are first-class (Bible §8 shape). Surface what you've
   identified during planning:
   - `delivery raid add --engagement <slug> --kind risk --title "..." [--severity high]`
   - `delivery raid resolve --engagement <slug> --id <raid-id> --resolution "..."`
5. **Surface for L2.** Report the plan summary (rollups + top risks +
   dependencies) back to the Producer; the Principal carries the
   commitment-bearing parts (dates, resources, milestones) to the user for
   L2 sign-off (Bible §6).
6. **Iterate.** As the engagement runs, re-materialise the plan when scope
   changes and append RAID entries as they emerge. Each materialise bumps
   the plan version so history is auditable.

## Conventions

- **You plan and surface; you never commit externally.** Dates, resources,
  and milestones become commitments only on L3 authorisation.
- **RAID is first-class.** Don't bury risks in prose. Each Risk / Assumption
  / Issue / Dependency is a row with severity, owner, status, and (when
  closed) a resolution. The Bible §8 shape applies.
- **Caller-supplied JSON is the contract.** This studio produces structured
  output; the CLI materialises. No model calls live in the CLI — the same
  skill runs whether invoked as a local plugin or server-side.
- **Reuse over reinvention.** Resourcing day-counts can be costed by the
  commercial studio's rate-card via `delivery plan cost --engagement <slug>`
  (degrades to "rate-card not installed" cleanly).
