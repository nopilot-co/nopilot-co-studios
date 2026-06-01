"""Render the design-token blocks that the static component libraries consume.

`components.css` uses `var(--ds-color-*)` etc.; `components.typ` reads `ds.*`.
This module turns a resolved token dict (see studio.tokens) into:

- a CSS `:root { --ds-... }` block (prepended to components.css at render), and
- a Typst `#let ds = (...)` block (prepended to components.typ at render).

Keeping the static component files token-driven means a brand re-skins the whole
component set with no edits to the component definitions.
"""

from __future__ import annotations

from typing import Any

_PT_TO_PX = {"2pt": "2px", "4pt": "4px", "8pt": "8px", "16pt": "16px", "32pt": "32px"}


def css_root(tokens: dict[str, Any]) -> str:
    """A `:root` block of `--ds-*` custom properties from the token set."""
    lines = [":root {"]
    for role, value in tokens["color"].items():
        lines.append(f"  --ds-color-{role.replace('_', '-')}: {value};")
    for size, value in tokens["space"].items():
        lines.append(f"  --ds-space-{size}: {_PT_TO_PX.get(value, value)};")
    for size, value in tokens["radius"].items():
        lines.append(f"  --ds-radius-{size}: {_PT_TO_PX.get(value, value)};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def typ_tokens(tokens: dict[str, Any]) -> str:
    """A Typst `#let ds = (...)` block from the token set (colours as rgb())."""
    color = ", ".join(
        f'{role}: rgb("{value}")' for role, value in tokens["color"].items()
    )
    space = ", ".join(f"{k}: {v}" for k, v in tokens["space"].items())
    radius = ", ".join(f"{k}: {v}" for k, v in tokens["radius"].items())
    return (
        "#let ds = (\n"
        f"  color: ({color}),\n"
        f"  space: ({space}),\n"
        f"  radius: ({radius}),\n"
        ")\n"
    )
