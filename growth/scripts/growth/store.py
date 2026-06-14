"""Per-engagement growth store."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from . import SCHEMAS, growth_root, load_yaml

LEADS_FILE = "_leads.yml"
MARKET_FILE = "_market.yml"
VERSION_FILE = "version.json"
STATUSES = ("draft", "approved", "archived")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _schema(name: str) -> dict:
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text())


def _validate(kind: str, data: dict) -> list[str]:
    validator = Draft202012Validator(_schema(kind))
    return [
        (".".join(str(p) for p in e.absolute_path) or "<root>") + ": " + e.message
        for e in sorted(
            validator.iter_errors(data), key=lambda e: list(e.absolute_path)
        )
    ]


def engagement_dir(slug: str) -> Path:
    return growth_root() / slug


def leads_path(slug: str) -> Path:
    return engagement_dir(slug) / LEADS_FILE


def market_path(slug: str) -> Path:
    return engagement_dir(slug) / MARKET_FILE


def version_path(slug: str) -> Path:
    return engagement_dir(slug) / VERSION_FILE


def engagement_exists(slug: str) -> bool:
    return version_path(slug).is_file()


def scaffold(slug: str) -> dict:
    if engagement_exists(slug):
        raise ValueError(
            f"engagement '{slug}' already exists at {engagement_dir(slug)}"
        )
    engagement_dir(slug).mkdir(parents=True, exist_ok=True)
    data = {
        "engagement": slug,
        "status": "draft",
        "created": _now(),
        "current": "0.0.0",
        "history": [],
    }
    write_version(slug, data)
    return data


def read_leads(slug: str) -> dict:
    if not leads_path(slug).is_file():
        raise FileNotFoundError(f"no leads for '{slug}'")
    return load_yaml(leads_path(slug).read_text())


def write_leads(slug: str, data: dict) -> dict:
    errs = _validate("leads", data)
    if errs:
        raise ValueError("invalid leads:\n  " + "\n  ".join(errs))
    if not engagement_exists(slug):
        raise FileNotFoundError(
            f"no engagement '{slug}' — run `growth leads new --engagement {slug}`"
        )
    data = dict(data)
    data["engagement"] = slug
    data.setdefault("provenance", {})["materialised"] = _now()
    data["provenance"].setdefault("materialised_by", "growth-studio")
    leads_path(slug).write_text(yaml.safe_dump(data, sort_keys=False))
    return data


def read_market(slug: str) -> dict:
    if not market_path(slug).is_file():
        raise FileNotFoundError(f"no market map for '{slug}'")
    return load_yaml(market_path(slug).read_text())


def write_market(slug: str, data: dict) -> dict:
    errs = _validate("market", data)
    if errs:
        raise ValueError("invalid market map:\n  " + "\n  ".join(errs))
    if not engagement_exists(slug):
        raise FileNotFoundError(
            f"no engagement '{slug}' — run `growth market new --engagement {slug}`"
        )
    data = dict(data)
    data["engagement"] = slug
    data.setdefault("provenance", {})["materialised"] = _now()
    data["provenance"].setdefault("materialised_by", "growth-studio")
    market_path(slug).write_text(yaml.safe_dump(data, sort_keys=False))
    return data


def read_version(slug: str) -> dict:
    return json.loads(version_path(slug).read_text())


def write_version(slug: str, data: dict) -> None:
    version_path(slug).parent.mkdir(parents=True, exist_ok=True)
    version_path(slug).write_text(json.dumps(data, indent=2) + "\n")


def bump(slug: str, *, level: str = "patch") -> str:
    data = read_version(slug)
    cur = data.get("current") or "0.0.0"
    major, minor, patch = (int(x) for x in cur.split("."))
    if level == "major":
        major, minor, patch = major + 1, 0, 0
    elif level == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    new_ver = f"{major}.{minor}.{patch}"
    data.setdefault("history", []).append({"version": new_ver, "at": _now()})
    data["current"] = new_ver
    write_version(slug, data)
    return new_ver


def set_status(slug: str, status: str) -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of: {', '.join(STATUSES)}")
    data = read_version(slug)
    data["status"] = status
    write_version(slug, data)
    return data


def list_engagements() -> list[str]:
    root = growth_root()
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if (p / VERSION_FILE).is_file())
