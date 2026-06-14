#!/usr/bin/env python3
"""delivery studio (#79) — store, plan materialiser, rollups, RAID register.

Standalone; run any venv with pyyaml + jsonschema:
  nitpicker/.venv/bin/python tests/test_delivery.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "delivery" / "scripts"))

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


VALID_PLAN = {
    "engagement": "demo",
    "objective": "Win the renewal pitch",
    "swimlanes": [
        {"id": "design", "name": "Design", "owner_role": "lead"},
        {"id": "content", "name": "Content", "owner_role": "senior"},
    ],
    "phases": [
        {
            "id": "phase-1-mobilise",
            "name": "Mobilise",
            "order": 1,
            "swimlane": "design",
            "entry": ["brief approved"],
            "exit": ["kickoff complete"],
            "dependencies": [],
            "duration_days": 5,
            "buffer_days": 1,
            "confidence": "high",
            "resourcing": [
                {"role": "lead", "days": 2},
                {"role": "senior", "days": 3},
            ],
        },
        {
            "id": "phase-2-design",
            "name": "Design",
            "order": 2,
            "swimlane": "design",
            "entry": ["kickoff complete"],
            "exit": ["design v1 signed off"],
            "dependencies": ["phase-1-mobilise"],
            "duration_days": 10,
            "buffer_days": 2,
            "confidence": "medium",
            "resourcing": [
                {"role": "lead", "days": 5},
                {"role": "senior", "days": 8},
                {"role": "mid", "days": 5},
            ],
        },
        {
            "id": "phase-3-content",
            "name": "Content",
            "order": 3,
            "swimlane": "content",
            "duration_days": 8,
            "buffer_days": 2,
            "resourcing": [
                {"role": "senior", "days": 5},
                {"role": "mid", "days": 5},
            ],
        },
    ],
    "contingency": {"pool_days": 5, "notes": "owned by Principal"},
}

with tempfile.TemporaryDirectory() as td:
    os.environ["STUDIOS_DOCKET_ROOT"] = td

    from delivery import delivery_root  # noqa: E402
    from delivery import store, plan as plan_mod, raid as raid_mod  # noqa: E402

    check(
        "delivery_root resolves to docket root",
        delivery_root() == (Path(td).resolve() / "delivery"),
        f"got {delivery_root()}",
    )

    # 1. scaffold an engagement
    store.scaffold("demo")
    check("engagement scaffolded", store.engagement_exists("demo"))
    check("raid.yml created", store.raid_path("demo").is_file())
    check(
        "scaffold rejects duplicate",
        raises(lambda: store.scaffold("demo"), ValueError),
    )

    # 2. materialise the plan + verify rollups
    plan_json = Path(td) / "plan.json"
    plan_json.write_text(json.dumps(VALID_PLAN))
    data = plan_mod.materialise("demo", plan_json)
    check("plan materialised + written", store.plan_path("demo").is_file())
    rollups = data["rollups"]

    # totals: 5 + 10 + 8 = 23 days; buffers 1+2+2=5; pool 5; contingency_pct = 10/23 = 43.5%
    check(
        "rollups: total_days = 23",
        rollups["total_days"] == 23,
        f"got {rollups['total_days']}",
    )
    check("rollups: buffer_days = 5", rollups["buffer_days"] == 5)
    check("rollups: pool = 5", rollups["contingency_pool_days"] == 5)
    check(
        "rollups: contingency_pct = 43.5%",
        rollups["contingency_pct"] == round(100 * 10 / 23, 1),
        f"got {rollups['contingency_pct']}",
    )
    check("rollups: phase_count = 3", rollups["phase_count"] == 3)
    check("rollups: swimlane_count = 2", rollups["swimlane_count"] == 2)
    # by_role: lead 2+5=7, senior 3+8+5=16, mid 5+5=10
    check("rollups: by_role lead = 7", rollups["by_role"]["lead"] == 7)
    check("rollups: by_role senior = 16", rollups["by_role"]["senior"] == 16)
    check("rollups: by_role mid = 10", rollups["by_role"]["mid"] == 10)
    # by_swimlane: design 5+10=15, content 8
    check("rollups: swimlane design = 15", rollups["by_swimlane"]["design"] == 15)
    check("rollups: swimlane content = 8", rollups["by_swimlane"]["content"] == 8)

    # 3. invalid plan rejected
    bad = dict(VALID_PLAN)
    bad["phases"] = []  # minItems 1
    bad_json = Path(td) / "bad.json"
    bad_json.write_text(json.dumps(bad))
    check(
        "empty phases array rejected",
        raises(lambda: plan_mod.materialise("demo", bad_json), ValueError),
    )

    # missing required field
    worse = dict(VALID_PLAN)
    worse["phases"] = [{"id": "p", "name": "x", "order": 1}]  # missing duration_days
    worse_json = Path(td) / "worse.json"
    worse_json.write_text(json.dumps(worse))
    check(
        "missing duration_days rejected",
        raises(lambda: plan_mod.materialise("demo", worse_json), ValueError),
    )

    # 4. version bump on materialise
    ver = store.bump("demo", level="minor")
    check("bump produces 0.1.0", ver == "0.1.0")

    # 5. RAID — add + ids + resolve + summary
    r1 = raid_mod.add(
        "demo", kind="risk", title="vendor outage during cutover", severity="high"
    )
    a1 = raid_mod.add(
        "demo", kind="assumption", title="client signs off in 5 days", severity="medium"
    )
    d1 = raid_mod.add(
        "demo", kind="dependency", title="brand assets from client", owner="lead"
    )
    check("RAID risk gets R-001", r1["id"] == "R-001")
    check("RAID assumption gets A-001", a1["id"] == "A-001")
    check("RAID dependency gets D-001", d1["id"] == "D-001")
    check("RAID risk severity recorded", r1["severity"] == "high")

    # add a second risk → R-002
    r2 = raid_mod.add("demo", kind="risk", title="scope creep on phase 2")
    check("RAID id allocation increments", r2["id"] == "R-002")

    # invalid kind rejected
    check(
        "RAID invalid kind rejected",
        raises(lambda: raid_mod.add("demo", kind="bogus", title="x"), ValueError),
    )

    # resolve
    resolved = raid_mod.resolve(
        "demo", raid_id="R-001", resolution="agreed standby vendor"
    )
    check("RAID resolve marks status", resolved["status"] == "resolved")
    check(
        "RAID resolve records resolution",
        resolved["resolution"] == "agreed standby vendor",
    )

    # resolve unknown
    check(
        "RAID resolve unknown id raises",
        raises(
            lambda: raid_mod.resolve("demo", raid_id="R-999", resolution="x"),
            KeyError,
        ),
    )

    # summary
    s = raid_mod.summary("demo")
    check("summary total = 4", s["total"] == 4)
    check(
        "summary risk open = 1, resolved = 1",
        s["risk"]["open"] == 1 and s["risk"]["resolved"] == 1,
    )
    check("summary assumption open = 1", s["assumption"]["open"] == 1)
    check("summary dependency open = 1", s["dependency"]["open"] == 1)
    check("summary total open = 3", s["open"] == 3)

    # filter
    risks_only = raid_mod.show("demo", kind="risk")
    check("show --kind risk filters correctly", len(risks_only) == 2)

    # 6. status transitions
    store.set_status("demo", "approved")
    check("status set to approved", store.read_version("demo")["status"] == "approved")
    check(
        "invalid status rejected",
        raises(lambda: store.set_status("demo", "bogus"), ValueError),
    )

if failures:
    print("FAIL:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(
    "PASS: delivery (store + plan materialiser + rollups + RAID CRUD/IDs/summary + status)"
)
