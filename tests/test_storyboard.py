#!/usr/bin/env python3
"""Motion Studio S1 — storyboard schema/validator, token resolution, board.
Standalone; run: <python> tests/test_storyboard.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "motion" / "scripts"))

from motion import board, storyboard, tokens  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


SAMPLE = REPO / "motion" / "examples" / "explainer-sample.storyboard.json"

# The shipped sample validates, loads, and normalizes.
spec = storyboard.load(SAMPLE)
check("sample valid", spec["scenes"], "no scenes")
check("normalize fps default", spec["global"]["fps"] == 30, str(spec["global"]))
check(
    "normalize layer region default",
    all(
        "region" in lr
        for s in spec["scenes"]
        for lr in s["layers"]
    ),
)
check("total duration", storyboard.total_duration(spec) == 20, str(storyboard.total_duration(spec)))

# Bad specs are rejected with errors.
check("missing brand rejected", storyboard.validate({"version": "0.1", "global": {}, "scenes": []}))
bad_layer = {
    "version": "0.1",
    "global": {"brand": "x"},
    "scenes": [{"id": "s", "duration": 1, "layers": [{"type": "wormhole"}]}],
}
errs = storyboard.validate(bad_layer)
check("bad layer type rejected", any("wormhole" in e or "enum" in e.lower() for e in errs), str(errs))
check("zero scenes rejected", storyboard.validate({"version": "0.1", "global": {"brand": "x"}, "scenes": []}))

# Tokens: defaults present; motion-system overrides; catalog lists the system.
tok = tokens.resolve(brand=None, motion_system=None)
check("color defaults", tok["color"]["tertiary"].startswith("#"), str(tok["color"]))
check("motion defaults", tok["motion"]["duration"]["base"] == 400, str(tok["motion"]))
check("lists calm-brief", "calm-brief" in tokens.list_motion_systems(), str(tokens.list_motion_systems()))
tok2 = tokens.resolve(brand=None, motion_system="calm-brief")
check("motion-system override", tok2["motion"]["duration"]["base"] == 500, str(tok2["motion"]["duration"]))

# Board renders self-contained HTML referencing the content.
html = board.render_html(spec, tok2)
check("board is html", html.lstrip().startswith("<!doctype html>"))
check("board has title", "Brand name: framework" in html)
check("board has narration", "first conversation begins" in html)
check("board has layer type", "TEXT" in html and "CHART" in html, "missing layer tags")
check("board no template leak", "{" not in html.split("<body>")[1], "unfilled placeholder in body")

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: motion storyboard (schema + tokens + board)")
