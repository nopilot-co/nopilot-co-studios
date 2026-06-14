#!/usr/bin/env python3
"""Layout tier (ADR-005 / #98) — verifies the new third orthogonal tier.

Run: design/.venv/bin/python tests/test_layouts.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

formats = importlib.import_module("studio.formats")
SealedKeyConflict = formats.SealedKeyConflict

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


# 1. layouts/ directory exists with at least linear + frame.
layouts = set(formats.list_layouts())
check("linear layout present", "linear" in layouts)
check("frame layout present", "frame" in layouts)

# 2. showcase-html resolves with layout=frame and the sealed structural ruleset.
sh = formats.resolve("showcase-html")
check("showcase-html layout=frame", sh.get("layout") == "frame", str(sh.get("layout")))
check("showcase-html layout_name composed", sh.get("layout_name", "").startswith("Frame"))
check(
    "showcase-html ruleset.structure inherited from frame",
    sh.get("ruleset", {}).get("structure") == "master-detail",
)
check(
    "showcase-html ruleset.master_holds_whole_topic inherited from frame",
    sh.get("ruleset", {}).get("master_holds_whole_topic") is True,
)
check(
    "showcase-html navigation_affordances inherited from frame",
    sh.get("ruleset", {}).get("navigation_affordances")
    == ["scroll-cue", "chevrons", "panel-dots", "arrow-keys", "swipe"],
)
check(
    "showcase-html style_guide.navigation inherited (frame layer)",
    "master-detail" in (sh.get("style_guide", {}).get("navigation") or ""),
)
check(
    "seals stripped from resolved contract",
    "seals" not in sh,
    "resolved contract should not carry the 'seals' meta-key",
)

# 3. A non-showcase slug defaults to layout=linear (nothing breaks).
pp = formats.resolve("pitch-pdf")
check("pitch-pdf defaults to layout=linear", pp.get("layout") == "linear")

# 4. Every existing slug still resolves cleanly (regression sweep).
for slug in formats.list_formats():
    try:
        r = formats.resolve(slug)
        check(f"{slug} resolves", isinstance(r, dict) and r.get("slug") == slug)
    except (FileNotFoundError, ValueError, SealedKeyConflict) as e:
        failures.append(f"{slug} resolve failed — {e}")

# 5. Sealed-key conflict raises hard.
#    Synthesise a tiny layer set and feed it directly to _merge_layers.
try:
    formats._merge_layers(
        [
            ("purpose", {"ruleset": {"structure": "linear"}, "seals": ["ruleset.structure"]}),
            ("export", {"ruleset": {"structure": "master-detail"}}),  # forbidden
        ]
    )
    failures.append("sealed-key conflict should have raised SealedKeyConflict")
except SealedKeyConflict as e:
    check(
        "sealed-key error mentions the offending key",
        "ruleset.structure" in str(e),
        str(e),
    )

# 6. Same-layer-can-seal-and-write is allowed.
try:
    out = formats._merge_layers(
        [
            ("layout", {"ruleset": {"structure": "master-detail"}, "seals": ["ruleset.structure"]}),
        ]
    )
    check("layer may write and seal its own key", out["ruleset"]["structure"] == "master-detail")
except SealedKeyConflict as e:
    failures.append(f"layer should be allowed to write and seal its own key: {e}")

# 7. Idempotent later writes still fail (force fork, no implicit pass-through).
try:
    formats._merge_layers(
        [
            ("layout", {"ruleset": {"structure": "master-detail"}, "seals": ["ruleset.structure"]}),
            ("slug", {"ruleset": {"structure": "master-detail"}}),  # same value, still forbidden
        ]
    )
    failures.append("even idempotent write to sealed key should raise (forces conscious fork)")
except SealedKeyConflict:
    pass

if failures:
    print(f"FAIL ({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(f"OK — {7} groups passed")
