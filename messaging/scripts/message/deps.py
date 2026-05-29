"""Runtime dependency detection for channel render targets.

Most messaging channels are text-first and need no native tools. Some targets
do — HTML email is compiled with MJML (a Node tool). The studio *declares* what
each channel's targets need (`channels/<channel>.yml → requires`) and *detects*
presence here. `message doctor` reports status; `render` skips tool-gated targets
with an actionable hint when the tool is absent. This module never installs.
"""

from __future__ import annotations

import shutil

from . import formats as formats_mod

INSTALL_HINTS = {
    "mjml": "npm install -g mjml",
}


def have(tool: str) -> bool:
    """Is the tool on PATH?"""
    return bool(shutil.which(tool))


def required_render_tools(resolved: dict) -> list[str]:
    return list((resolved.get("requires") or {}).get("render", []))


def missing_render_tools(resolved: dict) -> list[str]:
    return [t for t in required_render_tools(resolved) if not have(t)]


def format_availability(slug: str) -> dict:
    r = formats_mod.resolve(slug)
    missing = missing_render_tools(r)
    return {
        "slug": slug,
        "targets": formats_mod.channel_targets(r),
        "render_missing": missing,
        "render_ready": not missing,
    }


def doctor() -> dict:
    """Tool presence + per-format render readiness across all defined formats."""
    tools: set[str] = set()
    for slug in formats_mod.list_formats():
        try:
            r = formats_mod.resolve(slug)
        except (FileNotFoundError, ValueError):
            continue
        tools.update(required_render_tools(r))
    return {
        "tools": {t: have(t) for t in sorted(tools)},
        "formats": [format_availability(s) for s in formats_mod.list_formats()],
    }
