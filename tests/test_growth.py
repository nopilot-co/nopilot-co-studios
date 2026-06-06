#!/usr/bin/env python3
"""growth studio (#87) — store + leads materialiser + market materialiser + rollups."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "growth" / "scripts"))

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


LEADS = {
    "engagement": "demo",
    "icp": "vp-eng-scaleup",
    "criteria": ["50-500 engineers", "Series B+", "build platform"],
    "leads": [
        {
            "company": "Acme",
            "fit": "high",
            "owner": "alice",
            "source": "linkedin",
            "signals": {"matched": ["scaleup", "platform"]},
        },
        {"company": "Beta", "fit": "medium", "owner": "alice", "source": "referral"},
        {"company": "Gamma", "fit": "low", "owner": "bob", "source": "linkedin"},
        {"company": "Delta", "fit": "high", "owner": "bob", "source": "event"},
    ],
}

MARKET = {
    "engagement": "demo",
    "segments": [
        {
            "id": "seg-saas",
            "name": "B2B SaaS",
            "size": "$50B",
            "characteristics": ["recurring revenue"],
        },
        {"id": "seg-fin", "name": "Fintech", "size": "$20B"},
    ],
    "competitors": [
        {
            "id": "c-foo",
            "name": "Foo Co",
            "segment": "seg-saas",
            "positioning_quadrant": "high-touch/high-price",
        },
        {
            "id": "c-bar",
            "name": "Bar Co",
            "segment": "seg-saas",
            "positioning_quadrant": "self-serve/low-price",
        },
        {
            "id": "c-baz",
            "name": "Baz Co",
            "segment": "seg-fin",
            "positioning_quadrant": "high-touch/high-price",
        },
    ],
    "positioning": {
        "axes": ["price", "service-model"],
        "our_position": ["mid", "high-touch"],
    },
}

with tempfile.TemporaryDirectory() as td:
    os.environ["STUDIOS_DOCKET_ROOT"] = td

    from growth import growth_root  # noqa: E402
    from growth import store, leads as leads_mod, market as market_mod  # noqa: E402

    check(
        "growth_root resolves",
        growth_root() == (Path(td).resolve() / "growth"),
        f"got {growth_root()}",
    )

    # 1. scaffold
    store.scaffold("demo")
    check("engagement scaffolded", store.engagement_exists("demo"))
    check(
        "scaffold rejects duplicate",
        raises(lambda: store.scaffold("demo"), ValueError),
    )

    # 2. leads materialise + rollups
    p = Path(td) / "leads.json"
    p.write_text(json.dumps(LEADS))
    data = leads_mod.materialise("demo", p)
    check("leads written", store.leads_path("demo").is_file())
    check(
        "leads provenance stamped",
        data["provenance"]["materialised_by"] == "growth-studio",
    )
    r = data["rollups"]
    check("leads rollup: count = 4", r["count"] == 4)
    check("leads rollup: by_fit high=2", r["by_fit"]["high"] == 2)
    check("leads rollup: by_fit medium=1", r["by_fit"]["medium"] == 1)
    check("leads rollup: by_fit low=1", r["by_fit"]["low"] == 1)
    check("leads rollup: by_source linkedin=2", r["by_source"]["linkedin"] == 2)
    check("leads rollup: by_owner alice=2", r["by_owner"]["alice"] == 2)

    # 3. leads schema validation
    bad = dict(LEADS)
    bad["leads"] = []
    bad_path = Path(td) / "bad.json"
    bad_path.write_text(json.dumps(bad))
    check(
        "empty leads array rejected",
        raises(lambda: leads_mod.materialise("demo", bad_path), ValueError),
    )

    worse = dict(LEADS)
    worse["leads"] = [{"company": "X"}]  # missing fit
    worse_path = Path(td) / "worse.json"
    worse_path.write_text(json.dumps(worse))
    check(
        "missing fit rejected",
        raises(lambda: leads_mod.materialise("demo", worse_path), ValueError),
    )

    # 4. market materialise + rollups
    mp = Path(td) / "market.json"
    mp.write_text(json.dumps(MARKET))
    data = market_mod.materialise("demo", mp)
    check("market written", store.market_path("demo").is_file())
    r = data["rollups"]
    check("market rollup: segment_count = 2", r["segment_count"] == 2)
    check("market rollup: competitor_count = 3", r["competitor_count"] == 3)
    check(
        "market rollup: competitors_by_segment",
        r["competitors_by_segment"]["seg-saas"] == 2
        and r["competitors_by_segment"]["seg-fin"] == 1,
    )
    check(
        "market rollup: competitors_by_quadrant",
        r["competitors_by_quadrant"]["high-touch/high-price"] == 2,
    )

    # market schema rejection
    bad_m = {"engagement": "demo", "segments": []}
    bad_m_path = Path(td) / "bad-market.json"
    bad_m_path.write_text(json.dumps(bad_m))
    check(
        "empty segments rejected",
        raises(lambda: market_mod.materialise("demo", bad_m_path), ValueError),
    )

    # 5. version bump
    ver = store.bump("demo", level="minor")
    check("bump produces 0.1.0", ver == "0.1.0")

    # 6. status transitions
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
print(
    "PASS: growth (store + leads materialiser + market materialiser + rollups + schemas + status)"
)
