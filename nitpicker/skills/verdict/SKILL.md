---
name: verdict
description: Consolidate every dimension and test score into review/v<ver>/scores.yml, write the narrative findings.md, and run `nit score` to compute the weighted aggregate + verdict (scorecard.json). The final step of a nitpicker review. Use after the critique and apply-tests skills.
---

# verdict

Pull the whole review together: the dimension scores (visual-qa, brief-fulfilment,
audience-fit, tone-of-voice) and the test scores (so-what / yawn / sniff / …) into
one scored verdict plus an actionable write-up.

## Steps

1. **Assemble `review/v<ver>/scores.yml`** from every prior skill's score
   (`<ver>` = the captured version, the session's `current`):
   ```yaml
   dimensions:
     visual-qa: { score: 4, note: "…" }
     brief-fulfilment: { score: 3, note: "…" }
     audience-fit: { score: 4, note: "…" }
     tone-of-voice: { score: 4, note: "…" }
   tests:
     the-so-what-test: { score: 4, note: "…" }
     the-yawn-test: { score: 3, note: "…" }
     the-sniff-test: { score: 5, note: "…" }
   ```
   Include every dimension and every test that was scored. Omit a test only if it
   genuinely didn't apply (note that in `findings.md`).

2. **Compute the verdict:**
   ```bash
   nit score --session <path>          # reads scores.yml, writes scorecard.json
   ```
   This normalises and weights each item per `../configs/default/review-policy.yml`,
   enforces **gate** items (e.g. the sniff test, brief-fulfilment — a hard miss on
   a gate forces `fail`), and prints `pass | revise | fail` with the overall
   score. Don't hand-compute the verdict — let `nit score` be the single source
   of the number.

3. **Write `review/v<ver>/findings.md`** — the narrative the scorecard summarises:
   ```markdown
   # Nitpicker review — <session> · v<version>

   **Verdict:** <pass | revise | fail>   **Overall:** <NN>/100
   <gate failures, if any>

   ## Scorecard
   | Item | Score | Status |
   |------|-------|--------|
   | brief-fulfilment | 3/5 | warn |
   | … | | |

   ## Critical (must fix)
   - <finding> — <where> — <suggested fix>

   ## Significant / Minor
   - …

   ## What's working
   - …
   ```
   Order findings by severity, each tied to the dimension/test that raised it and
   carrying a concrete fix.

4. **Report back:** the verdict, the overall score, any gate failures, the
   critical-finding count, and the paths to `findings.md` + `scorecard.json`.
   If `revise`/`fail`: summarise the top fixes. If the asset came from another
   studio, offer to route those fixes back (design → re-render, messaging →
   re-compose) for a re-review (`nit capture --bump` → re-score) — the nitpicker
   itself never edits the asset.

## Constraints

- `nit score` owns the verdict math; your job is honest, complete scores and a
  clear write-up. Don't override the computed verdict — if it feels wrong, the
  scores or the policy are wrong, so fix those.
- Every critical/significant finding must be specific and carry a fix. "Feels
  off" is not a finding.
- Don't pad the write-up. A clean asset gets a short, confident `pass`.
