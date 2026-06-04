#!/usr/bin/env python3
"""audience studio (#41) — reader model + derived rubric + reuse of the nitpicker
scoring engine. Standalone; run: design/.venv/bin/python tests/test_audience.py

Covers the mechanics that need no external CLI (store/schema, rubric derivation +
weights, the date-safe loader). The scoring reuse (`audience review score` →
`nit aggregate`) is exercised only when the `nit` CLI is reachable, so the suite
stays green without a nitpicker install.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "audience" / "scripts"))

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


FULL_MODEL = {
    "audience": "demo-reader",
    "name": "Demo reader",
    "status": "inferred",
    "source": "inferred",
    "persona": {"role": "VP Engineering", "one_line": "Owns delivery + reliability."},
    "need_state": {
        "stage": "evaluating",
        "needs": [
            {
                "id": "reliability-at-scale",
                "statement": "Keep p99 as load doubles",
                "priority": "critical",
            },
            {"id": "reduce-toil", "statement": "Cut on-call", "priority": "high"},
            {"id": "nice-to-have", "statement": "Pretty dashboards", "priority": "low"},
        ],
    },
    # Unquoted ISO date — must survive as a string (date-safe loader).
    "provenance": {
        "sources": [
            {
                "id": "t",
                "kind": "transcript",
                "ref": "research/t.md",
                "captured": "2026-06-04",
            }
        ]
    },
}

with tempfile.TemporaryDirectory() as td:
    os.environ["STUDIOS_DOCKET_ROOT"] = td  # redirect the store into the temp dir
    from audience import rubric as rub  # noqa: E402  (after env set)
    from audience import store  # noqa: E402

    # --- store + schema --------------------------------------------------------
    store.scaffold("demo-reader", persona={"name": "Demo", "persona": {"role": "VP"}})
    check("scaffold: file written", store.exists("demo-reader"))
    check("scaffold: refuses clobber", raises(lambda: store.scaffold("demo-reader")))

    store.write("demo-reader", FULL_MODEL)
    check(
        "schema: full model valid",
        store.validate(FULL_MODEL) == [],
        str(store.validate(FULL_MODEL)),
    )
    reread = store.read("demo-reader")
    check(
        "loader: ISO date stays a string",
        reread["provenance"]["sources"][0]["captured"] == "2026-06-04",
        repr(reread["provenance"]["sources"][0]["captured"]),
    )
    bad = {
        **FULL_MODEL,
        "need_state": {"needs": [{"id": "x", "statement": "y", "priority": "urgent"}]},
    }
    check("schema: rejects bad priority", store.validate(bad) != [])
    built = store.mark_built("demo-reader", status="validated")
    check(
        "build: stamps + sets status",
        built["status"] == "validated" and built["provenance"]["built"],
    )

    # --- rubric derivation -----------------------------------------------------
    r = rub.derive("demo-reader")
    by = {t["test"]: t for t in r["tests"]}
    check(
        "derive: one test per need",
        set(by) == {"reliability-at-scale", "reduce-toil", "nice-to-have"},
    )
    check(
        "derive: critical → weight 2.0 + gate",
        by["reliability-at-scale"]["weight"] == 2.0
        and "reliability-at-scale" in r["gates"],
    )
    check("derive: high → weight 1.5", by["reduce-toil"]["weight"] == 1.5)
    check(
        "derive: low → weight 0.5, not a gate",
        by["nice-to-have"]["weight"] == 0.5 and "nice-to-have" not in r["gates"],
    )
    check("rubric: rejects unfilled stub criteria", rub.validate(r) != [])
    for t in r["tests"]:
        t["criteria"] = ["a concrete, observable signal"]
    check(
        "rubric: valid once criteria filled",
        rub.validate(r) == [],
        str(rub.validate(r)),
    )
    rub.write("demo-reader", r)

    # --- derive needs real needs ----------------------------------------------
    store.write(
        "demo-reader",
        {
            **FULL_MODEL,
            "need_state": {
                "needs": [{"id": "placeholder", "statement": "", "priority": "high"}]
            },
        },
    )
    check(
        "derive: errors with no real needs",
        raises(lambda: rub.derive("demo-reader"), ValueError),
    )
    store.write("demo-reader", FULL_MODEL)

    # --- scoring reuse (only if the nitpicker CLI is reachable) -----------------
    from audience import nit_bridge, session  # noqa: E402

    if nit_bridge.available():
        rub.write("demo-reader", r)  # filled rubric
        sess = session.new("demo-reader", "crit", str(REPO / "README.md"))
        (sess / "review" / "v1.0.0" / "scores.yml").write_text(
            "dimensions: {reader-fit: {score: 2}}\n"
            "tests: {reliability-at-scale: {score: 1}, reduce-toil: {score: 3}, nice-to-have: {score: 5}}\n"
        )
        card = session.score(sess)
        check(
            "score: gate forces fail",
            card["verdict"] == "fail"
            and "reliability-at-scale" in card["gates_failed"],
        )
        check(
            "score: writes scorecard",
            (sess / "review" / "v1.0.0" / "scorecard.json").is_file(),
        )
        check(
            "score: writes strengthening areas",
            (sess / "review" / "v1.0.0" / "strengthening-areas.md").is_file(),
        )
    else:
        print("  (skipped scoring reuse — nit CLI not reachable)")


if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: audience (store + schema + rubric derivation + scoring reuse)")
