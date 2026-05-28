# Sequence template: cold-outreach-3step

A classic cold outreach cadence: open, add value, close the loop. The `sequence`
skill uses this to set the steps, formats, and cadence, then composes each step.
Maps directly to:

```
message sequence new --brand <slug> --name <campaign> \
  --step cold:outreach-email \
  --step value:followup-email \
  --step breakup:followup-email
```

## Steps

| # | Step | Format | Send (relative) | Intent | Suggested CTA slug |
|---|------|--------|-----------------|--------|--------------------|
| 1 | `cold` | `outreach-email` | day 0 | Earn the reply: relevance + one specific ask | `worth-a-look` / `yes-no` |
| 2 | `value` | `followup-email` | day +3 | Add something new (proof, insight) — never just "bumping" | `send-detail` / `15-min` |
| 3 | `breakup` | `followup-email` | day +7 | Close the loop gracefully; leave the door open | `close-loop` |

## Rules of the cadence

- **Each step must stand alone** — assume they never read the prior one.
- **Step 2 adds value**, it doesn't nag. New angle, proof point, or resource.
- **Step 3 is short** and removes pressure; break-ups often get the most replies.
- Thread steps 2–3 with `Re: {step 1 subject}` (see `subject-lines/` → `reply-thread`).
- Honour the per-format ruleset on every step (subject/body/links/one-CTA).

> Add sequence templates by copying this file. Vary step count, formats, and
> cadence; keep the per-step *intent* column — it's what the skill composes against.
