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

4. **Open jobs.** Each job is one invocation of a capability:
   ```bash
   engagement job add --root <docket> --capability render-asset \
     --role design --title "investor deck v1"
   # → J-001 planned
   ```
   As work progresses:
   ```bash
   engagement job set --root <docket> --id J-001 --status in-progress
   engagement job set --root <docket> --id J-001 --status done
   ```

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
   #   next_checkpoint)
   ```

9. **Close.** Move the engagement through its lifecycle states:
   ```bash
   engagement status --root <docket> --set delivered
   engagement status --root <docket> --set closed
   ```

## Conventions

- **The manifest is the source of truth.** Don't paraphrase its state in
  prose. The rollup is the contract surface the Principal reads.
- **First-class open items.** Questions, Blockers, Risks live as rows —
  not in chat or commit messages. Each carries needs (`user` / `client`
  / `role`) so the Principal knows who to ask.
- **Decisions point; they don't duplicate.** Each decision is a pointer
  to a record (ADR, assessment, plan). The full content lives where the
  decision was made.
- **Checkpoints are the autonomy gate.** L2 (scope / price / cast / any
  binding commitment) and L3 (any outward delivery) must be open
  checkpoints, not implicit. The Principal carries them to the user
  (Phase 6 will make this a contract).
- **Rollup is derived; never hand-set.** Every write recomputes the
  rollup from the canonical fields.
- **History is append-only.** Every mutation adds a one-line note.

## Conventions for the Producer

When you (the Producer) advance a job, mirror the state into the
manifest. When a cast role surfaces a Question/Blocker/Risk, file it.
When a job hits an L2 boundary, open a Checkpoint and tell the
Principal. The manifest is how the Principal sees what you're doing —
keep it current.
