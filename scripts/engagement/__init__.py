"""engagement — the engagement-level manifest for the studios root plugin.

Deterministic glue for the **`engagement.json`** manifest the Producer
maintains as it sequences jobs across the cast. The engagement manifest
is the engagement-level analogue of the planner's `composition.json` —
it lives at the docket root and records:

- `brief` — objectives, audience/client, constraints, success criteria
- `cast[]` — the chosen roles + a one-line justification each
- `jobs[]` — `{id, capability, role, status, inputs, outputs, checkpoint?}`
- `questions[]` / `blockers[]` / `risks[]` — first-class open items
  (Bible §8 shape: id, kind, raised_by_role, raised_at, needs, status, …)
- `decisions[]` — pointers to ADR-style decision records
- `checkpoints[]` — pending / cleared L2 / L3 gates (Bible §6)
- `rollup` — derived status summary (recomputed on every mutation)

LLM-driven judgment — which cast to pick, which jobs to spawn, which
question to escalate, when to clear a checkpoint — lives in
``skills/engagement/SKILL.md``. This package handles only mechanics:
file ops, schema validation, id allocation, status transitions, and
the deterministic rollup.

No judgment lives here. CLI subcommands mirror the skill.
"""

from __future__ import annotations

from pathlib import Path

__version__ = "0.1.0"

PACKAGE_ROOT = Path(__file__).resolve().parent
SCHEMAS = PACKAGE_ROOT / "schemas"
