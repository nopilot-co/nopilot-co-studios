"""Asset library: design/formats/assets/<slug>.yml — a normalized, tokenized
catalog of asset types (pullquote, cover, data-table, …) referenced by formats.

Slice 1 owns the contracts + validation only; rendering is later slices.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from . import FORMATS, SCHEMAS

ASSETS_DIR = FORMATS / "assets"


def assets_dir(base: Path | None = None) -> Path:
    return base if base is not None else ASSETS_DIR


def list_assets(base: Path | None = None) -> list[str]:
    d = assets_dir(base)
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.yml"))


def load_asset(base: Path | None, slug: str) -> dict[str, Any]:
    path = assets_dir(base) / f"{slug}.yml"
    if not path.exists():
        raise FileNotFoundError(f"no asset '{slug}' at {path}")
    return yaml.safe_load(path.read_text()) or {}


def _schema() -> dict[str, Any]:
    return json.loads((SCHEMAS / "asset.schema.json").read_text())


def validate_asset(base: Path | None, slug: str) -> list[str]:
    try:
        data = load_asset(base, slug)
    except FileNotFoundError as e:
        return [str(e)]
    validator = Draft202012Validator(_schema())
    return [
        ("/".join(str(p) for p in e.path) + ": " + e.message) if e.path else e.message
        for e in sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    ]


def supports_export(asset: dict[str, Any], export: str) -> bool:
    return export in (asset.get("exports") or [])
