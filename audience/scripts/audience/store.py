"""The shared reader-model store: ``~/context/studios/audience/<slug>/``.

Mechanics for the reusable reader model (parallel to the brand store). Scaffolds
the per-slug folder, reads/writes/validates ``_audience.yml`` against the schema,
lists and shows models. The *synthesis* judgment (what the profile says) is the
psychographic-profile skill's; this module only persists + validates.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from . import SCHEMAS, audience_root_base, load_yaml

AUDIENCE_FILE = "_audience.yml"
STATUSES = ("draft", "inferred", "validated")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug_dir(slug: str) -> Path:
    return audience_root_base() / slug


def audience_path(slug: str) -> Path:
    return slug_dir(slug) / AUDIENCE_FILE


def exists(slug: str) -> bool:
    return audience_path(slug).is_file()


# ----------------------------------------------------------------- validation
def _schema() -> dict:
    return json.loads((SCHEMAS / "audience.schema.json").read_text())


def validate(data: dict) -> list[str]:
    validator = Draft202012Validator(_schema())
    return [
        (".".join(str(p) for p in e.absolute_path) or "<root>") + ": " + e.message
        for e in sorted(
            validator.iter_errors(data), key=lambda e: list(e.absolute_path)
        )
    ]


def validate_slug(slug: str) -> list[str]:
    if not exists(slug):
        return [
            f"no reader model '{slug}' (run `audience persona new --audience {slug}`)"
        ]
    return validate(read(slug))


# ----------------------------------------------------------------- read / write
def read(slug: str) -> dict:
    p = audience_path(slug)
    if not p.is_file():
        raise FileNotFoundError(
            f"no reader model '{slug}' under {audience_root_base()} "
            "— run `audience persona new` first"
        )
    return load_yaml(p.read_text())


def write(slug: str, data: dict) -> None:
    slug_dir(slug).mkdir(parents=True, exist_ok=True)
    audience_path(slug).write_text(yaml.safe_dump(data, sort_keys=False))


# ----------------------------------------------------------------- scaffold
def scaffold(slug: str, *, persona: dict | None = None) -> dict:
    """Create the store folder + a draft ``_audience.yml`` (persona block from a
    supplied persona, else a stub). Idempotent: won't clobber an existing model."""
    if exists(slug):
        raise ValueError(
            f"reader model '{slug}' already exists at {audience_path(slug)}"
        )
    (slug_dir(slug) / "research").mkdir(parents=True, exist_ok=True)
    data = {
        "audience": slug,
        "name": (persona or {}).get("name", slug.replace("-", " ").title()),
        "status": "draft",
        "source": "user-supplied" if persona else "inferred",
        "persona": (persona or {}).get("persona") or {"role": ""},
        "need_state": {
            "needs": [{"id": "placeholder", "statement": "", "priority": "high"}]
        },
        "provenance": {"sources": [], "built": "", "built_by": "audience-studio"},
    }
    write(slug, data)
    return data


def mark_built(slug: str, *, status: str | None = None) -> dict:
    """Validate the full model, stamp provenance.built, optionally set status."""
    data = read(slug)
    errors = validate(data)
    if errors:
        raise ValueError("invalid reader model:\n  " + "\n  ".join(errors))
    data.setdefault("provenance", {})["built"] = _now()
    data["provenance"].setdefault("built_by", "audience-studio")
    if status is not None:
        if status not in STATUSES:
            raise ValueError(f"status must be one of {', '.join(STATUSES)}")
        data["status"] = status
    write(slug, data)
    return data


# ----------------------------------------------------------------- list / show
def list_models() -> list[str]:
    base = audience_root_base()
    if not base.exists():
        return []
    return sorted(p.name for p in base.iterdir() if (p / AUDIENCE_FILE).is_file())


def show(slug: str) -> str:
    return yaml.safe_dump(read(slug), sort_keys=False)
