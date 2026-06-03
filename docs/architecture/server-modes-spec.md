# Server surfaces (modes 2–3) — build spec

> Issue #23. Decisions locked in [ADR-001](DECISIONS.md). This spec turns those
> decisions into an implementable plan. The **consistency invariant** governs
> everything: the server triggers and stores; it never reimplements studio logic.

## Goal

Let a remote caller (soma-anansi / any LSP / another agent) submit a brief and
receive finished, reviewed artifacts — by running the *same* creative-director
and studio skills the laptop runs, headless, server-side.

## Components (new `server/`, outside the studios)

```
server/
  mcp/            # MCP server: submit_brief, get_job, list_studios
  gatekeeper/     # bearer-token auth + outward-action policy (deny-by-default)
  jobs/           # job store + state machine + result envelopes
  runner/         # Runner interface; v1 impl = ClaudeCodeHeadlessRunner (`claude -p`)
```

`server/` depends on the studios only through their public contracts
(`studios.yml`, each `studio.yaml`, the `studio` CLI) — never their internals.

## Job contract (caller → server)

```json
{
  "brief": "Investor pitch deck for Acme, Series A, 12 slides",
  "brand": "acme",
  "format": "pitch-pptx",
  "source": null,
  "deliver": ["gamma", "slack"],
  "grants": { "gamma": true, "slack": false },
  "tenant": "acme-corp"
}
```

- `brief` required; `brand`/`format`/`source` mirror `design/studio.yaml → inputs`.
- `deliver` = requested outward services; `grants` = which are pre-approved.
  Ungranted services in `deliver` come back as `pending_approval`.

## Result envelope (server → caller)

```json
{
  "job_id": "job_01J...",
  "status": "completed | running | failed | pending_approval",
  "plan": [ "design · render-asset · brand=acme · format=pitch-pptx · → deck" ],
  "artifacts": [
    { "studio": "design", "path": ".../outputs/<session>/outputs/deck.v1.0.0.pptx",
      "format": "pitch-pptx" }
  ],
  "review": { "studio": "nitpicker", "verdict": "pass", "score": 0.86, "findings": [] },
  "deliveries": [
    { "service": "gamma", "status": "sent", "link": "https://gamma.app/..." },
    { "service": "slack", "status": "pending_approval" }
  ],
  "errors": []
}
```

This is the machine form of creative-director SKILL step 8 ("Report"). The skill
already produces all of it as prose; the runner captures it as structured output.

## Runner (the consistency-critical seam)

```
interface Runner:  run(job: Job, storage_root: Path) -> ResultEnvelope

ClaudeCodeHeadlessRunner:
  1. materialize job inputs under storage_root (uses $STUDIOS_PROJECT_ROOT)
  2. spawn `claude -p` with the design-studio plugin loaded + creative-director skill,
     tool surface = Read/Bash(`studio`)/MCP, and the brief as the prompt
  3. constrain outward MCP calls via the gatekeeper (deny-by-default)
  4. parse the agent's final structured report into a ResultEnvelope
```

A future `ProviderAgnosticRunner` implements the same interface; nothing else changes.

## Gatekeeper flow

- **Auth:** bearer token → tenant. Reject unknown tokens at the MCP boundary.
- **Outward policy:** render/QA always allowed. For each `deliver` service, allow
  the send only if `grants[service]` is true; otherwise record `pending_approval`
  and skip the send. (A later iteration may add an async approval queue — out of
  scope for v1; see the rejected option in ADR-001.)

## Build sequence (phased — each phase shippable)

1. **Envelope + job store.** Define `Job` / `ResultEnvelope` schemas (JSON Schema,
   mirroring `studio` schema conventions). In-memory store + state machine. Tests.
2. **Runner v1.** `ClaudeCodeHeadlessRunner` driving `claude -p` against the
   existing plugin; assert a known brief yields the expected artifact + envelope
   (golden test, storage root via env).
3. **Gatekeeper.** Token→tenant auth; deny-by-default outward policy applied to
   the runner's MCP tool surface. Tests for grant/deny/pending_approval.
4. **MCP server.** Expose `submit_brief` / `get_job` / `list_studios`; wire to
   store + runner + gatekeeper. End-to-end test with a stub caller.
5. **Storage hardening.** Confirm `$STUDIOS_PROJECT_ROOT` routes all studio output
   to server-side storage for a job; document the contract.

## Out of scope (v1)

- Provider-agnostic execution (deferred behind the `Runner` interface).
- Async human-approval queue for outward actions (deny-by-default only).
- Horizontal scale / worker pool (single-runner first; queue is a later transport
  swap, not a studios change).

## Open questions to resolve during phase 1

- Job store persistence: in-memory for v1, or SQLite/Supabase from the start?
- `claude -p` session/plugin bootstrapping on the server image (Brewfile parity).
- Multi-tenant storage isolation under `$STUDIOS_PROJECT_ROOT`.
