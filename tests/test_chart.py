#!/usr/bin/env python3
"""Motion Studio S4 — animated infographics (bar chart + KPI count-up).
Standalone; run: <python> tests/test_chart.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "motion" / "scripts"))

from motion import animate, storyboard, tokens  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


SAMPLE = REPO / "motion" / "examples" / "explainer-sample.storyboard.json"

# Schema accepts chart layers with `chart` + `data`.
spec = storyboard.load(SAMPLE)
charts = [lr for s in spec["scenes"] for lr in s["layers"] if lr["type"] == "chart"]
check("sample has chart layers", len(charts) >= 2, str(len(charts)))
kinds = {c.get("chart") for c in charts}
check("has bar + kpi", {"bar", "kpi"} <= kinds, str(kinds))

# A bad bar datum (missing value) is rejected.
bad = {
    "version": "0.1", "global": {"brand": "x"},
    "scenes": [{"id": "s", "duration": 1, "layers": [
        {"type": "chart", "chart": "bar", "data": [{"label": "x"}]}]}],
}
check("bar datum needs value", bool(storyboard.validate(bad)), "expected error")

# animate renders a real bar chart + KPI count-up, not placeholders.
tok = tokens.resolve(spec["global"].get("brand"), spec["global"].get("motion_system"))
html = animate.render_html(spec, tok)
check("bar chart rendered", "chart-bar" in html)
check("bar grows", "animation:barGrow" in html and "scaleY" in html)
for label in ("Industrial", "Technical", "Allegorical", "Literal"):
    check(f"bar label {label}", label in html)
check("bar values", ">6<" in html or ">4<" in html, "value labels missing")
check("kpi count-up", "kpiCount" in html and "@property --kpi-num" in html)
check("kpi target", "--target:5" in html, "kpi target not set")
check("charts not placeholdered", '>CHART<' not in html, "chart still rendered as a placeholder")

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: motion animated infographics (bar + kpi)")
