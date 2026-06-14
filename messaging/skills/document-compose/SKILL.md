---
name: document-compose
description: Author multi-section long-form documents (propositions, whitepapers, reports) from planner section briefs into per-section Markdown files in a production docket, in brand voice with citation tracking. Use when the planner has scaffolded sections and needs section content written — not for single-channel emails (use compose). Hand off assembled source to design render-asset.
---

# document-compose

Write **section content** for a composite document the planner scaffolded. Unlike
`compose` (single-channel, ≤200 words, one CTA), this skill authors **multiple
sections** with varied structure, multiple CTAs where appropriate, and explicit
source/citation notes — then the planner assembles and design renders.

## When to use

- A planner docket exists with `sections/<id>/brief.md` (or equivalent) but empty
  or stub `sections/<id>/content.md`.
- The brief asks for a proposition, prospectus, proposal, report, or whitepaper —
  not a single email/post.

## Steps

1. **Read the planner scaffold.** Inspect the docket root:
   - `production-manifest.json` / session manifest for the locked design format.
   - `sections/` — each section's `brief.md` (what this section must achieve).
   - Optional `inputs/brief.md` and audience reader slug (from planner `--audience`).

2. **Load voice + reader context.**
   - Brand voice: `~/context/studios/brand/<slug>/tone-of-voice.md` (or default).
   - If a reader slug is bound, read `~/context/studios/audience/<slug>/profile.md`
     (or the docket's audience artefact) and thread the need-state through each section.

3. **Author each section.** For every section in planner order, write
   `sections/<id>/content.md`:
   ```markdown
   ---
   section: executive-summary
   status: draft
   sources:
     - ref: inputs/research.md
       note: market sizing paragraph
   ---

   ## Executive summary

   <section body — structure varies per brief; not limited to email shape>

   <!-- optional inline CTA for this section -->
   ```
   - Match the section brief's required elements (from planner + format contract).
   - Track citations in front-matter `sources` (path + note) — no invented facts.
   - Vary structure section-to-section; avoid repeating the same paragraph shape.

4. **Lint voice mechanically** where possible:
   ```bash
   message lint --session <path>   # if section maps to a messaging session
   ```
   For docket sections, run forbidden-phrase checks against brand voice manually
   or via nitpicker tone-of-voice after assembly.

5. **Hand off to planner assemble**, then design:
   ```bash
   planner assemble --root <docket> --session <name>
   # → <session>/inputs/source.md
   studio session init --brand <slug> --name <name> --format <fmt> --source ...
   studio render --session <path>
   ```

6. Report section paths written and the assemble/render handoff command.

## Conventions

- One section file per planner section — never one monolithic draft outside `sections/`.
- Brand voice is mandatory; reader model is mandatory when `--audience` was used.
- Judgment lives here; planner assemble + studio render are deterministic glue.
- Do not hand-draft `source.md` directly — always write sections, then assemble.
