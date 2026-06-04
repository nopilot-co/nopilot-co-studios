"""Storyboard spec — load, validate, normalize.

The storyboard is the single source of truth for a render (issue #42). This
module is pure mechanics: read JSON, validate against the schema, and fill
declared defaults so downstream renderers (the board preview now; Remotion /
declarative SVG later) get a complete, normalized spec.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

from . import SCHEMAS

_SCHEMA_PATH = SCHEMAS / "storyboard.schema.json"

# Declared defaults the schema documents but JSON files may omit.
_GLOBAL_DEFAULTS = {"aspect": "16:9", "fps": 30, "captions": False}
_SCENE_DEFAULTS = {"transition": "cut"}
_LAYER_DEFAULTS = {"region": "center"}


def _schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text())


def validate(spec: dict[str, Any]) -> list[str]:
    """Return a list of human-readable validation errors ([] if valid)."""
    validator = jsonschema.Draft7Validator(_schema())
    errors = []
    for e in sorted(validator.iter_errors(spec), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errors.append(f"{loc}: {e.message}")
    return errors


def normalize(spec: dict[str, Any]) -> dict[str, Any]:
    """Fill declared defaults so renderers see a complete spec. Assumes valid."""
    out = json.loads(json.dumps(spec))  # deep copy
    g = out.setdefault("global", {})
    for k, v in _GLOBAL_DEFAULTS.items():
        g.setdefault(k, v)
    for scene in out.get("scenes", []):
        for k, v in _SCENE_DEFAULTS.items():
            scene.setdefault(k, v)
        for layer in scene.get("layers", []):
            for k, v in _LAYER_DEFAULTS.items():
                layer.setdefault(k, v)
    return out


def load(path: Path) -> dict[str, Any]:
    """Read + validate + normalize a storyboard file. Raises ValueError on
    invalid JSON or schema violations (with all errors listed)."""
    try:
        spec = json.loads(Path(path).read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"not valid JSON: {e}") from e
    errors = validate(spec)
    if errors:
        raise ValueError(
            "storyboard failed validation:\n  - " + "\n  - ".join(errors)
        )
    return normalize(spec)


def total_duration(spec: dict[str, Any]) -> float:
    """Sum of scene durations (seconds)."""
    return sum(float(s.get("duration", 0)) for s in spec.get("scenes", []))
