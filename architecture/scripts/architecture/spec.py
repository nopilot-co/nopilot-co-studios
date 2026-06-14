"""Materialise the caller-supplied architecture spec.

Caller-supplied-JSON materialiser pattern (mirror of delivery's plan.py).
The model produces the structured spec; this module validates + materialises
via the store (which runs both the schema and the referential-integrity
invariants).
"""

from __future__ import annotations

import json
from pathlib import Path

from . import load_yaml
from .store import write_spec


def _load_spec_payload(path: Path) -> dict:
    text = path.read_text()
    if path.suffix in (".yml", ".yaml"):
        return load_yaml(text)
    return json.loads(text)


def materialise(slug: str, spec_json: Path) -> dict:
    payload = _load_spec_payload(spec_json)
    return write_spec(slug, payload)
