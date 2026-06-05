#!/usr/bin/env python3
"""engagement manifest (#91) — engagement.json + jobs + items + decisions +
checkpoints + rollup invariants.

Standalone; run any venv with pyyaml + jsonschema:
  nitpicker/.venv/bin/python tests/test_engagement.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from engagement import (  # noqa: E402
    checkpoints as cp_mod,
    decisions as dec_mod,
    items as items_mod,
    jobs as jobs_mod,
    manifest as man,
)

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

    # 1. scaffold
    data = man.new(
        root, engagement_slug="demo", objective="Win the pitch", audience="vp-eng"
    )
    check("engagement.json created", man.exists(root))
    check("schema_version stamped", data["schema_version"] == "1.0")
    check("status starts draft", data["status"] == "draft")
    check("brief populated", data["brief"]["objective"] == "Win the pitch")
    check("rollup initial jobs_total = 0", data["rollup"]["jobs_total"] == 0)
    check("rollup initial open_questions = 0", data["rollup"]["open_questions"] == 0)
    check(
        "new refuses to overwrite",
        raises(lambda: man.new(root, engagement_slug="demo"), ValueError),
    )

    # 2. brief update
    data = man.set_brief(
        root, constraints=["deadline 2026-08-30"], success_criteria=["L2 sign-off"]
    )
    check(
        "brief constraints set", data["brief"]["constraints"] == ["deadline 2026-08-30"]
    )
    check(
        "brief success_criteria set",
        data["brief"]["success_criteria"] == ["L2 sign-off"],
    )

    # 3. cast
    man.add_cast(root, role="design", justification="renderer for the proposition")
    man.add_cast(root, role="commercial", justification="rate-card + value sizing")
    data = man.read(root)
    check("2 cast roles", len(data["cast"]) == 2)
    check(
        "cast rejects duplicate role",
        raises(lambda: man.add_cast(root, role="design"), ValueError),
    )

    # 4. jobs — id allocation + status transitions + rollup
    j1 = jobs_mod.add(root, capability="render-asset", role="design", title="deck v1")
    j2 = jobs_mod.add(root, capability="check-commercials", role="commercial")
    j3 = jobs_mod.add(root, capability="render-asset", role="design", title="deck v2")
    check(
        "job ids increment J-001..003",
        j1["id"] == "J-001" and j2["id"] == "J-002" and j3["id"] == "J-003",
    )
    check("job initial status planned", j1["status"] == "planned")
    jobs_mod.set_status(root, job_id="J-001", status="in-progress")
    jobs_mod.set_status(root, job_id="J-002", status="done")
    data = man.read(root)
    check("rollup: jobs_total = 3", data["rollup"]["jobs_total"] == 3)
    check(
        "rollup: jobs_by_status counts",
        data["rollup"]["jobs_by_status"]["in-progress"] == 1
        and data["rollup"]["jobs_by_status"]["done"] == 1
        and data["rollup"]["jobs_by_status"]["planned"] == 1,
    )
    check(
        "rollup: percent_complete = 33.3",
        data["rollup"]["percent_complete"] == round(100 * 1 / 3, 1),
    )
    check(
        "job set_status rejects bogus",
        raises(
            lambda: jobs_mod.set_status(root, job_id="J-001", status="bogus"),
            ValueError,
        ),
    )
    check(
        "job set_status rejects unknown id",
        raises(
            lambda: jobs_mod.set_status(root, job_id="J-999", status="done"),
            KeyError,
        ),
    )
    check(
        "list jobs filtered by status",
        len(jobs_mod.list_jobs(root, status="planned")) == 1,
    )

    # 5. first-class items: Q / B / R
    q1 = items_mod.add(
        root,
        kind="question",
        title="Pitch deck or brochure?",
        raised_by_role="principal",
        needs="user",
        blocking_jobs=["J-001"],
    )
    b1 = items_mod.add(root, kind="blocker", title="Brand assets missing")
    r1 = items_mod.add(root, kind="risk", title="Scope creep on phase 2")
    check("Q-001 allocated", q1["id"] == "Q-001")
    check("B-001 allocated", b1["id"] == "B-001")
    check("R-001 allocated", r1["id"] == "R-001")
    check("question carries needs=user", q1["needs"] == "user")
    check("question carries blocking_jobs", q1["blocking_jobs"] == ["J-001"])
    data = man.read(root)
    check(
        "rollup: open items counted",
        data["rollup"]["open_questions"] == 1
        and data["rollup"]["open_blockers"] == 1
        and data["rollup"]["open_risks"] == 1,
    )

    # add a second risk → R-002
    r2 = items_mod.add(root, kind="risk", title="Vendor outage")
    check("R-002 allocated", r2["id"] == "R-002")

    # resolve a question
    resolved = items_mod.resolve(
        root,
        kind="question",
        item_id="Q-001",
        resolution="Pitch deck",
    )
    check("Q-001 resolved", resolved["status"] == "resolved")
    check("Q-001 resolution recorded", resolved["resolution"] == "Pitch deck")
    data = man.read(root)
    check(
        "rollup: open_questions drops to 0 after resolve",
        data["rollup"]["open_questions"] == 0,
    )

    check(
        "items add invalid kind raises",
        raises(
            lambda: items_mod.add(root, kind="bogus", title="x"),
            ValueError,
        ),
    )
    check(
        "items add invalid needs raises",
        raises(
            lambda: items_mod.add(root, kind="question", title="x", needs="ghost"),
            ValueError,
        ),
    )
    check(
        "items resolve unknown raises",
        raises(
            lambda: items_mod.resolve(
                root, kind="question", item_id="Q-999", resolution="x"
            ),
            KeyError,
        ),
    )

    # show filter
    open_items = items_mod.show(root, status="open")
    check("show filtered by status open = 3", len(open_items) == 3)
    risks = items_mod.show(root, kind="risk")
    check("show filtered by kind risk = 2", len(risks) == 2)

    # 6. decisions
    d1 = dec_mod.add(
        root,
        title="value-based price band £75k-£250k",
        role="commercial",
        ref="clients/acme/assessment.yml",
        summary="commercial officer's sizing",
    )
    check("D-001 allocated", d1["id"] == "D-001")
    d2 = dec_mod.add(root, title="Pitch deck not brochure")
    check("D-002 allocated", d2["id"] == "D-002")
    check("decisions show 2", len(dec_mod.show(root)) == 2)

    # 7. checkpoints
    cp1 = cp_mod.open_checkpoint(
        root,
        level="L2",
        title="Confirm scope + investment band",
        raised_by_role="principal",
        blocking_jobs=["J-001"],
        evidence="clients/acme/assessment.yml",
    )
    cp2 = cp_mod.open_checkpoint(
        root, level="L3", title="Email proposal to user", raised_by_role="producer"
    )
    check("CP-001 allocated", cp1["id"] == "CP-001")
    check("CP-002 allocated", cp2["id"] == "CP-002")
    check("checkpoint level recorded", cp1["level"] == "L2")
    data = man.read(root)
    check("rollup: pending_checkpoints = 2", data["rollup"]["pending_checkpoints"] == 2)
    check(
        "rollup: next_checkpoint is the first pending",
        data["rollup"]["next_checkpoint"]["id"] == "CP-001",
    )

    cp_mod.clear(
        root,
        checkpoint_id="CP-001",
        outcome="Approved at £150k",
        decided_by="user",
    )
    data = man.read(root)
    check(
        "rollup: pending_checkpoints drops to 1 after clear",
        data["rollup"]["pending_checkpoints"] == 1,
    )
    check(
        "rollup: next_checkpoint becomes CP-002",
        data["rollup"]["next_checkpoint"]["id"] == "CP-002",
    )

    check(
        "checkpoint invalid level raises",
        raises(
            lambda: cp_mod.open_checkpoint(root, level="L1", title="x"),
            ValueError,
        ),
    )
    check(
        "checkpoint clear unknown raises",
        raises(
            lambda: cp_mod.clear(root, checkpoint_id="CP-999", outcome="x"),
            KeyError,
        ),
    )

    # 8. status transitions on the engagement itself
    man.set_status(root, "active")
    check("engagement status set to active", man.read(root)["status"] == "active")
    check(
        "engagement set_status rejects bogus",
        raises(lambda: man.set_status(root, "bogus"), ValueError),
    )

    # 9. history appended
    data = man.read(root)
    check(
        "history has many entries (every mutation appends)",
        len(data["history"]) >= 15,
        f"got {len(data['history'])}",
    )

    # 10. schema validation gates writes
    bad = man.read(root)
    bad["status"] = "invalid-status"
    check(
        "schema rejects invalid engagement status",
        raises(lambda: man.write(root, bad), ValueError),
    )

    bad2 = man.read(root)
    bad2["jobs"].append(
        {"id": "J-9", "capability": "x", "status": "done"}
    )  # id pattern needs 3 digits
    check(
        "schema rejects job id pattern violation",
        raises(lambda: man.write(root, bad2), ValueError),
    )

    # 11. round-trip: persisted JSON parses cleanly + matches latest read
    raw = json.loads(man.path_for(root).read_text())
    check("persisted JSON has rollup", "rollup" in raw)
    check("persisted JSON validates", not man.validate(raw))

if failures:
    print("FAIL:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(
    "PASS: engagement (manifest + brief + cast + jobs + items + decisions + checkpoints + rollup + schema)"
)
