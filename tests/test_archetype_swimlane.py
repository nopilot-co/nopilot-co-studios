#!/usr/bin/env python3
"""Swimlane (timeline/gantt) parity — gslide + UDS-HTML (ADR-006 / #129). Standalone.

NB: pptx renders a DISTINCT node-flow swimlane (lanes of connected boxes), a
different visualisation that is intentionally NOT unified into this node (#129).
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

from studio import archetype_ir as ir  # noqa: E402
from studio import gslide, uds_html  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


node = ir.normalise_swimlane({"months": ["Jan", "Feb", "Mar", "Apr"],
    "lanes": [{"name": "Discovery", "label": "Audit", "start": "Jan", "end": "Feb"},
              {"name": "Design", "label": "Build", "start": "Feb", "end": "Mar"}],
    "milestones": [{"at": "Mar", "label": "Launch"}]})
check("months parsed", node.months == ["Jan", "Feb", "Mar", "Apr"])
check("lane names", [lane.name for lane in node.lanes] == ["Discovery", "Design"], str(node.lanes))
check("lane span start/end", (node.lanes[0].start, node.lanes[0].end) == ("Jan", "Feb"))
check("milestone parsed", node.milestones[0].label == "Launch")
check("empty degrades", ir.normalise_swimlane("x: 1").is_empty)
check("capabilities[swimlane] = gslide+html", ir.CAPABILITIES["swimlane"] == {"gslide", "html"})
check("timeline aliases swimlane", ir.canonical("timeline") == "swimlane")

SW_MD = ("---\ntitle: T\n---\n\n## Plan {#p}\n\n::: swimlane\n"
         "months: [Jan, Feb, Mar, Apr]\n"
         "lanes:\n  - {name: Discovery, label: Audit, start: Jan, end: Feb}\n"
         "  - {name: Design, label: Build, start: Feb, end: Mar}\n"
         "milestones:\n  - {at: Mar, label: Launch}\n:::\n")

with tempfile.TemporaryDirectory() as td:
    src = Path(td) / "d.md"
    src.write_text(SW_MD)
    _t, reqs = gslide.build_requests(src, brand="nopilot")
    inserts = [r["insertText"]["text"] for r in reqs if "insertText" in r]
    check("gslide: lane names", all(x in inserts for x in ("Discovery", "Design")), str(inserts))
    check("gslide: month axis", all(x in inserts for x in ("Jan", "Feb", "Mar", "Apr")))
    check("gslide: milestone", "Launch" in inserts)

_m, html = uds_html.render_body(SW_MD, brand="nopilot")
check("html: uds-swimlane figure", 'class="uds-swimlane"' in html)
check("html: lane names", all(x in html for x in ("Discovery", "Design")))
check("html: month axis", all(x in html for x in ("Jan", "Feb", "Mar", "Apr")))
check("html: milestone", "Launch" in html)
check("html: fence consumed", ":::" not in html)

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: swimlane archetype — native parity across gslide / UDS-HTML")
