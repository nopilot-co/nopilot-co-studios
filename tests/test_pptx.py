#!/usr/bin/env python3
"""Editable PPTX engine (#19). Standalone; run:
design/.venv/bin/python tests/test_pptx.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design" / "scripts"))

from studio import pptx_render  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{(' — ' + detail) if detail else ''}")


TOK = {
    "color": {
        "neutral": "#142F54",
        "surface": "#21456b",
        "tertiary": "#B14B33",
        "on_primary": "#FFFFFF",
        "secondary": "#6B7280",
        "primary": "#2A3548",
    },
    "space": {"sm": "8pt", "md": "16pt", "lg": "32pt"},
    "radius": {"sm": "2pt", "md": "4pt", "lg": "8pt"},
}

# split_slides: headings and cover/section blocks start new slides.
md = (
    "::: cover-slide\n# Q3 Strategy\nSubtitle here.\n:::\n\n"
    "## Context\nA point about the market.\n\n"
    "## Plan\n- First\n- Second\n"
)
slides = pptx_render.split_slides(md)
check("split: 3 slides", len(slides) == 3, str(len(slides)))
check("split: first is cover", slides[0]["kind"] == "cover-slide", str(slides[0]))

# build_pptx writes a real .pptx with the right slide count.
with tempfile.TemporaryDirectory() as td:
    out = Path(td) / "deck.pptx"
    pptx_render.build_pptx(md, TOK, out)
    check("pptx written", out.exists() and out.stat().st_size > 0)
    from pptx import Presentation

    prs = Presentation(str(out))
    check("pptx slide count", len(list(prs.slides)) == 3, str(len(list(prs.slides))))

if failures:
    print(f"FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("PASS: pptx (tier 1)")
