# Architecture Decisions

Architecture Decision Records for Studios. Newest first.

---

## ADR-001 — Server surfaces (modes 2–3): runner, transport, gatekeeper

- **Status:** Accepted (2026-06-03)
- **Issue:** #23
- **Context:** The studios architecture defines three invocation modes that must
  preserve one invariant — the *same* studio skills, run over the *same*
  deterministic CLI, produce identical outputs regardless of trigger or LLM host.
  Mode 1 (local plugin) ships today. Modes 2–3 (local CLI dispatched from a
  server; fully server-side) are unbuilt. The blocking question was *how* to
  execute the markdown skills off the laptop without reimplementing studio logic.

### Decisions

1. **Skill-execution runner → Claude Code headless (`claude -p`).**
   The server dispatches each job to the same Claude Code harness the laptop
   uses, in print/headless mode, with the studio plugin loaded and the same tool
   surface (Read, Bash → `studio` CLI, MCP). This is the *strongest possible*
   guarantee of the consistency invariant: it is literally the same executor.
   - *Trade-off:* Anthropic-only today, which the issue title ("provider-agnostic")
     anticipates as a goal, not a v1 requirement. We isolate the executor behind a
     `Runner` interface (`run(job) -> ResultEnvelope`) so a provider-agnostic
     harness can be added later without touching transport, gatekeeper, or studios.

2. **Transport → MCP server.**
   The creative-director is exposed as an MCP server so any caller (soma-anansi,
   any LSP, another agent) invokes it the *same way Claude invokes any MCP* —
   matching the issue's framing. Tool surface (v1): `submit_brief`, `get_job`,
   `list_studios`. Results return as a structured result envelope.
   - *Trade-off:* async job semantics over a tool interface (submit → poll
     `get_job`) rather than a long-blocking call; acceptable and conventional.

3. **Gatekeeper → bearer token + deny-by-default outward.**
   Callers authenticate with a per-caller/tenant bearer token. Local work
   (render, QA) runs freely. Outward sends (Gamma/Canva/Slack/Gmail) are denied
   unless the submitted job carries an explicit per-action grant
   (`grants: {gamma: true, ...}`); ungranted outward steps return as
   `pending_approval` in the envelope rather than firing. This preserves the
   "confirm before outward send" invariant in a non-interactive context.

### Consequences

- A new top-level `server/` component (outside the studios) hosts the MCP server,
  gatekeeper, job store, and runner — it is an orchestrator/store, never a place
  where studio logic is reimplemented.
- The storage-root abstraction (`$STUDIOS_DOCKET_ROOT` / `$STUDIOS_PROJECT_ROOT`,
  already in `design/scripts/studio/__init__.py`) is the seam the server uses to
  point each job at server-side storage.
- Provider-agnostic execution is explicitly deferred behind the `Runner` seam.

See [`server-modes-spec.md`](server-modes-spec.md) for the build spec.
