"""Brand voice resolution — shared with the design studio.

Brand is a studios-level entity (SPEC §6, §12.1 resolved). A message is written
in a brand's voice, read from the shared brand store first, then the legacy
design-owned location, then the canonical default in design/resources/brand-voice/.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import BRAND_ROOT, BRAND_VOICE_DEFAULT, DESIGN_CONTEXT


def voice_path(brand: str | None) -> Path | None:
    if brand:
        # Shared studios-level store first, then the legacy design-owned location.
        for base in (BRAND_ROOT / brand, DESIGN_CONTEXT / brand / "brand"):
            p = base / "tone-of-voice.md"
            if p.exists():
                return p
    return BRAND_VOICE_DEFAULT if BRAND_VOICE_DEFAULT.exists() else None


def forbidden_words(brand: str | None) -> list[str]:
    """Best-effort: quoted terms under a Forbidden/Avoid section of the voice file."""
    p = voice_path(brand)
    if not p or not p.exists():
        return []
    out: list[str] = []
    in_section = False
    for line in p.read_text().splitlines():
        if re.match(r"^#+\s", line):  # a heading boundary
            in_section = bool(re.search(r"(avoid|forbidden)", line, re.I))
            continue
        if re.match(r"^\s*(avoid|forbidden)\s*:", line, re.I):
            in_section = True
            continue
        if in_section:
            out.extend(re.findall(r'"([^"]+)"', line))
    return out
