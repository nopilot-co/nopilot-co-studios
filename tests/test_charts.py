#!/usr/bin/env python3
"""data-viz engine (#20) — matplotlib SVG charts, expanded per export.
Standalone; run: design/.venv/bin/python tests/test_charts.py
"""

from __future__ import annotations

import sys
import tempfile
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

# every type renders valid SVG.
for ctype in ("line", "pie", "scatter", "area"):
    spec = {"type": ctype, "x": ["A", "B", "C"], "y": [3, 5, 4]}
    if ctype == "pie":
        spec = {"type": "pie", "labels": ["A", "B", "C"], "values": [3, 5, 4]}
    s = charts.render_svg(spec, TOK)
    check(f"{ctype}: is svg", "<svg" in s[:400], ctype)

# multi-series bar.
ms = charts.render_svg(
    {
        "type": "bar",
        "x": ["Q1", "Q2"],
        "series": [{"name": "Plan", "y": [10, 14]}, {"name": "Actual", "y": [12, 18]}],
    },
    TOK,
)
check("multi-series legend", "Plan" in ms and "Actual" in ms)

# bad type -> render_svg raises (so expand can catch it).
raised = False
try:
    charts.render_svg({"type": "nope", "y": [1]}, TOK)
except Exception:
    raised = True
check("bad type raises", raised)

# expand: writes an SVG file + replaces the div; bad chart -> fallback, no crash.
with tempfile.TemporaryDirectory() as td:
    out = Path(td)
    doc = "Intro.\n\n::: chart\ntype: bar\nx: [Q1, Q2]\ny: [3, 9]\n:::\n\nOutro.\n"
    h = charts.expand(doc, "html", TOK, out)
    check("expand html img", "![](_chart-1.svg)" in h, h)
    check("expand wrote svg", (out / "_chart-1.svg").exists())
    check("expand prose kept", "Intro." in h and "Outro." in h)
    p = charts.expand(doc, "pdf", TOK, out)
    check("expand pdf image", "#image(" in p and "_chart-" in p, p)
    bad = charts.expand("::: chart\ntype: nope\n:::\n", "html", TOK, out)
    check("expand bad -> fallback", "could not render" in bad and "::: panel" in bad)
    # non-chart div passes through
    other = "::: pullquote\nhi\n:::\n"
    check("expand passthrough", charts.expand(other, "html", TOK, out) == other)

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: charts (bar)")
