---
name: compose
description: Write a brand communication (email, post, announcement, etc.) into a messaging session's inputs/message.md, in the brand's voice and to the locked format's brief. Use after message-intake. Supersedes the older outreach-copy skill.
---

# compose

Write the message for a session, in the brand's voice, to the locked format's
execution brief. The Python CLI handles structure, linting, and rendering; you
handle the words.

## Steps

1. **Read the contract and the voice.**
   ```bash
   message formats show --format <slug>   # slug = version.json "format"
   ```
   Note `execution_brief.required_sections`, `style_guide`, and the `ruleset`
   limits (subject length, body budget, link/CTA caps, forbidden phrases). Read
   the brand voice file printed by `message new` (the brand's `tone-of-voice.md`,
   else the default) and obey its forbidden/preferred lists.

2. **Write `inputs/message.md`.** Fill the front-matter and replace the
   `<!-- section -->` stubs with real copy:
   ```markdown
   ---
   subject: "A subject under the char limit"   # only if the channel requires one
   preview: "One-line preview / first line"
   channel: email
   status: draft
   ---

   <hook / opening that leads with the reader's stake>

   <body — one idea, within the word budget>

   <a single, clear CTA>
   ```
   Stay within the ruleset as you write — don't rely on lint to catch overflow.

3. **Lint** (deterministic enforcement):
   ```bash
   message lint --session <path>
   ```
   Fix any violations (subject too long, body over budget, too many links,
   forbidden phrases) and re-lint until clean.

4. **Render** the channel target(s):
   ```bash
   message render --session <path> --bump patch
   ```
   Outputs land in `outputs/<slug>.v<version>.<ext>`. Render re-checks the ruleset
   and fails if violated.

5. Hand off to `message-qa` for the qualitative pass, then report the paths.

## Conventions

- One idea, one ask. Lead with the recipient's stake.
- Specific over generic; cut every word the message survives without.
- Never invent a brand voice — if none exists, say so and use the default.
