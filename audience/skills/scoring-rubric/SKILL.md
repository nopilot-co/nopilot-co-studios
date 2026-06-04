---
name: scoring-rubric
description: Derive a weighted scoring rubric from the reader's need-state — one scored test per need, weighted by priority, with critical needs as gates — expressed in the nitpicker test-definition format so the critique scores against the shared nitpicker engine. Drafts via `audience rubric derive`; you fill the criteria. Use after psychographic-profile, before audience-critique.
---

# scoring-rubric

Turn the reader's needs into a **measuring instrument**: a weighted rubric the
critique scores work against. The mechanism is derived from the need-state so the
score reflects *this reader's* priorities — not generic quality. The rubric is in
the nitpicker's test format, so scoring reuses the nitpicker engine (no separate
math, same review policy).

## Steps

1. **Derive the draft:**
   ```bash
   audience rubric derive --audience <slug>
   ```
   This writes `rubric.yml` with one test per real need, weight by priority
   (critical 2.0 + gate, high 1.5, medium 1.0, low 0.5), `dimension: reader-fit`,
   and a stubbed `criteria` for each.

2. **Fill the criteria (your judgment).** For each test, replace the stub with the
   **concrete signals this reader uses to judge that need is met** — drawn from
   their `decision_factors`, `preferred_evidence`, and `objections`. Sharpen the
   `question` to the reader's voice. Good criteria are observable in the artifact
   ("shows proof at comparable scale, with numbers"), not vague ("is convincing").

3. **Tune weights + gates if needed.** The priority→weight mapping is a sensible
   default; adjust a `weight` or add/remove a gate only with a reason. A gate means
   "fail the work outright if this need is badly unmet" — reserve for the reader's
   true must-haves.

4. **Set the scale anchors (optional).** Add `scale.labels` (1..5) where naming the
   anchors helps the critique score consistently.

5. **Validate:**
   ```bash
   audience rubric validate --audience <slug>
   ```
   This rejects unfilled stubs, bad weights, and gates that aren't real tests. Fix
   any errors before critiquing.

6. Hand the slug to `audience-critique` to score real work against this rubric.

## Conventions

- One test per need; the rubric **is** the need-state made measurable. Don't add
  tests for things the reader doesn't need.
- Criteria must be concrete and reader-specific — the critique scores against them,
  so vagueness produces a meaningless number.
- The rubric uses the nitpicker test shape on purpose: `audience review score`
  feeds it to `nit aggregate`, so the verdict math + policy are single-sourced.
