"""Runtime dependency detection for renderable formats.

Native tools (quarto, typst, libreoffice) can't be pip-installed or vendored, so
the studio *declares* what each export needs (`exports/<export>.yml` → `requires`)
and *detects* presence here. `studio doctor` reports status; render/qa fail with
actionable messages at the point of use. This module never installs anything.
"""

from __future__ import annotations

import shutil

from . import formats as formats_mod

INSTALL_HINTS = {
    "quarto": "brew install --cask quarto",
    "typst": "brew install typst",
    "libreoffice": "brew install --cask libreoffice",
}


def have(tool: str) -> bool:
    """Is the tool on PATH? (libreoffice ships as `soffice` on some systems.)"""
    if tool == "libreoffice":
        return bool(shutil.which("libreoffice") or shutil.which("soffice"))
    return bool(shutil.which(tool))


def required_tools(resolved: dict) -> dict[str, list[str]]:
    req = resolved.get("requires") or {}
    return {"render": list(req.get("render", [])), "qa": list(req.get("qa", []))}


def missing_for(resolved: dict, phase: str) -> list[str]:
    return [t for t in required_tools(resolved).get(phase, []) if not have(t)]


def format_availability(slug: str) -> dict:
    r = formats_mod.resolve(slug)
    renderable = formats_mod.is_renderable(r)
    render_missing = missing_for(r, "render") if renderable else []
    return {
        "slug": slug,
        "renderable": renderable,
        "render_ready": renderable and not render_missing,
        "render_missing": render_missing,
        "qa_missing": missing_for(r, "qa") if renderable else [],
    }


def doctor() -> dict:
    """Tool presence + per-format render/QA readiness across all defined formats."""
    tools: set[str] = set()
    for slug in formats_mod.list_formats():
        try:
            r = formats_mod.resolve(slug)
        except (FileNotFoundError, ValueError):
            continue
        req = required_tools(r)
        tools.update(req["render"])
        tools.update(req["qa"])
    return {
        "tools": {t: have(t) for t in sorted(tools)},
        "formats": [format_availability(s) for s in formats_mod.list_formats()],
    }
