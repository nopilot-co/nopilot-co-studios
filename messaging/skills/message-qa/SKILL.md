---
name: message-qa
description: Quality pass over a composed/rendered message. Judges it against the format contract (required sections, CTA, voice) and deliverability, beyond the deterministic checks `message lint` already enforces. Writes review/v<version>/findings.md. Use after compose.
---

# message-qa

Critique a message against its contract and brand voice. Deterministic limits are
already enforced by `message lint`/`render`; you judge the qualitative rules.

## Steps

1. Identify the version (default: `current` in `version.json`) and read the
   rendered output in `outputs/` plus `inputs/message.md`.

2. Load both contracts:
   ```bash
   message formats show --format <slug>   # slug = version.json "format"
   ```
   and the brand voice file (the brand's `tone-of-voice.md`, else the default).

3. Critique against the **rubric**:

   **Contract fidelity**
   - Are all `execution_brief.required_sections` present and doing their job?
   - `must_include_cta` honored, and is there exactly one clear CTA (`one_cta`)?
   - Does it read as the intended purpose (outreach earns a reply; announcement
     leads with the news; nurture gives before it asks) on the intended channel?

   **Voice**
   - Adheres to the brand's tone attributes; no forbidden words/phrases; matches
     the preferred constructions.

   **Deliverability & craft**
   - Subject earns the open (specific, not spammy); first line / preview works.
   - No spam triggers (ALL CAPS, "act now", excessive punctuation).
   - Skimmable; the ask is effortless to act on.

4. Write `review/v<version>/findings.md`:
   ```markdown
   # Message QA — <brand> · <format-slug> · v<version>

   **Verdict:** <pass | revise | fail>

   ## Critical (must fix)
   - <finding> — <suggested fix>

   ## Significant / Minor
   - ...

   ## What's working
   - ...
   ```

5. Report the verdict + critical count + path. If `revise`/`fail`, offer to
   rewrite and re-render.

## Constraints

- Don't re-flag what `lint` already covers (counts/limits) unless it's still
  wrong. Focus on judgment: voice, CTA strength, purpose fit, deliverability.
- Don't invent findings. If it's clean, say so.
