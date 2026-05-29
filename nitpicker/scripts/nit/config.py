"""Global config resolution: the brand-agnostic baselines + review policy.

All configs are studios-level (``configs/`` at the repo root), shared across
studios and independent of brand slug. A brand may overlay its own
tone-of-voice; absent one, the default baseline is the standard the nitpicker
holds an asset to.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from . import BRAND_ROOT, DEFAULTS, DESIGN_CONTEXT, TESTS


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing config: {path}")
    with path.open() as f:
        return yaml.safe_load(f) or {}


def baseline_path(name: str) -> Path:
    return DEFAULTS / f"{name}.yml"


def list_baselines() -> list[str]:
    if not DEFAULTS.exists():
        return []
    return sorted(p.stem for p in DEFAULTS.glob("*.yml"))


def load_baseline(name: str) -> dict[str, Any]:
    return _load_yaml(baseline_path(name))


def review_policy() -> dict[str, Any]:
    """The aggregation policy; empty dict (sane defaults applied downstream) if absent."""
    p = baseline_path("review-policy")
    return _load_yaml(p) if p.exists() else {}


def brand_tov_path(brand: str | None) -> Path | None:
    """A brand's own tone-of-voice.md, if any — overlays the default baseline."""
    if not brand:
        return None
    for base in (BRAND_ROOT / brand, DESIGN_CONTEXT / brand / "brand"):
        p = base / "tone-of-voice.md"
        if p.exists():
            return p
    return None


def show(brand: str | None = None) -> str:
    """A readable summary of the resolved global config."""
    lines = ["# nitpicker config", "", f"configs root : {DEFAULTS.parent}", ""]
    lines.append("baselines (configs/default/):")
    for name in list_baselines() or ["(none)"]:
        lines.append(f"  - {name}")
    lines.append("")
    lines.append("tests (configs/tests/):")
    if TESTS.exists():
        for p in sorted(TESTS.glob("*.y*ml")):
            lines.append(f"  - {p.stem}")
    else:
        lines.append("  (none)")
    lines.append("")
    bp = brand_tov_path(brand)
    lines.append(
        f"brand voice overlay: {bp if bp else '(none — default baseline only)'}"
    )
    return "\n".join(lines) + "\n"
