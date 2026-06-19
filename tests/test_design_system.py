#!/usr/bin/env python3
"""Per-session design-system selection (#21). Standalone; run:
    design/.venv/bin/python tests/test_design_system.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

from studio import tokens  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


# The catalog lists the shipped systems (and excludes the design.md index).
systems = tokens.list_design_systems()
check("lists systems", "design-yacht-club" in systems, str(systems))
check("excludes index", "design" not in systems, str(systems))

# A design system re-skins the token set vs the bare default.
default = tokens.resolve("___no_brand___")
yacht = tokens.resolve("___no_brand___", design_system="design-yacht-club")
check("ds changes tokens", yacht["color"] != default["color"], str(yacht["color"]))
# Yacht Club's neutral is its navy foundation, distinct from the default neutral.
check("ds neutral applied", yacht["color"]["neutral"] == "#0B2440", yacht["color"]["neutral"])
# on-primary hyphen -> on_primary key.
check("ds on_primary key", "on_primary" in yacht["color"], str(yacht["color"].keys()))

# Unknown system degrades silently to defaults (no crash).
unknown = tokens.resolve("___no_brand___", design_system="___nope___")
check("unknown ds -> defaults", unknown["color"]["neutral"] == default["color"]["neutral"])

# Brand colours still win over the design system (precedence).
# (Use a real brand if present; otherwise this is covered by the role_map logic.)
import studio.tokens as _t  # noqa: E402
sys_only = _t._design_system_tokens("design-yacht-club")
check("ds token parse", sys_only.get("color", {}).get("neutral") == "#0B2440", str(sys_only))

# on_surface (#27): readable body text on a `surface` fill, derived from the
# *resolved* surface so it stays legible for any brand × design-system pairing.
AA_BODY = 4.5  # WCAG AA contrast ratio for normal-size text.

check("on_surface present (default)", "on_surface" in default["color"], str(default["color"].keys()))
check(
    "default on_surface contrasts",
    tokens._contrast(default["color"]["on_surface"], default["color"]["surface"]) >= AA_BODY,
    f"{default['color']['on_surface']} on {default['color']['surface']}",
)
# Every shipped design-system — including the dark-surfaced ones (zed #1D1D1B,
# yacht-club / index #142F54) that motivated #27 — must yield legible panel text.
for _sys in tokens.list_design_systems():
    _tk = tokens.resolve("___no_brand___", design_system=_sys)
    _ratio = tokens._contrast(_tk["color"]["on_surface"], _tk["color"]["surface"])
    check(f"{_sys} on_surface contrasts", _ratio >= AA_BODY, f"ratio={_ratio:.2f}")
# The classic regression: a dark brand foreground layered onto a dark design-system
# surface would be invisible if on_surface just copied the brand ink. Derivation
# decouples it — on_surface must differ from a clashing dark foreground here.
_dark = tokens.resolve("___no_brand___", design_system="design-zed")
check(
    "dark surface gets light ink",
    tokens._relative_luminance(_dark["color"]["on_surface"]) > 0.5,
    _dark["color"]["on_surface"],
)
# on_surface flows through to both engines.
from studio import components  # noqa: E402

check("css emits on-surface", "--ds-color-on-surface" in components.css_root(default), "")
check("typst emits on_surface", "on_surface" in components.typ_tokens(default), "")

# px-based design-system lengths must become valid Typst lengths (Typst has no px).

typ = components.typ_tokens(yacht)
check("typst no px units", "px" not in typ, typ)
check("typst space is pt", "8pt" in typ, typ)
# CSS side coerces pt -> px.
css = components.css_root(tokens.resolve("___no_brand___"))  # defaults are pt
check("css no pt units", "pt;" not in css, css)

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: design-system selection")
