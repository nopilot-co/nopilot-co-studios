#!/usr/bin/env python3
"""Render-engine foundation (slice 2): token resolution + the CSS/Typst token
blocks the static component libraries consume, and the component library shape.
Standalone; run: design/.venv/bin/python tests/test_components.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

from studio import components, tokens  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


# Unknown brand -> defaults (deterministic, no external brand store needed).
tok = tokens.resolve("___no_such_brand___")
check("token groups", set(tok) >= {"color", "space", "radius"}, str(tok.keys()))
check(
    "token colour roles",
    set(tok["color"])
    >= {"primary", "secondary", "tertiary", "neutral", "surface", "on_primary"},
    str(tok["color"].keys()),
)

css = components.css_root(tok)
check("css :root", css.strip().startswith(":root {"))
check("css token var", "--ds-color-tertiary:" in css, css)
check("css px conversion", "--ds-space-md: 16px;" in css, css)

typ = components.typ_tokens(tok)
check("typ ds binding", typ.startswith("#let ds = ("), typ)
check("typ rgb colour", 'tertiary: rgb("' in typ, typ)
check("typ underscore key", "on_primary: rgb(" in typ, typ)

# The static component library defines the bridged functions.
comp_typ = (REPO / "design/templates/components/components.typ").read_text()
for fn in (
    "c_pullquote", "c_highlight", "c_ds_callout", "c_panel", "c_stat_panel",
    "c_cta", "c_precis", "c_section", "c_cover", "c_bio", "c_byline",
):
    check(f"typ defines {fn}", f"#let {fn}(" in comp_typ, fn)

comp_css = (REPO / "design/templates/components/components.css").read_text()
for cls in (".pullquote", ".highlight", ".ds-callout", ".panel", ".stat-panel", ".cta"):
    check(f"css defines {cls}", cls + " " in comp_css or cls + "," in comp_css, cls)

# The Lua bridge only acts on typst and lists the component classes.
comp_lua = (REPO / "design/templates/components/components.lua").read_text()
check("lua guards typst", 'is_format("typst")' in comp_lua)
check("lua normalizes hyphens", 'gsub("-", "_")' in comp_lua)

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: render-engine foundation (tokens + components)")
