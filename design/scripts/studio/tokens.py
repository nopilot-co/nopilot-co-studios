"""Design tokens — the concrete values the component library renders with.

Slice-2 token resolution. A component references abstract tokens (e.g.
``ds.color.tertiary`` / ``var(--ds-color-tertiary)``); this module produces the
concrete value set for a brand by reading its ``_brand.yml`` colour/typography
and filling the remaining design-system tokens (tertiary accent, surface,
neutral, spacing, radius) from sensible defaults.

A later slice can source these from a per-session design-system selection
(``resources/design-systems/``); the shape returned here is the contract.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

from . import PLUGIN_ROOT
from . import brand as brand_mod

_DESIGN_SYSTEMS_DIR = PLUGIN_ROOT / "resources" / "design-systems"

# Brand-agnostic fallbacks (a calm, neutral system) for tokens a brand.yml
# doesn't express. Brand colours override the colour roles they map to.
_DEFAULTS: dict[str, Any] = {
    "color": {
        "primary": "#1A2433",
        "secondary": "#6B7280",
        "tertiary": "#C0392B",
        "neutral": "#0F1626",
        "surface": "#F1F3F6",
        "on_primary": "#FFFFFF",
        "foreground": "#1A2433",
        "background": "#FFFFFF",
    },
    "space": {"sm": "8pt", "md": "16pt", "lg": "32pt"},
    "radius": {"sm": "2pt", "md": "4pt", "lg": "8pt"},
}

# Pixel equivalents for CSS (Typst uses pt; CSS uses px/rem).
_PX = {"8pt": "8px", "16pt": "16px", "32pt": "32px", "2pt": "2px", "4pt": "4px", "8pt_r": "8px"}


def _brand_colors(slug: str) -> dict[str, str]:
    """Pull whatever colour roles a brand's _brand.yml declares (best-effort)."""
    try:
        path = brand_mod.brand_yml_path(slug)
        data = yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return {}
    color = data.get("color", {}) or {}
    # Posit brand.yml: color.primary / .secondary / .foreground / .background, and
    # a `palette` of named swatches. Map the common roles.
    out: dict[str, str] = {}
    for role in ("primary", "secondary", "foreground", "background"):
        v = color.get(role)
        if isinstance(v, str):
            out[role] = v
    palette = color.get("palette", {}) or {}
    # An accent for `tertiary` if the brand offers one.
    for key in ("accent", "tertiary", "highlight"):
        if isinstance(palette.get(key), str):
            out["tertiary"] = palette[key]
            break
    return out


def list_design_systems() -> list[str]:
    """Available design-system slugs (filenames in resources/design-systems/,
    excluding the `design.md` index)."""
    if not _DESIGN_SYSTEMS_DIR.exists():
        return []
    return sorted(
        p.stem for p in _DESIGN_SYSTEMS_DIR.glob("*.md") if p.stem != "design"
    )


def _design_system_tokens(slug: str) -> dict[str, Any]:
    """Parse a design-system file's YAML front-matter into the token shape
    ``{color, space, radius}``. Returns {} if the slug is unknown/malformed."""
    path = _DESIGN_SYSTEMS_DIR / f"{slug}.md"
    if not path.exists():
        return {}
    m = re.match(r"\A---\n(.*?)\n---", path.read_text(), re.DOTALL)
    if not m:
        return {}
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}
    out: dict[str, Any] = {"color": {}, "space": {}, "radius": {}}
    for role, val in (fm.get("colors") or {}).items():
        if isinstance(val, str):
            # design-system uses `on-primary`; tokens use `on_primary`.
            out["color"][role.replace("-", "_")] = val
    for k, v in (fm.get("spacing") or {}).items():
        out["space"][k] = str(v)
    for k, v in (fm.get("rounded") or {}).items():
        out["radius"][k] = str(v)
    return out


def resolve(slug: str, design_system: str | None = None) -> dict[str, Any]:
    """Concrete token set: ``{color:{...}, space:{...}, radius:{...}}``.

    Precedence (later wins): built-in defaults → the locked design-system (if any)
    → the brand's own ``_brand.yml`` colours. A brand is the most specific
    instantiation, so its declared colours override the chosen design-system.
    """
    import copy

    tokens = copy.deepcopy(_DEFAULTS)

    # Layer the design system over the defaults.
    if design_system:
        for group, vals in _design_system_tokens(design_system).items():
            tokens.setdefault(group, {}).update(vals)

    # Brand colours win on top.
    bc = _brand_colors(slug)
    role_map = {
        "primary": "primary",
        "secondary": "secondary",
        "foreground": "foreground",
        "background": "background",
        "tertiary": "tertiary",
    }
    for brand_role, tok in role_map.items():
        if bc.get(brand_role):
            tokens["color"][tok] = bc[brand_role]
    # Derive surface/neutral/on_primary if neither brand nor system spoke them.
    if "background" in bc:
        tokens["color"].setdefault("surface", bc["background"])
    return tokens
