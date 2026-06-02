"""Structured-diagram engine (slice 4a).

Expands `::: <diagram>` fenced divs whose body is YAML into the render engine for
the session's single locked export — Mermaid for HTML, Typst `fletcher` for PDF —
brand-tokenized on both sides. Runs in render.py's preprocess step, before Quarto.

Diagram classes: flow, timeline, process, hierarchy, org.
Unknown/malformed YAML degrades to a visible panel (never crashes the render).
"""

from __future__ import annotations

import re
from typing import Any

import yaml

# A fenced div opening `::: name` or `::: {.name}`, body, then a closing `:::`.
_DIV_RE = re.compile(
    r"^:::+\s*(?:\{\.)?(?P<name>[a-z][a-z0-9-]*)\}?\s*\n"
    r"(?P<body>.*?)\n"
    r"^:::+\s*$",
    re.MULTILINE | re.DOTALL,
)

DIAGRAM_CLASSES = {"flow", "timeline", "process", "hierarchy", "org"}


def expand(markdown: str, export: str, tokens: dict[str, Any]) -> str:
    """Replace every diagram div with its engine block for `export` (html|pdf).

    Other exports (pptx/revealjs) and non-diagram divs pass through unchanged.
    """
    if export not in ("html", "pdf"):
        return markdown

    def _sub(m: re.Match) -> str:
        name = m.group("name")
        if name not in DIAGRAM_CLASSES:
            return m.group(0)  # not a diagram — leave for the Lua bridge / Quarto
        try:
            spec = yaml.safe_load(m.group("body")) or {}
            if not isinstance(spec, dict):
                raise ValueError("diagram body must be a YAML mapping")
            return _render(name, spec, export, tokens)
        except Exception as e:  # noqa: BLE001 — never crash a render on bad input
            return _fallback(name, m.group("body"), str(e))

    return _DIV_RE.sub(_sub, markdown)


def _render(name: str, spec: dict, export: str, tokens: dict) -> str:
    raise NotImplementedError  # filled in Task 2+


def _fallback(name: str, body: str, err: str) -> str:
    return (
        f"::: panel\n**[diagram '{name}' could not render: {err}]**\n\n"
        f"```\n{body.strip()}\n```\n:::\n"
    )
