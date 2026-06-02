"""Render the design-token blocks that the static component libraries consume.

`components.css` uses `var(--ds-color-*)` etc.; `components.typ` reads `ds.*`.
This module turns a resolved token dict (see studio.tokens) into:

- a CSS `:root { --ds-... }` block (prepended to components.css at render), and
- a Typst `#let ds = (...)` block (prepended to components.typ at render).

Keeping the static component files token-driven means a brand re-skins the whole
component set with no edits to the component definitions.
"""

from __future__ import annotations

import re
from typing import Any

# Typst has no `px` unit. Tokens may arrive in pt (defaults) or px (some design
# systems); normalise to a Typst-valid length for the `#let ds` block.
_LEN_RE = re.compile(r"^([\d.]+)\s*(px|pt|mm|cm|em|in)?$")


def _to_typst_len(value: str) -> str:
    """Coerce a CSS/px length to a Typst length (px -> pt 1:1; pass pt/em/etc.)."""
    m = _LEN_RE.match(str(value).strip())
    if not m:
        return str(value)
    num, unit = m.group(1), (m.group(2) or "pt")
    return f"{num}pt" if unit == "px" else f"{num}{unit}"


def _to_css_len(value: str) -> str:
    """Coerce a length to a CSS unit (pt -> px 1:1; pass px/rem/etc.)."""
    m = _LEN_RE.match(str(value).strip())
    if not m:
        return str(value)
    num, unit = m.group(1), (m.group(2) or "px")
    return f"{num}px" if unit == "pt" else f"{num}{unit}"


def css_root(tokens: dict[str, Any]) -> str:
    """A `:root` block of `--ds-*` custom properties from the token set."""
    lines = [":root {"]
    for role, value in tokens["color"].items():
        lines.append(f"  --ds-color-{role.replace('_', '-')}: {value};")
    for size, value in tokens["space"].items():
        lines.append(f"  --ds-space-{size}: {_to_css_len(value)};")
    for size, value in tokens["radius"].items():
        lines.append(f"  --ds-radius-{size}: {_to_css_len(value)};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def typ_tokens(tokens: dict[str, Any]) -> str:
    """A Typst `#let ds = (...)` block from the token set (colours as rgb())."""
    color = ", ".join(
        f'{role}: rgb("{value}")' for role, value in tokens["color"].items()
    )
    space = ", ".join(f"{k}: {_to_typst_len(v)}" for k, v in tokens["space"].items())
    radius = ", ".join(f"{k}: {_to_typst_len(v)}" for k, v in tokens["radius"].items())
    return (
        "#let ds = (\n"
        f"  color: ({color}),\n"
        f"  space: ({space}),\n"
        f"  radius: ({radius}),\n"
        ")\n"
    )
