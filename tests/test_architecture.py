#!/usr/bin/env python3
"""architecture studio (#81) — store + spec materialiser + invariants + ADR CRUD.

Standalone; run any venv with pyyaml + jsonschema:
  nitpicker/.venv/bin/python tests/test_architecture.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "architecture" / "scripts"))

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


VALID_SPEC = {
    "engagement": "demo",
    "objective": "Cutover ingest pipeline",
    "systems": [
        {
            "id": "api",
            "name": "Public API",
            "role": "ingress",
            "status": "evolving",
            "criticality": "critical",
        },
        {
            "id": "worker",
            "name": "Worker",
            "role": "processor",
            "status": "new",
            "criticality": "high",
        },
        {
            "id": "warehouse",
            "name": "Warehouse",
            "role": "store",
            "status": "existing",
            "criticality": "high",
        },
    ],
    "data_flows": [
        {
            "id": "f-api-worker",
            "from": "api",
            "to": "worker",
            "direction": "one-way",
            "frequency": "on-event",
            "payload": "ingest-event",
            "criticality": "high",
        },
        {
            "id": "f-worker-warehouse",
            "from": "worker",
            "to": "warehouse",
            "direction": "one-way",
            "frequency": "batch",
            "payload": "processed-batch",
            "criticality": "high",
        },
    ],
    "integrations": [
        {
            "id": "i-event-bus",
            "flow": "f-api-worker",
            "technology": "Kafka",
            "contract": "ingest-event-v1.proto",
            "auth": "mTLS",
            "error_handling": "DLQ + retry with exponential backoff",
        }
    ],
}


with tempfile.TemporaryDirectory() as td:
    os.environ["STUDIOS_DOCKET_ROOT"] = td

    from architecture import architecture_root  # noqa: E402
    from architecture import store, spec as spec_mod, adr as adr_mod  # noqa: E402
    from architecture import invariants, design_bridge  # noqa: E402

    check(
        "architecture_root resolves",
        architecture_root() == (Path(td).resolve() / "architecture"),
        f"got {architecture_root()}",
    )

    # 1. scaffold
    store.scaffold("demo")
    check("engagement scaffolded", store.engagement_exists("demo"))
    check("adrs/ dir created", store.adrs_dir("demo").is_dir())
    check(
        "scaffold rejects duplicate",
        raises(lambda: store.scaffold("demo"), ValueError),
    )

    # 2. valid spec materialise
    spec_json = Path(td) / "spec.json"
    spec_json.write_text(json.dumps(VALID_SPEC))
    data = spec_mod.materialise("demo", spec_json)
    check("spec written", store.spec_path("demo").is_file())
    check("spec preserves engagement", data["engagement"] == "demo")
    check(
        "provenance stamped",
        data["provenance"]["materialised_by"] == "architecture-studio",
    )

    # 3. invariants — missing system in `from`
    bad = json.loads(json.dumps(VALID_SPEC))
    bad["data_flows"].append({"id": "f-bogus", "from": "ghost", "to": "warehouse"})
    inv = invariants.check(bad)
    check(
        "invariant: missing system in `from` flagged",
        any("ghost" in m for m in inv),
        f"got {inv}",
    )

    bad2 = json.loads(json.dumps(VALID_SPEC))
    bad2["integrations"].append({"id": "i-bogus", "flow": "f-ghost"})
    inv2 = invariants.check(bad2)
    check(
        "invariant: integration referencing missing flow flagged",
        any("f-ghost" in m for m in inv2),
        f"got {inv2}",
    )

    bad3 = json.loads(json.dumps(VALID_SPEC))
    bad3["systems"].append({"id": "api", "name": "Duplicate", "role": "x"})
    inv3 = invariants.check(bad3)
    check(
        "invariant: duplicate system id flagged",
        any("duplicate system id" in m for m in inv3),
        f"got {inv3}",
    )

    # 4. materialise rejects invariant-violating spec
    bad_json = Path(td) / "bad.json"
    bad_json.write_text(json.dumps(bad))
    check(
        "materialise rejects invariant breach",
        raises(lambda: spec_mod.materialise("demo", bad_json), ValueError),
    )

    # schema violation (missing required field)
    schema_bad = {"engagement": "demo", "systems": []}  # minItems 1
    schema_json = Path(td) / "schema-bad.json"
    schema_json.write_text(json.dumps(schema_bad))
    check(
        "materialise rejects schema violation",
        raises(lambda: spec_mod.materialise("demo", schema_json), ValueError),
    )

    # 5. version bump on materialise
    ver = store.bump("demo", level="minor")
    check("bump produces 0.1.0", ver == "0.1.0")

    # 6. ADRs — add + list + show
    adr1 = adr_mod.add(
        "demo",
        title="event bus over REST between api and worker",
        status="accepted",
        context="we need replayability",
        decision="use Kafka",
        consequences="adds infra dependency",
    )
    check("ADR id is ADR-001", adr1["id"] == "ADR-001")
    check("ADR file present", Path(adr1["path"]).is_file())

    adr2 = adr_mod.add("demo", title="warehouse partitioning by date")
    check("ADR ids increment", adr2["id"] == "ADR-002")

    items = adr_mod.show("demo")
    check("show lists 2 ADRs", len(items) == 2)
    check(
        "ADR statuses preserved",
        {(i["id"], i["status"]) for i in items}
        == {("ADR-001", "accepted"), ("ADR-002", "proposed")},
    )

    # 7. ADR status transition
    updated = adr_mod.set_status("demo", "ADR-002", "accepted")
    check("set-status updates ADR", updated["status"] == "accepted")
    check(
        "set-status rejects bogus status",
        raises(
            lambda: adr_mod.set_status("demo", "ADR-001", "bogus"),
            ValueError,
        ),
    )
    check(
        "set-status rejects unknown id",
        raises(
            lambda: adr_mod.set_status("demo", "ADR-999", "accepted"),
            KeyError,
        ),
    )

    # 8. design_bridge degrades when design isn't on PATH
    out_dir = Path(td) / "render"
    rendered = design_bridge.render(VALID_SPEC, out_dir=out_dir)
    check(
        "design_bridge writes diagram source",
        (out_dir / "architecture.md").is_file(),
    )
    md = (out_dir / "architecture.md").read_text()
    check("diagram source includes mermaid block", "```mermaid" in md)
    check(
        "diagram source mentions system ids",
        "api" in md and "worker" in md and "warehouse" in md,
    )

    # 9. status transitions
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
    "PASS: architecture (store + spec materialiser + 3 invariants + schema + ADR CRUD + design_bridge degrade + status)"
)
