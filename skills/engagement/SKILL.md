---
name: engagement
description: Maintain the engagement-level manifest (engagement.json) over a production docket — brief, cast, jobs, first-class Questions / Blockers / Risks (Bible §8), Decisions (Bible §7), L2 / L3 Checkpoints (Bible §6), and a deterministic rollup. Used by the Producer as they sequence jobs across the cast, and read by the Principal via `engagement status` when walking the engagement back to the user. Use whenever an engagement needs auditable, replayable state.
---

# engagement

You are the **engagement orchestrator**: maintain `engagement.json` —
the engagement-level analogue of the planner's `composition.json`. The
manifest is the structured state of an engagement: what it is, who's on
it, what's running, what's open, what's been decided, what's waiting on
the user.

The `engagement` CLI does the deterministic part (validation, id
allocation, status transitions, rollup recomputation). You provide the
judgment — which cast to pick, which jobs to spawn, which Question to
escalate, when to clear a Checkpoint.

The Producer maintains this manifest as it sequences jobs. The Principal
reads it (via `engagement status`) to walk state back to the user.

## Lifecycle

1. **Scaffold.** The Principal (or whoever opens the engagement) runs:
   ```bash
   engagement new --root <docket> --engagement <slug> \
     [--objective "..."] [--audience <slug>] [--client <slug>]
   ```
   This writes `engagement.json` with the brief skeleton.

2. **Shape the brief.** Fill in objectives, audience, constraints,
   success criteria:
   ```bash
   engagement brief --root <docket> --objective "..." \
     --constraint "deadline 2026-08-30" --success "L2 sign-off by …"
   ```

3. **Pick the cast.** For each chosen role, justify in one line:
   ```bash
   engagement cast add --root <docket> --role design \
     --justification "renderer for the proposition deck"
   ```

4. **Open jobs.** Each job is one invocation of a capability. **Declare
   the action class** (Bible §6) — L0 gather, L1 draft (default), L2
   decide, L3 deliver:
   ```bash
   engagement job add --root <docket> --capability render-asset \
     --role design --title "investor deck v1" --action-class L1
   # → J-001 planned (L1)

   engagement job add --root <docket> --capability assess-commercial-value \
     --role commercial --title "Value-based scoping" --action-class L2
   # → J-002 planned (L2) — will need a cleared Checkpoint before done

   engagement job add --root <docket> --capability compose-message \
     --role messaging --title "Send proposal email" --action-class L3
   # → J-003 planned (L3) — will need cleared CP + decided_by before done
   ```
   As work progresses:
   ```bash
   engagement job set --root <docket> --id J-001 --status in-progress
   engagement job set --root <docket> --id J-001 --status done
   ```
   For L2 / L3 jobs the `done` transition is **gated** — see step 7
   (Checkpoints) and the autonomy section below.

5. **Surface open items first-class** (Bible §8). Don't bury Questions /
   Blockers / Risks in prose — every one is a row:
   ```bash
   engagement item add --root <docket> --kind question \
     --title "Does the user want a pitch deck or a brochure?" \
     --raised-by principal --needs user --blocking J-001
   engagement item resolve --root <docket> --kind question --id Q-001 \
     --resolution "Pitch deck"
   ```

6. **Record decisions** (Bible §7). Every consequential judgment gets a
   pointer:
   ```bash
   engagement decision add --root <docket> \
     --title "value-based price band £75k-£250k" \
     --role commercial --ref clients/acme/assessment.yml
   ```

7. **Open L2 / L3 checkpoints** (Bible §6). A Checkpoint pauses the
   engagement and surfaces a decision to the Principal → user:
   ```bash
   engagement checkpoint open --root <docket> --level L2 \
     --title "Confirm scope + investment band" \
     --raised-by principal --evidence clients/acme/assessment.yml
   engagement checkpoint clear --root <docket> --id CP-001 \
     --outcome "Approved at £150k" --decided-by user
   ```

8. **Report status.** The deterministic rollup is the source of truth
   the Principal carries back:
   ```bash
   engagement status --root <docket>
   # → engagement / status / rollup (jobs total + by_status / percent_complete /
   #   open_questions / open_blockers / open_risks / pending_checkpoints /
   #   next_checkpoint / awaiting_l2 / awaiting_l3 / jobs_by_action_class)
   ```
   For per-job autonomy detail (which L2 / L3 jobs are blocked by what):
   ```bash
   engagement autonomy --root <docket>
   # → one row per job: ✓ can complete · ⛔ blocked: needs cleared CP …
   ```

9. **Close.** Move the engagement through its lifecycle states:
   ```bash
   engagement status --root <docket> --set delivered
   engagement status --root <docket> --set closed
   ```

## Observability — `ledger.jsonl` (Phase 7)

Every mutation that goes through the engagement modules (job add /
set_status, item add / resolve, checkpoint open / clear, decision add)
appends one structured event to `ledger.jsonl` at the docket root —
append-only, one JSON object per line. The manifest gives you *current*
state; the ledger gives you *every transition*.

```bash
engagement ledger show --root <docket> [--kind job.set_status] [--subject J-001] [--limit 50]
engagement ledger tail --root <docket> --limit 20      # JSONL on stdout
```

Events carry: `at`, `actor` (role or `system`), `kind`, `subject` (the
id the event is about), `summary`, and a `details` payload (status
transition, action class, decided_by, etc.). The ledger plus the
manifest plus the per-artefact provenance (composition.provenance,
audience model provenance, etc.) is the audit + replay backbone.

## SoR bridge — GitHub Projects (Phase 7)

The docket is canonical. The Producer maintains it; everything else
is a *projection*. v0.1.0 ships the **GitHub Projects adapter** as a
sync-plan builder:

```bash
engagement sync github --root <docket> --owner <gh-owner> [--project "Title"]
# → JSON plan: project, upsert-issue per job/Q/B/R, status_move per job,
#   check per checkpoint, comment per decision. Includes a
#   conflict-rule note + respect_inbound_edit flags so live `gh` writes
#   skip overwriting user edits.
engagement sync github --root <docket> --owner <gh-owner> --apply
# → v0.1.0 dry-runs even with --apply; live `gh` calls land in v0.1.1.
```

Mapping (Bible §8):

| Docket entity | GitHub Projects |
|---|---|
| engagement | Project |
| job (J-NNN) | Issue / card, status column = job.status |
| question (Q-NNN) | Issue labelled `question` |
| blocker (B-NNN) | Issue labelled `blocked` |
| risk (R-NNN) | Issue labelled `risk` |
| decision (D-NNN) | Comment + ADR pointer |
| checkpoint (CP-NNN) | Check on the blocking job(s) |

The adapter pattern is in `scripts/engagement/sor/` — adding Jira or
Linear is one new class implementing `SoRAdapter.build_sync_plan`.

## Conventions

- **The manifest is the source of truth.** Don't paraphrase its state in
  prose. The rollup is the contract surface the Principal reads.
- **First-class open items.** Questions, Blockers, Risks live as rows —
  not in chat or commit messages. Each carries needs (`user` / `client`
  / `role`) so the Principal knows who to ask.
- **Decisions point; they don't duplicate.** Each decision is a pointer
  to a record (ADR, assessment, plan). The full content lives where the
  decision was made.
- **Checkpoints are the autonomy gate — contract-enforced.** L2 (scope
  / price / cast / any binding commitment) and L3 (any outward delivery)
  must be open Checkpoints, not implicit. As of Phase 6 this is a CLI
  invariant: a job declared `--action-class L2` or `L3` **cannot** move
  to `done` unless there's a cleared Checkpoint that lists the job in
  `blocking_jobs[]`; L3 additionally requires the Checkpoint to carry
  `decided_by` (explicit human authorisation, never automated). Attempts
  exit with code 4 and a typed `AutonomyError` so callers can branch on
  the rule. Inspect per-job state with `engagement autonomy --root <docket>`.
- **Rollup is derived; never hand-set.** Every write recomputes the
  rollup from the canonical fields.
- **History is append-only.** Every mutation adds a one-line note.

## Conventions for the Producer

When you (the Producer) advance a job, mirror the state into the
manifest. When a cast role surfaces a Question/Blocker/Risk, file it.
When a job hits an L2 boundary, open a Checkpoint and tell the
Principal. The manifest is how the Principal sees what you're doing —
keep it current.
