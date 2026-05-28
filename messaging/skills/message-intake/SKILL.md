---
name: message-intake
description: Start a messaging session — choose the communication format (purpose × channel, e.g. outreach-email) and lock it in. Use before compose. Creates the session and version.json via `message new`.
---

# message-intake

Set up a messaging session and **lock in the format** it will produce. A session
is one brand × one format slug × one message.

## Steps

1. **Pick the format.** Every session targets one `<purpose>-<channel>` slug.
   List options:
   ```bash
   message formats list
   ```
   - Map the brief to a purpose (outreach, followup, announcement, nurture) and a
     channel (email, linkedin-post, slack-post, sms). "Cold email to a prospect"
     → `outreach-email`.
   - If the user wants the same message on two channels, that's **two sessions**.
   - Read the contract you're committing to:
     ```bash
     message formats show --format <slug>
     ```

2. **Name the session** (kebab-case; include the format, e.g. `acme-q3-outreach-email`).

3. **Create it:**
   ```bash
   message new --brand <brand> --name <session-name> --format <slug>
   ```
   This validates the format, scaffolds `inputs/message.md` (front-matter +
   section stubs), writes `version.json` (with the locked `format` and `channel`),
   and prints the brand voice file in effect.

4. Hand the session path to `compose`. Later skills read the locked format from
   `version.json` — never re-pick it.

## Conventions

- One brand × one format per session; the format is immutable once created.
- The brand supplies the voice (shared from the design studio); intake does not
  choose voice separately.
