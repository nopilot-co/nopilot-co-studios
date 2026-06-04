#!/usr/bin/env python3
"""Motion Studio S3 — Lottie export structure. Standalone; run:
    <python> tests/test_lottie.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "motion" / "scripts"))

from motion import lottie, storyboard, tokens  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


SAMPLE = REPO / "motion" / "examples" / "explainer-sample.storyboard.json"
spec = storyboard.load(SAMPLE)
tok = tokens.resolve(spec["global"].get("brand"), spec["global"].get("motion_system"))
anim = lottie.render(spec, tok)

# Top-level Lottie shape.
for key in ("v", "fr", "ip", "op", "w", "h", "layers", "fonts"):
    check(f"has {key}", key in anim, str(sorted(anim.keys())))
fps = spec["global"]["fps"]
check("fps", anim["fr"] == fps, str(anim["fr"]))
check("op = total frames", anim["op"] == round(storyboard.total_duration(spec) * fps), str(anim["op"]))
check("size 16:9", (anim["w"], anim["h"]) == (1280, 720), f"{anim['w']}x{anim['h']}")

layers = anim["layers"]
check("has layers", len(layers) > len(spec["scenes"]), str(len(layers)))
check("bg layer last (bottom)", layers[-1]["nm"] == "bg" and layers[-1]["ty"] == 4)

text_layers = [l for l in layers if l["ty"] == 5]
shape_layers = [l for l in layers if l["ty"] == 4]
check("has text layers", len(text_layers) >= 4, str(len(text_layers)))
check("has shape layers", len(shape_layers) >= 2, str(len(shape_layers)))

# A title text layer carries the content + a font + a colour.
titles = [l for l in text_layers if l["t"]["d"]["k"][0]["s"]["t"] == "Brand name: framework"]
check("title text present", bool(titles), "no title text layer")
if titles:
    doc = titles[0]["t"]["d"]["k"][0]["s"]
    check("text font ref", doc["f"] == "MotionSans")
    check("text colour rgb floats", len(doc["fc"]) == 3 and all(0 <= c <= 1 for c in doc["fc"]), str(doc["fc"]))

# Content layers fade (animated opacity), and stay within their scene window.
content = [l for l in layers if l["nm"] != "bg"]
check("opacity animated", all(l["ks"]["o"]["a"] == 1 for l in content), "static opacity")
check("layer windows ordered", all(l["op"] > l["ip"] for l in content))

# Round-trips through JSON.
check("json serializable", isinstance(json.dumps(anim), str))

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: motion lottie export (structure)")
