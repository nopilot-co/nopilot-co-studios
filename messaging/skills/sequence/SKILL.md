---
name: sequence
description: Compose a multi-step communication sequence (e.g. cold outreach → follow-up → break-up) as a set of linked messaging sessions, each its own format, with escalating/varying angles. Use when the brief is a campaign rather than a single message.
---

# sequence

Plan and compose an ordered set of messages — each its own session and format —
that work together as a campaign.

## Steps

1. **Plan the steps.** From the brief, decide the ordered list: purpose + channel
   + timing + the *distinct angle* of each step. A classic cold sequence:
   - 1 · `outreach-email` — the opener (the core hook + ask)
   - 2 · `followup-email` — a new angle / piece of value (not a reminder)
   - 3 · `followup-email` — the break-up (permission to close the loop)

   Show the plan and confirm before composing.

2. **Compose each step** as its own session, in order, via `message-intake` +
   `compose`:
   ```bash
   message new --brand <brand> --name <campaign>-step1-outreach-email --format outreach-email
   message new --brand <brand> --name <campaign>-step2-followup-email  --format followup-email
   ```
   Keep a through-line: each step references the prior touch without repeating it,
   and every step adds something new.

3. **Lint, render, and QA each step** as usual (`compose` covers this per step).

4. **Report** the sequence: the steps, their session paths, the cadence, and the
   single CTA each step drives toward.

## Conventions

- Each step is its own session/format — never multiple steps in one session.
- No step is "just following up." Every touch earns its place with a new angle.
- Keep the ask consistent across the sequence; vary the reason to act, not the goal.
