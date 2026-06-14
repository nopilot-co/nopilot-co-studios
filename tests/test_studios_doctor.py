#!/usr/bin/env python3
"""studios doctor (#104) — registry + CLI readiness smoke test.

  python3 tests/test_studios_doctor.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from studios_doctor import doctor  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


rep = doctor()
check("returns orchestrators dict", isinstance(rep.get("orchestrators"), dict))
check("returns studios list", isinstance(rep.get("studios"), list))
check("all_ready is bool", isinstance(rep.get("all_ready"), bool))

for name in ("planner", "engagement"):
    check(f"orchestrator key {name}", name in rep["orchestrators"])

active = 0
for s in rep["studios"]:
    active += 1
    check(f"studio {s['slug']} has install hint", bool(s.get("install")))
    check(
        f"studio {s['slug']} ready flag matches cli",
        s["ready"] == bool(s.get("cli")),
    )

check("at least one active studio in registry", active >= 1)

if failures:
    print("FAIL")
    for f in failures:
        print(" ", f)
    raise SystemExit(1)

print(f"OK — {len(failures) + 6 + active} checks passed (structure + {active} studios)")
