#!/usr/bin/env python3
"""autonomy ladder enforcement (#93) — L0-L3 action classes + checkpoint
surfacing per Bible §6.

Standalone; run any venv with pyyaml + jsonschema:
  nitpicker/.venv/bin/python tests/test_autonomy.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from engagement import autonomy, checkpoints as cp_mod, jobs as jobs_mod  # noqa: E402
from engagement import manifest as man  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


def raises(fn, exc=Exception) -> bool:
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    man.new(root, engagement_slug="demo", objective="Test the autonomy ladder")

    # 1. action_class accepted; defaults to L1
    j_default = jobs_mod.add(root, capability="render-asset", role="design")
    check("default action_class L1", j_default["action_class"] == "L1")

    # 2. L0/L1 jobs complete freely
    jobs_mod.set_status(root, job_id=j_default["id"], status="in-progress")
    jobs_mod.set_status(root, job_id=j_default["id"], status="done")
    check("L1 → done free", True)

    j_gather = jobs_mod.add(
        root, capability="ingest-context", role="context", action_class="L0"
    )
    jobs_mod.set_status(root, job_id=j_gather["id"], status="done")
    check("L0 → done free", True)

    # 3. invalid action_class rejected
    check(
        "add rejects invalid action_class",
        raises(
            lambda: jobs_mod.add(root, capability="x", action_class="bogus"),
            ValueError,
        ),
    )

    # 4. L2 job blocked without cleared checkpoint
    j_l2 = jobs_mod.add(
        root,
        capability="assess-commercial-value",
        role="commercial",
        action_class="L2",
        title="Value-based scoping",
    )
    jobs_mod.set_status(root, job_id=j_l2["id"], status="in-progress")
    check(
        "L2 → done without CP raises AutonomyError",
        raises(
            lambda: jobs_mod.set_status(root, job_id=j_l2["id"], status="done"),
            autonomy.AutonomyError,
        ),
    )

    # The error carries the rule + job id
    try:
        jobs_mod.set_status(root, job_id=j_l2["id"], status="done")
    except autonomy.AutonomyError as e:
        check("AutonomyError carries rule", e.rule == "l2-checkpoint-required")
        check("AutonomyError carries job_id", e.job_id == j_l2["id"])

    # Open a CP that's not yet cleared — still blocked
    cp_pending = cp_mod.open_checkpoint(
        root,
        level="L2",
        title="Confirm scope + price",
        blocking_jobs=[j_l2["id"]],
    )
    check("CP opened", cp_pending["status"] == "pending")
    check(
        "L2 → done while CP pending still blocked",
        raises(
            lambda: jobs_mod.set_status(root, job_id=j_l2["id"], status="done"),
            autonomy.AutonomyError,
        ),
    )

    # CP cleared but missing decided_by — for L2 that's fine
    cp_mod.clear(root, checkpoint_id=cp_pending["id"], outcome="Approved at £150k")
    j = jobs_mod.set_status(root, job_id=j_l2["id"], status="done")
    check("L2 → done after CP cleared works", j["status"] == "done")

    # 5. L3 job — requires CP cleared + decided_by
    j_l3 = jobs_mod.add(
        root,
        capability="compose-message",
        role="messaging",
        action_class="L3",
        title="Email proposal to user",
    )
    jobs_mod.set_status(root, job_id=j_l3["id"], status="in-progress")
    check(
        "L3 → done without CP raises AutonomyError",
        raises(
            lambda: jobs_mod.set_status(root, job_id=j_l3["id"], status="done"),
            autonomy.AutonomyError,
        ),
    )

    cp_l3 = cp_mod.open_checkpoint(
        root, level="L3", title="Send the proposal", blocking_jobs=[j_l3["id"]]
    )

    # Clear without decided_by — L3 still blocked
    cp_mod.clear(root, checkpoint_id=cp_l3["id"], outcome="Sent")
    try:
        jobs_mod.set_status(root, job_id=j_l3["id"], status="done")
        check("L3 → done with CP missing decided_by should raise", False)
    except autonomy.AutonomyError as e:
        check(
            "L3 needs decided_by — rule is l3-human-authorisation-required",
            e.rule == "l3-human-authorisation-required",
        )

    # Re-clear with decided_by — now allowed
    cp_mod.clear(
        root,
        checkpoint_id=cp_l3["id"],
        outcome="Sent on user authority",
        decided_by="user",
    )
    j = jobs_mod.set_status(root, job_id=j_l3["id"], status="done")
    check("L3 → done after CP cleared with decided_by works", j["status"] == "done")

    # 6. non-`done` transitions are always free (even for L2/L3)
    j_l2b = jobs_mod.add(
        root,
        capability="plan-delivery",
        role="delivery",
        action_class="L2",
    )
    # planned → in-progress → blocked → in-progress: all free
    jobs_mod.set_status(root, job_id=j_l2b["id"], status="in-progress")
    jobs_mod.set_status(root, job_id=j_l2b["id"], status="blocked")
    jobs_mod.set_status(root, job_id=j_l2b["id"], status="in-progress")
    check("L2 non-`done` transitions free", True)

    # 7. autonomy_state + rollup_counts reflect the contract
    state = autonomy.autonomy_state(man.read(root))
    by_id = {r["id"]: r for r in state}
    check(
        "autonomy_state j_l2b is L2 + blocked",
        by_id[j_l2b["id"]]["action_class"] == "L2",
    )
    check(
        "autonomy_state j_l2b cannot complete (no CP)",
        not by_id[j_l2b["id"]]["can_complete"]
        and any("cleared CP" in m for m in by_id[j_l2b["id"]]["blocked_by"]),
    )
    check(
        "autonomy_state j_l3 done shows can_complete=False (already done)",
        not by_id[j_l3["id"]]["can_complete"],
    )

    counts = autonomy.rollup_counts(man.read(root))
    check("rollup_counts awaiting_l2 = 1", counts["awaiting_l2"] == 1)
    check("rollup_counts awaiting_l3 = 0", counts["awaiting_l3"] == 0)
    check("rollup_counts by_action_class L0 = 1", counts["by_action_class"]["L0"] == 1)
    check("rollup_counts by_action_class L1 = 1", counts["by_action_class"]["L1"] == 1)
    check("rollup_counts by_action_class L2 = 2", counts["by_action_class"]["L2"] == 2)
    check("rollup_counts by_action_class L3 = 1", counts["by_action_class"]["L3"] == 1)

    # 8. manifest rollup grows with autonomy counts
    data = man.read(root)
    check("manifest rollup has awaiting_l2", "awaiting_l2" in data["rollup"])
    check("manifest rollup has awaiting_l3", "awaiting_l3" in data["rollup"])
    check(
        "manifest rollup awaiting_l2 = 1",
        data["rollup"]["awaiting_l2"] == 1,
        f"got {data['rollup']['awaiting_l2']}",
    )
    check(
        "manifest rollup jobs_by_action_class L2 = 2",
        data["rollup"]["jobs_by_action_class"]["L2"] == 2,
    )

    # 9. schema validates action_class enum
    bad = man.read(root)
    bad["jobs"][0]["action_class"] = "L9"
    check(
        "schema rejects invalid action_class",
        raises(lambda: man.write(root, bad), ValueError),
    )

if failures:
    print("FAIL:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(
    "PASS: autonomy ladder (L0/L1 free; L2 needs cleared CP; L3 needs cleared CP + decided_by; non-`done` transitions free; rollup counts; schema)"
)
