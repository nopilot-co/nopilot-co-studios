"""Communication formats: purpose × channel, resolved by layered merge.

A format slug is ``<purpose>-<channel>`` (e.g. ``outreach-email``). Its contract
is the deep-merge of ``purposes/<purpose>.yml`` <- ``channels/<channel>.yml`` <-
the slug file's ``overrides``. Mirrors the design studio's formats module.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from . import FORMATS, SCHEMAS


def _purposes_dir() -> Path:
    return FORMATS / "purposes"


def _channels_dir() -> Path:
    return FORMATS / "channels"


def slug_path(slug: str) -> Path:
    return FORMATS / f"{slug}.yml"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing format file: {path}")
    with path.open() as f:
        return yaml.safe_load(f) or {}


def list_formats() -> list[str]:
    if not FORMATS.exists():
        return []
    return sorted(p.stem for p in FORMATS.glob("*.yml"))


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, val in (overlay or {}).items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = copy.deepcopy(val)
    return out


def resolve(slug: str) -> dict[str, Any]:
    """Resolve a format slug into its merged contract (purpose <- channel <- overrides)."""
    spec = _load_yaml(slug_path(slug))
    purpose = spec.get("extends")
    channel = spec.get("channel")
    if not purpose or not channel:
        raise ValueError(f"{slug}.yml must set both `extends` (purpose) and `channel`")

    base = _load_yaml(_purposes_dir() / f"{purpose}.yml")
    overlay = _load_yaml(_channels_dir() / f"{channel}.yml")
    purpose_name = base.get("name", purpose)
    channel_name = overlay.get("name", channel)

    merged = _deep_merge(base, overlay)
    merged = _deep_merge(merged, spec.get("overrides", {}))

    merged["slug"] = slug
    merged["purpose"] = purpose
    merged["channel"] = channel
    merged["purpose_name"] = purpose_name
    merged["channel_name"] = channel_name
    merged["name"] = f"{purpose_name} · {channel_name}"
    return merged


def validate(slug: str) -> list[str]:
    try:
        resolved = resolve(slug)
    except (FileNotFoundError, ValueError) as e:
        return [str(e)]
    schema_path = SCHEMAS / "format.schema.json"
    if not schema_path.exists():
        return ["format.schema.json missing from plugin"]
    schema = json.loads(schema_path.read_text())
    validator = Draft202012Validator(schema)
    return [
        f"{'.'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in validator.iter_errors(resolved)
    ]


def channel_targets(resolved: dict[str, Any]) -> list[str]:
    return list((resolved.get("render") or {}).get("target", []))


def show(slug: str) -> str:
    return yaml.safe_dump(resolve(slug), sort_keys=False, default_flow_style=False)
