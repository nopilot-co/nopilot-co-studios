"""data-viz engine (#20).

Renders `::: chart` fenced divs (YAML body) to brand-styled SVG via matplotlib —
the SAME SVG embedded inline in HTML and placed with Typst `#image()` in PDF, so
the two targets are identical (true parity, no per-engine divergence).

matplotlib is imported LAZILY so the module loads even when it's absent; in that
case each chart degrades to a visible fallback panel (the render never crashes).

Runs in render.py's preprocess step, after diagrams.expand.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

# Same fenced-div grammar as diagrams.py.
_DIV_RE = re.compile(
    r"^:::+\s*(?:\{\.)?(?P<name>[a-z][a-z0-9-]*)\}?\s*\n"
    r"(?P<body>.*?)\n"
    r"^:::+\s*$",
    re.MULTILINE | re.DOTALL,
)

CHART_CLASS = "chart"
CHART_TYPES = {"bar", "line", "pie", "scatter", "area"}


def _series(spec: dict) -> list[dict]:
    """Normalise to a list of {name, y} series. Supports single `y` or `series`."""
    if spec.get("series"):
        out = []
        for s in spec["series"]:
            out.append(
                {
                    "name": str(s.get("name", "")),
                    "y": [float(v) for v in s.get("y", [])],
                }
            )
        return out
    if spec.get("y") is not None:
        return [{"name": str(spec.get("name", "")), "y": [float(v) for v in spec["y"]]}]
    return []


def _palette(tokens: dict) -> list[str]:
    c = tokens["color"]
    return [c["tertiary"], c["primary"], c["secondary"], c["neutral"], c["surface"]]


def render_svg(spec: dict, tokens: dict) -> str:
    """Render one chart spec to an SVG string. Raises on bad spec (caller catches)."""
    import matplotlib

    matplotlib.use("svg")
    import io

    import matplotlib.pyplot as plt

    ctype = spec.get("type", "bar")
    if ctype not in CHART_TYPES:
        raise ValueError(f"unknown chart type '{ctype}'")

    c = tokens["color"]
    palette = _palette(tokens)
    fig, ax = plt.subplots(figsize=(6, 3.4))
    x = [str(v) for v in (spec.get("x") or spec.get("labels") or [])]
    series = _series(spec)

    if ctype == "pie":
        values = [float(v) for v in (spec.get("values") or spec.get("y") or [])]
        labels = x or [str(i) for i in range(len(values))]
        ax.pie(values, labels=labels, colors=palette, textprops={"color": c["primary"]})
        ax.set_aspect("equal")
    elif ctype == "bar":
        n = len(series)
        idx = range(len(x))
        width = 0.8 / max(n, 1)
        for si, s in enumerate(series):
            offs = [i + si * width - 0.4 + width / 2 for i in idx]
            ax.bar(
                offs,
                s["y"],
                width=width,
                color=palette[si % len(palette)],
                label=s["name"] or None,
            )
        ax.set_xticks(list(idx))
        ax.set_xticklabels(x)
    elif ctype in ("line", "area"):
        for si, s in enumerate(series):
            col = palette[si % len(palette)]
            ax.plot(range(len(s["y"])), s["y"], color=col, label=s["name"] or None)
            if ctype == "area":
                ax.fill_between(range(len(s["y"])), s["y"], color=col, alpha=0.25)
        ax.set_xticks(range(len(x)))
        ax.set_xticklabels(x)
    elif ctype == "scatter":
        for si, s in enumerate(series):
            ax.scatter(
                range(len(s["y"])),
                s["y"],
                color=palette[si % len(palette)],
                label=s["name"] or None,
            )
        ax.set_xticks(range(len(x)))
        ax.set_xticklabels(x)

    if spec.get("title"):
        ax.set_title(str(spec["title"]), color=c["primary"])
    ax.tick_params(colors=c["secondary"])
    for sp in ("top", "right"):
        if sp in ax.spines:
            ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        if sp in ax.spines:
            ax.spines[sp].set_color(c["secondary"])
    if any(s["name"] for s in series) and ctype != "pie":
        ax.legend(frameon=False, labelcolor=c["primary"])
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    fig.tight_layout()

    buf = io.StringIO()
    fig.savefig(buf, format="svg")
    plt.close(fig)
    return buf.getvalue()


def _fallback(body: str, err: str) -> str:
    return (
        f"::: panel\n**[chart could not render: {err}]**\n\n"
        f"```\n{body.strip()}\n```\n:::\n"
    )


def expand(markdown: str, export: str, tokens: dict[str, Any], out_dir: Path) -> str:
    """Replace every `::: chart` div with an image of its rendered SVG, for `export`.

    HTML: a markdown image referencing the written SVG (Quarto inlines it).
    PDF:  a Typst `#image()` raw block (keeps the SVG as vector).
    Other exports / non-chart divs pass through unchanged.
    """
    if export not in ("html", "pdf"):
        return markdown

    counter = [0]

    def _sub(m: re.Match) -> str:
        if m.group("name") != CHART_CLASS:
            return m.group(0)
        try:
            spec = yaml.safe_load(m.group("body")) or {}
            if not isinstance(spec, dict):
                raise ValueError("chart body must be a YAML mapping")
            svg = render_svg(spec, tokens)
        except Exception as e:  # noqa: BLE001 — never crash a render
            return _fallback(m.group("body"), str(e))
        counter[0] += 1
        name = f"_chart-{counter[0]}.svg"
        (out_dir / name).write_text(svg, encoding="utf-8")
        if export == "pdf":
            return f'```{{=typst}}\n#image("{name}", width: 100%)\n```\n'
        return f"![]({name})\n"

    return _DIV_RE.sub(_sub, markdown)
