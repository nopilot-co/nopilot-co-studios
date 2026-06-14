"""Runtime dependency detection for renderable formats.

Native tools (quarto, typst, libreoffice) can't be pip-installed or vendored, so
the studio *declares* what each export needs (`exports/<export>.yml` → `requires`)
and *detects* presence here. `studio doctor` reports status; render/qa fail with
actionable messages at the point of use. This module never installs anything.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from . import formats as formats_mod

# `html-raster` is a capability token, not a PATH binary: HTML/RevealJS QA needs
# a headless browser to rasterize a page (see `have`). Satisfied by Playwright's
# bundled Chromium or by wkhtmltoimage.
INSTALL_HINTS = {
    "quarto": "brew install --cask quarto",
    "typst": "brew install typst",
    "libreoffice": "brew install --cask libreoffice",
    "html-raster": "uv sync --extra playwright && playwright install chromium  (or: brew install wkhtmltopdf)",
}


def html_rasterizer() -> str | None:
    """Which HTML rasterizer is available for QA capture, if any.

    Returns ``"playwright"``, ``"wkhtmltoimage"``, or ``None``. Checked without
    launching a browser — Playwright counts only if its Chromium is actually
    installed (the package alone is not enough).
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            exe = p.chromium.executable_path
        if exe and Path(exe).exists():
            return "playwright"
    except Exception:
        pass
    if shutil.which("wkhtmltoimage"):
        return "wkhtmltoimage"
    return None


def have(tool: str) -> bool:
    """Is the dependency available? (libreoffice ships as `soffice` on some
    systems; `html-raster` is a capability satisfied by a headless browser.)"""
    if tool == "libreoffice":
        return bool(shutil.which("libreoffice") or shutil.which("soffice"))
    if tool == "html-raster":
        return html_rasterizer() is not None
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
