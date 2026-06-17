---
name: reflect
description: At the close of a studio run, reflect on how the plugin/studio ITSELF could be improved — its skills, CLIs, formats, assets, orchestration, or docs — and capture it as a durable, append-only learning via the `learnings` CLI. This is distinct from critiquing the deliverable. Use at every engagement close, or when the reflection gate fires at session end.
---

# reflect

You are closing a run. Before you stop, spend one short beat on the **tooling**,
not the deliverable: *what about the studio itself — its skills, CLI, formats,
assets, orchestration, or docs — slowed us down, surprised us, or could be
better next time?*

This is the studio improving the studio. The client work is judged by the
nitpicker / audience / visual-qa skills; **this skill is only about the plugin.**

## Steps

1. **Recall the friction.** Look back over the run for anything awkward, manual,
   repeated, missing, or confusing in the *tooling* — e.g. a CLI flag that
   should exist, a skill step that misled, a format/asset gap, a render that
   needed a hand-fix, an orchestration order that was wrong.

2. **Decide if there's a real learning.** A learning is a concrete,
   tool-directed improvement — not "the client copy could be punchier" (that's
   deliverable critique). If there's genuinely nothing, that's fine — record it
   explicitly in step 4 so the trail stays honest.

3. **Classify** each learning into one `category`:
   `skill` · `cli` · `format` · `asset` · `orchestration` · `docs`. Pick a
   `severity` (`low` / `medium` / `high`) — `high` = it blocked the run or
   silently corrupted output.

4. **Capture it** with the deterministic CLI (the judgment is yours; the CLI
   does the file, schema, and id):

   ```bash
   # one call per distinct improvement
   learnings add \
     --studio <studio|cross> \
     --category <skill|cli|format|asset|orchestration|docs> \
     --severity <low|medium|high> \
     --title "<one line>" \
     --proposed-change "<the concrete change>" \
     [--engagement <slug>] [--body "<detail>"]

   # nothing worth recording this run? say so — keeps the audit honest
   # (this also satisfies the reflection gate):
   learnings none --engagement <slug> --reason "<why nothing this run>"
   ```

5. **Stop.** Don't open issues or ADRs here — high-severity or recurring items
   are promoted later by the maintainer (`learnings promote …` → a GitHub issue
   or an ADR in `docs/architecture/DECISIONS.md`). Capture is cheap; promotion
   is deliberate.

## Conventions

- **One learning per distinct improvement** — don't bundle several into one.
- **About the tool, not the client work.** If you can't name the skill / CLI /
  format / asset / orchestration step / doc it touches, it isn't a learning.
- **Append-only.** `learnings/` is never edited except a learning's `status`
  (`open → triaged → promoted | wontfix | fixed`). Never delete a record.
- **Engagement *decisions* still go to ADRs** via the engagement manifest
  (`engagement decision add`); this skill is for *plugin* improvement only.
- Reference the run or related learnings by slug in `--body`.
