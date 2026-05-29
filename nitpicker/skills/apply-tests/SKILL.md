---
name: apply-tests
description: Run the asset's content through the configurable, extensible scored test battery in configs/tests/ (the-so-what-test, the-yawn-test, the-sniff-test, …). Scores each test against its criteria and scale and records the scores. Use after the critique skills, before verdict.
---

# apply-tests

Score the asset through every test in the battery. Each test is a self-describing
YAML scoring mechanism — you apply its scale and criteria; `nit score` (run by
`verdict`) aggregates the weighted result. New tests are picked up automatically.

## Steps

1. **Enumerate the battery:**
   ```bash
   nit tests list                       # all tests with their question + weight
   nit tests show --test <slug>         # full definition of one
   ```

2. **For each test**, read its definition and score the asset against it:
   - Read the test's `question`, `scale` (with its labelled anchors), and the
     `criteria` the score is judged against.
   - Apply it to the relevant content (`applies_to`: text, visual, or both).
   - Pick the integer score on the test's scale whose anchor label best matches
     the asset. Be honest and consistent — calibrate to the labels, not to a
     gut "feels like a 4".
   - Capture a one-line justification citing the specific evidence, and (if below
     the test's `threshold.pass`) the concrete fix that would raise it.

   The shipped tests:
   - **the-so-what-test** — relevant, exciting, impactful? Will it change the
     reader's mind? (criteria: relevance to the ICP, concrete payoff, stakes,
     memorability, a real shift.)
   - **the-yawn-test** — interesting, readable, engaging? (opening earns
     attention, momentum, effortless to read, varied rhythm, no filler.)
   - **the-sniff-test** — credible, authoritative, believable? **(a gate)**
     (claims specific + substantiated, no hype outrunning evidence, authoritative
     not arrogant, internally consistent, honest about limits.)

3. **Record the scores.** Add each test's score (and note) under `tests:` in the
   review's `scores.yml` (the `verdict` skill assembles this file). Shape:
   ```yaml
   tests:
     the-so-what-test: { score: 4, note: "specific ROI payoff but soft stakes" }
     the-yawn-test: { score: 3, note: "strong open, sags in the middle third" }
     the-sniff-test: { score: 5, note: "named customers + hard numbers" }
   ```

## Constraints

- Score against each test's own criteria and scale — don't import a different
  bar. If a test doesn't apply to this asset type (`applies_to`), skip it and say
  why rather than forcing a score.
- The battery is extensible: if the user has added a test, score it too — never
  hard-code to only the three shipped tests.
- Don't double-penalise: a weak hook is a yawn-test finding; don't also re-litigate
  it as a so-what failure unless it genuinely fails both.
