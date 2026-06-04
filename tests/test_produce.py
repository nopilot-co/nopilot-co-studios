#!/usr/bin/env python3
"""Motion Studio S2 — declarative animation + produce (no video in unit test).
Standalone; run: <python> tests/test_produce.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "motion" / "scripts"))

from motion import animate, produce, storyboard, tokens  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


SAMPLE = REPO / "motion" / "examples" / "explainer-sample.storyboard.json"
spec = storyboard.load(SAMPLE)
tok = tokens.resolve(spec["global"].get("brand"), spec["global"].get("motion_system"))

# Stage sizing.
check("16:9 stage", animate.stage_size(spec) == (1280, 720), str(animate.stage_size(spec)))
check("9:16 stage", animate.stage_size({"global": {"aspect": "9:16"}}) == (720, 1280))

# Animated HTML: self-contained, sequenced, branded.
html = animate.render_html(spec, tok)
check("html doctype", html.lstrip().startswith("<!doctype html>"))
check("has stage", 'class="stage"' in html)
check("scene keyframes", "@keyframes sceneShow" in html and "@keyframes mUp" in html)
check("scene count", html.count('class="scene"') == len(spec["scenes"]), str(html.count('class="scene"')))
check("has narration content", "first conversation begins" in html)
# Scenes are sequenced (later scene has a non-zero animation-delay).
check("sequenced delay", " 4s both" in html or " 4.0s both" in html or "4s both" in html, "no delayed scene")

# Engine selection — auto keeps the declarative default; both explicit.
check("auto → declarative", produce.select_engine("auto") == "declarative")
check("explicit declarative", produce.select_engine("declarative") == "declarative")
check("explicit remotion", produce.select_engine("remotion") == "remotion")

# produce(make_video=False) writes the HTML preview and returns it.
with tempfile.TemporaryDirectory() as d:
    out = produce.produce(SAMPLE, Path(d), make_video=False)
    check("produce html output", "html" in out and out["html"].exists(), str(out))
    check("produce no video", "mp4" not in out)

# Remotion engine is wired (S3): the project ships and detection is boolean.
rd = produce._remotion_dir()
check("remotion package.json", (rd / "package.json").exists(), str(rd))
for f in ("src/index.ts", "src/Root.tsx", "src/Storyboard.tsx"):
    check(f"remotion {f}", (rd / f).exists())
check("remotion availability is bool", isinstance(produce._remotion_available(), bool))

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: motion produce (animate + engine select + html)")
