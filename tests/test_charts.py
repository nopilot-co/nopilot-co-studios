#!/usr/bin/env python3
"""data-viz engine (#20) — matplotlib SVG charts, expanded per export.
Standalone; run: design/.venv/bin/python tests/test_charts.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

from studio import charts  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


TOK = {
    "color": {
        "neutral": "#142F54",
        "surface": "#21456b",
        "tertiary": "#B14B33",
        "on_primary": "#FFFFFF",
        "secondary": "#6B7280",
        "primary": "#2A3548",
    },
    "space": {"sm": "8pt", "md": "16pt", "lg": "32pt"},
    "radius": {"sm": "2pt", "md": "4pt", "lg": "8pt"},
}

# bar: a single series renders to SVG with the data + brand colour.
svg = charts.render_svg(
    {
        "type": "bar",
        "title": "Revenue",
        "x": ["Q1", "Q2", "Q3", "Q4"],
        "y": [12, 18, 15, 24],
    },
    TOK,
)
check("bar: is svg", svg.lstrip().startswith("<?xml") or "<svg" in svg[:400], svg[:80])
check("bar: has title", "Revenue" in svg)
check(
    "bar: brand accent",
    "B14B33" in svg or "b14b33" in svg.lower(),
    "accent colour missing",
)

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: charts (bar)")
