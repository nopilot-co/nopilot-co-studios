---
name: tone-of-voice
description: Rigorously apply the standardised tone-of-voice principles (configs/default/tone-of-voice.yml), overlaid by the brand's own voice if one applies. Judges the asset's copy against the ToV attributes, do/don't, forbidden phrases, preferred constructions, and mechanics. Writes the tone-of-voice section of the review. Use after review-intake.
---

# tone-of-voice

Hold the asset's copy to the **standardised tone-of-voice baseline**, rigorously
and consistently. Score 1–5 for the `tone-of-voice` dimension.

## Steps

1. **Load the standard.** The baseline is brand-agnostic and always applies:
   ```bash
   nit config show --brand <slug>     # shows baselines + any brand voice overlay
   ```
   - **Baseline:** `../configs/default/tone-of-voice.yml` — `attributes`,
     `principles`, `mechanics`, `do`, `dont`, `forbidden`, `preferred`.
   - **Brand overlay** (if a brand): its `tone-of-voice.md` in the brand store
     *specialises* the baseline. It can tighten or add; it does not relax the
     baseline. Where they conflict, the brand wins on character, the baseline
     wins on craft (clarity, no hype, no forbidden phrases).

2. **Read the copy** (source `.md` and/or the captured/rendered text) and judge,
   point by point:

   **Attributes** — does the writing actually project the named character
   (clear, confident, human, specific, …)? Quote lines that do and that don't.

   **Principles** — clarity over cleverness; leads with the reader; shows rather
   than asserts; one idea per unit; no warm-up. Flag each violation with the line.

   **Mechanics** — active voice, right person/tense, varied sentence length,
   minimal hedging.

   **Forbidden phrases** — flag every occurrence of a `forbidden` term (these are
   hard fails on sight). List each with its location.

   **Preferred constructions** — flag where a `preferred.use` should replace an
   `instead` term.

3. **Be rigorous and consistent.** Apply the same bar everywhere; don't let a
   strong piece off on a forbidden phrase, and don't nitpick a weak one into the
   ground on mechanics. Every flag cites the exact line and the rule it breaks.

4. **Score and record.** Assign the 1–5 (5 = on-voice throughout, zero forbidden
   phrases, clean mechanics; drop hard for forbidden phrases or pervasive
   off-voice copy). Write findings — each as `"<quoted line>" — <rule> — <fix>` —
   into the review notes the `verdict` skill consolidates.

## Constraints

- The baseline is the floor; a brand voice never excuses a forbidden phrase or
  hype that fails the principles.
- Quote, don't paraphrase — a ToV finding without the offending line isn't
  actionable.
- Voice mechanics are yours; *what* the copy says for the audience is
  `audience-fit`'s; whether it's credible is the sniff test's. Coordinate, don't
  triple-count.
