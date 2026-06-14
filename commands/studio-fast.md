---
description: Fast single-studio path — skip Principal shaping for well-specified draft work. Usage: /studio --fast design "render this markdown as pitch-pdf for brand acme". Outward delivery (L3) still requires explicit confirmation; format contracts still enforced.
---

You are invoked in **fast mode**: a well-specified, single-studio job that does
not need Principal shaping or multi-studio planning.

Treat `$ARGUMENTS` as: `<studio-slug> <brief>` (e.g. `design render acme pitch-pdf
from ~/briefs/pitch.md`).

## Rules

1. **Skip Principal shaping** — do not re-run objective/scope/cast confirmation
   for draft/internal work.
2. **Invoke the Producer in fast mode** — invoke the **`producer`** skill with an
   explicit note: `mode=fast`, `studio=<slug>`, `brief=<text>`. The Producer
   routes one job to that studio only; skips step-3 plan confirmation and
   non-essential review gates for drafts.
3. **Keep fail-closed format validation** — the studio's locked format contract,
   lint, and render rules still apply.
4. **L3 is never skipped** — publishing, posting, or emailing still requires
   explicit user confirmation.

If the request spans multiple studios, is outward-facing, or needs scope shaping,
tell the user to use `/studio` without `--fast`.
