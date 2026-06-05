#!/usr/bin/env python3
"""analytics studio (#85) — store + materialiser + rollups."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "analytics" / "scripts"))

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


VALID_ANALYSIS = {
    "engagement": "demo",
    "objective": "Understand engagement drop-off",
    "dataset": {
        "source": "events.csv",
        "kind": "csv",
        "sample_size": 10000,
        "fields": ["user_id", "step", "ts", "completed"],
    },
    "descriptive_statistics": {"completion_rate": 0.42},
    "patterns": [
        {
            "id": "p-drop-step-3",
            "description": "Drop-off concentrates at step 3",
            "confidence": "high",
            "evidence": "step=3 drops 38%",
        },
        {
            "id": "p-late-cohort",
            "description": "Late-week cohorts churn faster",
            "confidence": "medium",
        },
    ],
    "insights": [
        {
            "id": "i-onboarding-friction",
            "statement": "Step 3 friction is the main onboarding drop-off driver",
            "severity": "high",
            "confidence": "high",
            "supporting_patterns": ["p-drop-step-3"],
        },
        {
            "id": "i-cohort-decay",
            "statement": "Acquisition timing materially affects activation",
            "severity": "medium",
            "confidence": "medium",
            "supporting_patterns": ["p-late-cohort"],
        },
        {
            "id": "i-flag",
            "statement": "Need fresher data — 90 days is too stale",
            "severity": "low",
            "confidence": "low",
        },
    ],
    "recommendations": [
        {
            "id": "r-redesign-step-3",
            "title": "Redesign step 3",
            "owner": "design",
            "severity": "high",
        },
        {
            "id": "r-fresh-data",
            "title": "Pull last 30d",
            "owner": "analytics",
            "severity": "medium",
        },
    ],
}

with tempfile.TemporaryDirectory() as td:
    os.environ["STUDIOS_DOCKET_ROOT"] = td

    from analytics import analytics_root  # noqa: E402
    from analytics import store, analysis as ana_mod  # noqa: E402

    check(
        "analytics_root resolves",
        analytics_root() == (Path(td).resolve() / "analytics"),
        f"got {analytics_root()}",
    )

    # 1. scaffold
    store.scaffold("demo")
    check("engagement scaffolded", store.engagement_exists("demo"))
    check("viz/ dir created", (store.engagement_dir("demo") / "viz").is_dir())
    check(
        "scaffold rejects duplicate",
        raises(lambda: store.scaffold("demo"), ValueError),
    )

    # 2. materialise valid analysis + verify rollups
    p = Path(td) / "analysis.json"
    p.write_text(json.dumps(VALID_ANALYSIS))
    data = ana_mod.materialise("demo", p)
    check("analysis written", store.analysis_path("demo").is_file())
    check(
        "provenance stamped",
        data["provenance"]["materialised_by"] == "analytics-studio",
    )

    r = data["rollups"]
    check("rollups: pattern_count = 2", r["pattern_count"] == 2)
    check("rollups: insight_count = 3", r["insight_count"] == 3)
    check("rollups: recommendation_count = 2", r["recommendation_count"] == 2)
    check("rollups: sample_size = 10000", r["sample_size"] == 10000)
    check(
        "rollups: insights by severity counted",
        r["insights_by_severity"]["high"] == 1
        and r["insights_by_severity"]["medium"] == 1
        and r["insights_by_severity"]["low"] == 1,
    )
    check(
        "rollups: insights by confidence counted",
        r["insights_by_confidence"]["high"] == 1
        and r["insights_by_confidence"]["medium"] == 1
        and r["insights_by_confidence"]["low"] == 1,
    )
    check(
        "rollups: recommendations by owner counted",
        r["recommendations_by_owner"]["design"] == 1
        and r["recommendations_by_owner"]["analytics"] == 1,
    )

    # 3. invalid analysis — empty insights array
    bad = dict(VALID_ANALYSIS)
    bad["insights"] = []
    bad_path = Path(td) / "bad.json"
    bad_path.write_text(json.dumps(bad))
    check(
        "empty insights rejected",
        raises(lambda: ana_mod.materialise("demo", bad_path), ValueError),
    )

    # missing required field
    worse = dict(VALID_ANALYSIS)
    worse["insights"] = [{"id": "x", "statement": "y"}]  # missing severity
    worse_path = Path(td) / "worse.json"
    worse_path.write_text(json.dumps(worse))
    check(
        "missing severity rejected",
        raises(lambda: ana_mod.materialise("demo", worse_path), ValueError),
    )

    # 4. version bump
    ver = store.bump("demo", level="minor")
    check("bump produces 0.1.0", ver == "0.1.0")

    # 5. status transitions
    store.set_status("demo", "approved")
    check("status set", store.read_version("demo")["status"] == "approved")
    check(
        "invalid status rejected",
        raises(lambda: store.set_status("demo", "bogus"), ValueError),
    )

if failures:
    print("FAIL:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("PASS: analytics (store + materialiser + rollups + status)")
