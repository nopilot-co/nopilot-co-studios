"""Token resolution for the motion studio.

Two token families:

- **Visual** (colour/type) — REUSED from the design studio's token layer when its
  package is importable, so motion and static assets stay visually identical.
  Falls back to a neutral default palette when design-studio isn't installed.
- **Motion** (easing / duration / transition / pacing) — resolved here, layered
  ``defaults → motion-system``.

(Future: a shared ``studios-core`` package folds the visual side in directly so
the soft-import below isn't needed. Tracked against the studios refactor.)
"""

from __future__ import annotations

import re
from typing import Any

import yaml

from . import RESOURCES

_MOTION_SYSTEMS_DIR = RESOURCES / "motion-systems"

# Neutral fallback palette (matches the design studio's defaults) for when the
# design-studio token package isn't importable.
_COLOR_DEFAULTS: dict[str, str] = {
    "primary": "#1A2433",
    "secondary": "#6B7280",
    "tertiary": "#C0392B",
    "neutral": "#0F1626",
    "surface": "#F1F3F6",
    "on_primary": "#FFFFFF",
    "foreground": "#1A2433",
    "background": "#FFFFFF",
}

_MOTION_DEFAULTS: dict[str, Any] = {
    "easing": {
        "standard": "cubic-bezier(0.4, 0.0, 0.2, 1)",
        "decelerate": "cubic-bezier(0.0, 0.0, 0.2, 1)",
        "accelerate": "cubic-bezier(0.4, 0.0, 1, 1)",
    },
    "duration": {"fast": 200, "base": 400, "slow": 800},
    "transitions": ["cut", "fade", "slide", "wipe"],
    "pacing": {"default_scene_seconds": 4, "words_per_minute": 150},
}


def _design_colors(brand_slug: str | None) -> dict[str, str]:
    """Brand colour roles via the design studio's resolver, if available."""
    if not brand_slug:
        return {}
    try:
        from studio import tokens as design_tokens  # type: ignore
    except Exception:
        return {}
    try:
        return dict(design_tokens.resolve(brand_slug).get("color", {}))
    except Exception:
        return {}


def list_motion_systems() -> list[str]:
    if not _MOTION_SYSTEMS_DIR.exists():
        return []
    return sorted(p.stem for p in _MOTION_SYSTEMS_DIR.glob("*.md"))


def _motion_system_tokens(slug: str) -> dict[str, Any]:
    """Parse a motion-system file's YAML front-matter into motion tokens."""
    path = _MOTION_SYSTEMS_DIR / f"{slug}.md"
    if not path.exists():
        return {}
    m = re.match(r"\A---\n(.*?)\n---", path.read_text(), re.DOTALL)
    if not m:
        return {}
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}
    out: dict[str, Any] = {}
    for key in ("easing", "duration", "transitions", "pacing"):
        if key in fm:
            out[key] = fm[key]
    return out


def resolve(brand: str | None = None, motion_system: str | None = None) -> dict[str, Any]:
    """Concrete token set: ``{color: {...}, motion: {...}}``.

    Colour precedence: defaults → design-studio brand resolution (if available).
    Motion precedence: defaults → motion-system.
    """
    import copy

    color = dict(_COLOR_DEFAULTS)
    color.update(_design_colors(brand))

    motion = copy.deepcopy(_MOTION_DEFAULTS)
    if motion_system:
        for k, v in _motion_system_tokens(motion_system).items():
            if isinstance(v, dict):
                motion.setdefault(k, {}).update(v)
            else:
                motion[k] = v

    return {"color": color, "motion": motion}
