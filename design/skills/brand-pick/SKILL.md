---
name: brand-pick
description: List available brands in ~/context/studios/design/ and let the user pick one for the current session. Sets the brand context for subsequent render and qa skills. Use at the start of any design-studio workflow.
---

# brand-pick

Sets the active brand for the session.

## Steps

1. Run:
   ```bash
   studio brand list
   ```
   Output is one line per brand: `<slug>  <primary-color>  <font-family>  (last-rendered: <date>)`.

2. If the user has not already named a brand:
   - If 0 brands exist, say so and offer to invoke `brand-ingest` to create one.
   - If 1 brand exists, confirm it as the default (don't ask).
   - If 2+ brands exist, present them via AskUserQuestion as options.

3. Once chosen, store the slug in the session's `version.json` (created by `session-init`) and pass it to all subsequent skills as `--brand <slug>`.

Brand selection is independent of **format**: brands are format-agnostic. The
format slug (`pitch-pdf`, `proposal-html`, …) is chosen and locked separately at
`session-init`. Picking the brand here does not pick the format.

## Pushback

- If the user names a brand that doesn't exist, list available brands instead of trying to guess. Suggest `brand-ingest` to create it.
