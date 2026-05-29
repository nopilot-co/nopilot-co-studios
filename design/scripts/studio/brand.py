"""Brand loading, validation, listing.

A brand is a studios-level entity living at ~/context/studios/brand/<slug>/
(shared with the messaging studio). The single source of truth is _brand.yml
(Posit brand.yml standard). Brands created before elevation live at the legacy
~/context/studios/design/<slug>/brand/ and are still read transparently.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from . import BRAND_ROOT, CONTEXT_ROOT, SCHEMAS


def _legacy_brand_root(slug: str) -> Path:
    return CONTEXT_ROOT / slug / "brand"


def brand_root(slug: str) -> Path:
    """Resolve a brand's canonical folder.

    Prefers the shared studios-level store; falls back to the legacy design-owned
    location only when that's the one that exists. New brands are written to the
    shared store.
    """
    shared = BRAND_ROOT / slug
    if shared.exists():
        return shared
    legacy = _legacy_brand_root(slug)
    if legacy.exists():
        return legacy
    return shared


def brand_yml_path(slug: str) -> Path:
    return brand_root(slug) / "_brand.yml"


def load(slug: str) -> dict[str, Any]:
    p = brand_yml_path(slug)
    if not p.exists():
        raise FileNotFoundError(f"no _brand.yml at {p}")
    with p.open() as f:
        return yaml.safe_load(f) or {}


def list_brands() -> list[dict[str, str]]:
    """One row per brand: slug, primary color, headline font, last-rendered date.

    Unions the shared studios-level store with legacy design-owned brands; the
    shared store wins on slug collision.
    """
    brand_dirs: dict[str, Path] = {}
    if BRAND_ROOT.exists():
        for child in sorted(BRAND_ROOT.iterdir()):
            if child.is_dir() and (child / "_brand.yml").exists():
                brand_dirs.setdefault(child.name, child)
    if CONTEXT_ROOT.exists():
        for child in sorted(CONTEXT_ROOT.iterdir()):
            if child.is_dir() and (child / "brand" / "_brand.yml").exists():
                brand_dirs.setdefault(child.name, child / "brand")

    rows: list[dict[str, str]] = []
    for slug, brand_dir in sorted(brand_dirs.items()):
        try:
            data = yaml.safe_load((brand_dir / "_brand.yml").read_text()) or {}
        except yaml.YAMLError:
            continue
        primary = (data.get("color", {}) or {}).get("primary", "—")
        font = ((data.get("typography", {}) or {}).get("headings", {}) or {}).get(
            "family", "—"
        )
        rows.append(
            {
                "slug": slug,
                "primary": str(primary),
                "font": str(font),
                "last_rendered": _last_rendered(slug),
            }
        )
    return rows


def _last_rendered(slug: str) -> str:
    # Render sessions stay design-owned even after brand elevation.
    outputs = CONTEXT_ROOT / slug / "outputs"
    if not outputs.exists():
        return ""
    latest_mtime = 0.0
    for session in outputs.iterdir():
        version_json = session / "version.json"
        if version_json.exists():
            latest_mtime = max(latest_mtime, version_json.stat().st_mtime)
    if latest_mtime == 0:
        return ""
    from datetime import datetime, timezone

    return datetime.fromtimestamp(latest_mtime, tz=timezone.utc).strftime("%Y-%m-%d")


def validate(slug: str) -> list[str]:
    """Return list of validation errors (empty = valid)."""
    schema_path = SCHEMAS / "brand.schema.json"
    if not schema_path.exists():
        return ["brand.schema.json missing from plugin"]
    schema = json.loads(schema_path.read_text())
    try:
        data = load(slug)
    except FileNotFoundError as e:
        return [str(e)]
    validator = Draft202012Validator(schema)
    return [
        f"{'.'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in validator.iter_errors(data)
    ]


def show(slug: str) -> str:
    data = load(slug)
    return yaml.safe_dump(data, sort_keys=False, default_flow_style=False)
