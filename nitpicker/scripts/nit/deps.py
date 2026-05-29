"""Runtime dependency detection for asset capture.

The nitpicker *captures* the target so the visual-qa skill has pixels to judge.
Different target kinds need different tools; this module detects what's present
and `nit doctor` reports it. Text-only targets (md/txt) need nothing. This
module never installs — it declares, detects, and lets capture degrade with an
actionable hint.
"""

from __future__ import annotations

import importlib.util
import shutil

# tool -> (how to detect, install hint). "py:<module>" checks an importable
# module; anything else is looked up on PATH.
TOOLS = {
    "pypdfium2": ("py:pypdfium2", "pip install pypdfium2  (PDF page capture)"),
    "playwright": (
        "py:playwright",
        "pip install playwright && playwright install chromium  (URL/HTML capture)",
    ),
    "libreoffice": (
        "bin:libreoffice",
        "brew install --cask libreoffice  (PPTX capture)",
    ),
    "wkhtmltoimage": (
        "bin:wkhtmltoimage",
        "brew install --cask wkhtmltopdf  (fallback HTML capture)",
    ),
}

INSTALL_HINTS = {name: hint for name, (_, hint) in TOOLS.items()}


def have(tool: str) -> bool:
    detect = TOOLS.get(tool, (f"bin:{tool}", ""))[0]
    kind, _, ref = detect.partition(":")
    if kind == "py":
        return importlib.util.find_spec(ref) is not None
    # libreoffice ships its binary as `soffice` on many systems.
    if ref == "libreoffice":
        return bool(shutil.which("libreoffice") or shutil.which("soffice"))
    return bool(shutil.which(ref))


def doctor() -> dict:
    """Tool presence for every capture dependency."""
    return {"tools": {name: have(name) for name in TOOLS}}
