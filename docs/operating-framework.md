# The Studio Operating Framework

> The canonical operating model for nopilot-co-studios — its vision, principles,
> entities, roles, method, and governance. This is the "Bible": the single source
> of truth for **how the studio wins and delivers work**, for clients/prospects and
> delivery teams alike.
>
> **Status:** living document, v1. The studio is mid-transition from a
> creative-only studio to a multi-discipline one. Sections below mark **Today**
> (built) vs **Target** (the model we are building toward) so this stays honest.
> This document is itself a piece of **service design**, produced and maintained
> via the studio's own method (see §9).
>
> **Scope note.** This is the *operating model* (for humans and agents). It is
> distinct from `CLAUDE.md` (machine instructions for the coding agent) and from
> per-studio `CLAUDE.md` files (a studio's internal contract). When they conflict,
> this framework sets intent; the `CLAUDE.md` files set mechanics.

---

## 1. Purpose & Vision

The studio exists to **refine an opportunity into a response that wins hearts and
minds and solidifies shared intent.** It takes an opportunity — mapped as a brief —
and ideates a **creative, technical, commercial, and delivery** response that gives
every constituent (the client/prospect *and* the delivery team) clarity of
**purpose, method, and required investment**.

The output is **ideas, represented in the clearest, most work-winning format the
moment requires** — proposals, pitches, commercial models, delivery plans,
technical specs, propositions, build plans, timelines, roadmaps, system documents,
data analyses, thought leadership, explainers, advocacy content.

Every such deliverable carries the same three payloads:

- **What** — the idea / the recommendation.
- **Why** — the evidence and reasoning that make it credible (decision-making input).
- **How** — the method, plan, and investment to execute it (execution instruction).

We call this assembled deliverable the **Proposition** (§3). The purpose of
every Proposition is twofold: **win the work** (persuade) and **enable the
work** (instruct). It is simultaneously a sales artefact and a delivery artefact.

---

## 2. Principles (Invariants)

These are non-negotiable. Every studio, role, and tool upholds them.

1. **Judgment in skills, mechanics in CLIs.** LLM judgment lives in markdown skills;
   deterministic file ops, calculations, validation, and rendering live in a
   package/CLI. They mirror 1:1. This is what makes outputs identical whether a job
   runs on a laptop, via a server's CLI, or server-side.
2. **Deterministic seams.** The boundaries *between* jobs are deterministic. Judgment
   is bounded inside a job; hand-offs are typed artefacts and CLI calls. This is what
   makes the whole auditable and replayable.
3. **Canonical truth lives in the docket.** The production docket is the durable,
   portable system of record for an engagement — artefacts, decisions, status. Other
   surfaces (e.g. GitHub Projects) are *projections* of it (§8).
4. **Reuse over reinvention, across CLI boundaries.** A capability that needs another
   studio's engine calls it over its CLI rather than re-implementing it (e.g.
   planner → `studio docket`, audience → `nit aggregate`, nitpicker → audience model).
   Packages stay independently installable; logic stays single-sourced.
5. **Human gates on stakes and outward actions.** Local, reversible work is
   autonomous; strategic decisions and anything outward-facing or irreversible
   require explicit human authorisation (§6).
6. **Evidence and provenance on every claim and decision.** Assertions cite sources;
   decisions record their rationale, alternatives, and author (§7).
7. **Extensible by registry.** A capability becomes routable the moment it is
   registered (`studios.yml` + a manifest) — adding one does not require editing the
   orchestrator.

---

## 3. Entities (canonical vocabulary)

Use these words precisely; they are the shared language of the framework.

| Entity | Definition |
|---|---|
| **Opportunity** | A potential piece of work, before it is shaped. Raw. |
| **Brief** | A shaped opportunity: objectives, audience/client, constraints, success criteria. The Principal's first output. |
| **Engagement** | One run of the studio against a brief, from intake to delivery. The top-level unit of work. |
| **Cast** | The subset of roles chosen for an engagement's scope. Not every role is used every time. |
| **Role** | A named function in the operating model (Principal, Producer, Commercial Officer, Technical Architect, …). Realised as a studio, a skill, or an orchestration skill. |
| **Capability** | A typed thing a studio can do (`render-asset`, `assess-audience-fit`, `check-commercials`, …), declared in its `studio.yaml` and indexed in `studios.yml`. Roles are routed by capability, not by name. |
| **Studio** | A self-contained service offering: skills (judgment) + a deterministic CLI (mechanics) + a `studio.yaml` manifest + a data root. Owns a durable, reusable artefact type. |
| **Skill** | One unit of LLM judgment (a `SKILL.md`). Studios are built from skills. |
| **Orchestration skill** | A root-level skill that coordinates and holds no artefact of its own (Principal, Producer, planner). |
| **Job** | One invocation of a capability within an engagement, with typed inputs and outputs. The unit of observation and status. |
| **Artifact** | Any typed output (a deck, a commercial model, a delivery plan, a section, a reader model). Carries provenance. |
| **Proposition** | The assembled, reader-facing deliverable for an engagement (§1) — the work-winning artefact built from the cast's artefacts. |
| **Gate** | A review checkpoint that returns a verdict (nitpicker objective review, audience reader-fit, beancounter commercials check). |
| **Decision** | A recorded consequential judgment: *what, why, alternatives, evidence, role, when* (§7). |
| **Question / Blocker / Risk** | First-class open items needing resolution: a Question awaits an answer (user/client/role); a Blocker halts jobs; a Risk is a tracked threat (§8). |
| **Checkpoint** | A point where the engagement pauses for human authorisation (an L2/L3 boundary, §6). |
| **Docket** | The production folder that is the engagement's canonical store (artefacts, manifest, decisions, ledger). Portable and offline-capable. |
| **Engagement manifest** | `engagement.json` in the docket — the canonical state of the engagement (cast, jobs, questions, blockers, risks, decisions, rollup). |
| **SoR projection** | A live mirror of engagement state in the user's system of record (GitHub Projects by default), kept coherent with the docket (§8). |

---

## 4. Roles & the Cast

### The two standing roles (front-of-house + orchestration)

- **Principal** *(Today — orchestration skill at `skills/principal/`; the single
  point of contact).* The user always talks to the Principal. It owns the
  relationship and the **what/why**: intake and objective clarification; client,
  audience, and market mapping; value-based scoping and pricing; **choosing the
  cast**; representing the work back to the user; and all L2 sign-offs. It uses
  the Commercial, Growth/BD, and Audience capabilities to do its mapping (today
  only Audience is routable; Commercial and Growth/BD degrade to prose with the
  gap flagged until those studios ship). It is accountable for the engagement.
  `/studio` enters here.

- **Producer** *(Today — orchestration skill at `skills/producer/`; was
  `creative-director`).* Takes the Principal's shaped engagement and owns the
  **how**: assembles the cast, writes each role a focused sub-brief, sequences
  jobs, chains artefacts, runs the gates, and maintains the engagement manifest +
  ledger. It does **not** talk to the client (the Principal does). The rename
  revealed its true nature — the skill was already "a thin coordinator, not a
  maker" — no new behaviour.

> **Why split?** "creative-director" conflated two unrelated jobs — owning the user
> relationship and routing the work. As the cast spans tech/delivery/commercial/data,
> the front door must lead with **strategy**, not creative; and the router should be
> **domain-neutral**. The Principal owns *what + who*; the Producer owns *how*.

### The cast (capability roles)

Chosen per scope — a small brief might use only design + commercial; a transformation
pitch might use most of them.

| Role | Kind | Capability (indicative) | Status |
|---|---|---|---|
| **Design** | Studio | `render-asset` (PDF/PPTX/HTML/RevealJS), `brand-ingest` | **Today** |
| **Messaging** | Studio | `compose-message`, `sequence` | **Today** |
| **Audience** | Studio | `model-audience`, `assess-audience-fit` | **Today** |
| **Nitpicker** | Studio (review-class) | `review-asset`, `run-tests` | **Today** |
| **Planner** | Orchestration skill | composite-document planning + assembly | **Today** |
| **Commercial** | Studio | `check-commercials` (beancounter), `assess-commercial-value` (commercial officer) | **Today** |
| **Growth / BD** | Studio | lead-gen, market research, market mapping | **Target** |
| **Analytics** | Studio | `analyse-data` (patterns, web/engagement, insight) | **Target** |
| **Delivery** | Studio | `plan-delivery` (swimlanes, phasing, resourcing, contingency, RAID) | **Today** |
| **Architecture** | Studio | `design-architecture` (systems, data flows, integrations) | **Target** |
| **Context** | Studio (infrastructural) | `ingest-context`, `map-context`, `extend-context` | **Target** |
| **Quality assurance** | *Extends Nitpicker* | new test batteries + dimensions for technical/delivery quality | **Target** |
| **Brand stewardship** | *Shared resource + nitpicker dimension + Principal remit* | not a maker studio (§ note) | **Today/Target** |

**Classification rule** (how to decide studio vs skill vs review-class): a **studio**
owns a durable, reusable artefact + a data root + deterministic mechanics worth a CLI
+ a routable capability. A **review-class** role judges someone else's artefact
against criteria and **reuses the nitpicker engine** rather than re-implementing
scoring. A **skill** is one judgment step inside a studio. An **orchestration skill**
coordinates and owns no artefact.

> **Brand** is deliberately *not* a maker studio. It has three homes: strategic
> ownership by the Principal, a review dimension in the nitpicker (tone-of-voice +
> brand-spec checks, strengthened into a brand-guardian battery that runs on every
> deliverable), and curation by the Context studio. This gives brand a strong voice
> — client's and agency's — without a redundant studio.

### Decision rights (RACI, summarised)

| | Principal | Producer | Cast role | User / Client |
|---|---|---|---|---|
| Engagement outcome + relationship | **A** | C | I | C |
| Objectives, scope, value/price | **A/R** | C | C | **Approves (L2)** |
| Cast selection | **A/R** | C | I | I |
| Running jobs, sequencing, gates | C | **A/R** | R | I |
| A job's in-domain judgment | I | C | **A/R** | I |
| Outward delivery (send/publish) | A | R | I | **Authorises (L3)** |

---

## 5. The Method (the Engagement lifecycle)

1. **Intake & shape** *(Principal).* Turn the opportunity into a **Brief**: clarify
   objectives, map the client/audience/market, and frame value-based scope. Open the
   docket and the engagement manifest. Raise initial **Questions**.
2. **Select the cast** *(Principal).* Choose the roles the scope needs; state why.
   This is an L2 decision — confirm scope + indicative investment with the user.
3. **Plan & brief** *(Producer).* Decompose the brief into **Jobs** mapped to
   capabilities; sequence them and note chaining; write each role a focused sub-brief;
   record the plan in the manifest.
4. **Produce** *(cast).* Each role runs its pipeline. Gather and draft (L0–L1) are
   autonomous; in-domain consequential calls are recorded **Decisions**; cross-domain
   or value decisions are surfaced as **Checkpoints** (L2).
5. **Gate** *(review-class roles).* Route artefacts through the relevant gates —
   nitpicker (objective + brand + QA), audience (reader-fit), beancounter (commercials).
   Loop findings back to the producing role until the gate passes.
6. **Assemble the Proposition** *(Producer → Principal).* Merge the cast's
   artefacts into the work-winning format(s); ensure the what/why/how payloads are
   present and coherent.
7. **Checkpoint & sign-off** *(Principal ↔ user).* Walk the user through the response;
   resolve open Questions; get L2 sign-off on scope/price/commitments.
8. **Deliver** *(hard-gated, L3).* Publish/send outward only on explicit authorisation.
9. **Reflect & maintain.** Capture learnings; update the canon and shared context.

The **document-planner**, **audience**, and **review** loop already implement steps
3–6 for composite documents (see the reader-driven composite-document play in the
Producer skill). The lifecycle above generalises that play across all disciplines.

---

## 6. Autonomy & Decision Rights

Autonomy is **graduated by action class** — by reversibility × stakes × outwardness —
never global. The default posture is **supervised-autonomous** ("fire-and-checkpoint"):
the studio runs the pipeline unattended through gather + draft, and **pauses at every
strategic decision and every outward/irreversible action.**

| Level | Class | Examples | Autonomy |
|---|---|---|---|
| **L0** | **Gather** | research, analyse, read, capture | Autonomous, always |
| **L1** | **Draft** | produce internal reversible artefacts, render, validate, score | Autonomous; logged |
| **L2** | **Decide** | objectives, scope, **value-based price**, cast selection, commercial model, delivery commitments | **Checkpointed** — role proposes, Principal confirms with the user before it binds |
| **L3** | **Commit / Deliver** | send a proposal, email a client, publish, agree a price externally | **Hard-gated** — explicit human authorisation every time |

- A job may run end-to-end at L0–L1 with no human in the loop.
- Crossing into L2 raises a **Checkpoint**: the engagement pauses, the proposed
  decision + its evidence + alternatives are surfaced, and work resumes on approval.
- L3 is never automated, regardless of trust level.
- Engagements may opt into a stricter posture (step-confirmed) for high-stakes or
  early-trust work, or a looser one (draft-then-review) for speed — but L3 stays hard.

---

## 7. Observability & Provenance

Because the seams are deterministic, **every state transition is a recordable event.**
Four append-only records, all in the docket, answer *what happened, by whom, when, and
why*:

- **Job ledger** (`ledger.jsonl`) — one line per event: job started/ended, by which
  capability/role, inputs → outputs, gates passed, checkpoints hit. The timeline.
- **Decision records** (`decisions/`, ADR-style) — for consequential judgments
  (this scope, this price via value-method Y, this cast): *what, why, alternatives
  considered, evidence (refs), the role, the timestamp*. The "why, by whom".
- **Artifact provenance** — a uniform field on every artefact: which job produced it,
  from what inputs. (Already present as the composition's `source.provenance` and the
  audience model's `provenance.sources`; standardised here.)
- **Gate verdicts** — the structured scorecards/findings from the review-class roles
  (nitpicker, audience, beancounter) are decision evidence in their own right.

**Auditability & replay.** A job's output is determined by its inputs + the skill
version + the CLI version. Given the ledger and provenance, any job can be explained
and, in principle, replayed. This is the trust backbone for client work: nothing is a
black box.

---

## 8. Status, Questions & Systems of Record

### The engagement manifest (canonical)

`engagement.json` in the docket is the single source of truth for engagement state —
the engagement-level analogue of `composition.json`. It holds:

- `brief` — objectives, audience/client, constraints, success criteria.
- `cast` — the chosen roles + why.
- `jobs[]` — each `{id, capability, role, status, inputs, outputs, checkpoint?}`.
- `questions[]` / `blockers[]` / `risks[]` — first-class open items (below).
- `decisions[]` — pointers to the decision records.
- `artifacts[]` — produced artefacts + provenance.
- `checkpoints[]` — pending/cleared L2/L3 gates.
- `rollup` — derived status summary (per-job status, % complete, what's outstanding,
  what's awaiting the user, the next checkpoint).

**Open items are first-class**, never buried in prose:

```
question | blocker | risk:
  { id, type, raised_by_role, raised_at, needs: user|client|role,
    status: open|answered|resolved, resolution, blocking_jobs[] }
```

A deterministic **status rollup** (the analogue of `planner status`) lets the user — or
the Principal on their behalf — see at any moment: where each job is, what remains,
which Questions await them, and the next checkpoint.

### Systems of record: docket canonical, GitHub Projects projection

- **Docket = system of *record*.** Durable, portable, versioned, offline-capable; it
  travels with the engagement. It wins on artefacts and decisions.
- **GitHub Projects = system of *engagement*.** The live collaboration surface where
  the user works day-to-day (the studio default). It wins on human task-status edits.

A deterministic **bridge** projects the docket into the SoR (one-way by default, with
optional inbound for human status edits):

| Docket entity | GitHub Projects |
|---|---|
| Engagement | Project |
| Job | Issue / card (status column) |
| Question | Issue labelled `question`, assigned to who must answer |
| Blocker | Issue labelled `blocked` |
| Risk | Issue labelled `risk` |
| Decision | ADR file + linked issue comment |
| Gate verdict | Check / status label |

**Conflict rule:** on divergence, the docket wins on artefacts and decisions; the SoR
wins on human task-status edits (last-writer per field domain). The bridge is
**adapter-based** so Jira and Linear adapters can be added later without changing the
canonical layer. This formalises the studio's existing rule that GitHub Issues are the
spine — and puts a portable, canonical layer underneath it.

---

## 9. Governance & Maintenance

- **This document is itself a service-design artefact**, produced and maintained via
  the studio's own method: it began as an Engagement whose brief was "design our
  operating model," and it evolves the same way — proposed changes are decisions
  (logged), reviewed through the gates (does it serve clients *and* delivery teams?),
  and versioned.
- **Versioning.** Bump the version line at the top on each substantive change; record
  the rationale as a decision (ADR in `docs/architecture/DECISIONS.md`).
- **Relationship to other canon.** `CLAUDE.md` files are *mechanics* (how the agent
  operates the tools); this framework is *intent* (how the studio wins and delivers).
  `studios.yml` + the `studio.yaml` manifests are the *machine-readable* registry of
  the roles described in §4. Keep them in step: a new role lands as a manifest +
  registry entry **and** an update here.
- **Change discipline.** Prefer extending the registry (a new capability) over editing
  the orchestrators. Keep judgment in skills and mechanics in CLIs. Mark new
  capabilities **Today** here only once they are built and routable.

---

### Appendix — Today vs Target at a glance

- **Today (built & routable):** design, messaging, audience, nitpicker,
  **commercial**, **delivery** studios; the document-planner orchestration
  skill; the **Principal** (front-of-house) and the **Producer**
  (orchestrator, was `creative-director`); the reader-driven
  composite-document play; per-engagement docket + manifests
  (`production-manifest.json`, `composition.json`, `version.json`); review
  gates (nitpicker, audience reader-fit, commercial check-commercials) and
  their scorecards; a first-class delivery plan (swimlanes / phases /
  resourcing / contingency) + RAID register per engagement; a studios-level
  tool-bench (`tools/` — `notion-sources`, `source-enrich`,
  `source-summarise`, `theme-propose`, `theme-cluster`, `theme-entity`,
  `youtube-transcript`) with a CI-enforced dumb-tool invariant.
- **Target (this framework builds toward):** the Growth/BD, Analytics,
  Architecture, and Context studios; QA + brand-guardian batteries in the
  nitpicker; the engagement manifest (`engagement.json`) with first-class
  questions/blockers/risks (today the delivery studio's RAID register fills
  this for delivery-side items); the supervised-autonomy ladder as an
  enforced contract; and the GitHub Projects bridge.
