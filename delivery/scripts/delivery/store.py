"""Per-engagement delivery store.

Mechanics for ``~/context/studios/delivery/<engagement>/``: scaffolding,
schema validation, plan + RAID I/O, version stamps. No judgment.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from . import SCHEMAS, delivery_root, load_yaml

PLAN_FILE = "_plan.yml"
RAID_FILE = "raid.yml"
VERSION_FILE = "version.json"
BRIEF_FILE = "brief.md"
STATUSES = ("draft", "approved", "active", "delivered")


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


# ----------------------------------------------------------------- engagement dirs


def engagement_dir(slug: str) -> Path:
    return delivery_root() / slug


def plan_path(slug: str) -> Path:
    return engagement_dir(slug) / PLAN_FILE


def raid_path(slug: str) -> Path:
    return engagement_dir(slug) / RAID_FILE


def version_path(slug: str) -> Path:
    return engagement_dir(slug) / VERSION_FILE


def brief_path(slug: str) -> Path:
    return engagement_dir(slug) / BRIEF_FILE


def engagement_exists(slug: str) -> bool:
    return version_path(slug).is_file()


# ----------------------------------------------------------------- scaffold


def scaffold(slug: str, *, brief: Path | None = None) -> dict:
    """Create the engagement store with an empty RAID + version stamp.
    Idempotent on the dir; raises if version.json already exists."""
    if engagement_exists(slug):
        raise ValueError(
            f"engagement '{slug}' already exists at {engagement_dir(slug)}"
        )
    engagement_dir(slug).mkdir(parents=True, exist_ok=True)
    if brief and brief.is_file():
        shutil.copy2(brief, brief_path(slug))
    write_raid(slug, {"engagement": slug, "items": []})
    data = {
        "engagement": slug,
        "status": "draft",
        "created": _now(),
        "current": "0.0.0",
        "history": [],
    }
    write_version(slug, data)
    return data


# ----------------------------------------------------------------- plan I/O


def read_plan(slug: str) -> dict:
    if not plan_path(slug).is_file():
        raise FileNotFoundError(
            f"no plan for '{slug}' — run `delivery plan materialise --engagement {slug}`"
        )
    return load_yaml(plan_path(slug).read_text())


def write_plan(slug: str, data: dict) -> dict:
    """Validate against plan.schema.json, stamp provenance, write."""
    errs = _validate("plan", data)
    if errs:
        raise ValueError("invalid plan:\n  " + "\n  ".join(errs))
    if not engagement_exists(slug):
        raise FileNotFoundError(
            f"no engagement '{slug}' — run `delivery plan new --engagement {slug}`"
        )
    data = dict(data)
    data["engagement"] = slug
    data.setdefault("provenance", {})["materialised"] = _now()
    data["provenance"].setdefault("materialised_by", "delivery-studio")
    plan_path(slug).write_text(yaml.safe_dump(data, sort_keys=False))
    return data


def validate_plan_payload(data: dict) -> list[str]:
    """Validate a plan payload without persisting (skill-side use)."""
    return _validate("plan", data)


# ----------------------------------------------------------------- RAID I/O


def read_raid(slug: str) -> dict:
    if not raid_path(slug).is_file():
        # An engagement always has a raid.yml (scaffold wrote one); if it's
        # missing, the engagement is broken.
        raise FileNotFoundError(
            f"raid.yml missing for engagement '{slug}' (engagement broken?)"
        )
    return load_yaml(raid_path(slug).read_text())


def write_raid(slug: str, data: dict) -> dict:
    errs = _validate("raid", data)
    if errs:
        raise ValueError("invalid raid:\n  " + "\n  ".join(errs))
    raid_path(slug).parent.mkdir(parents=True, exist_ok=True)
    raid_path(slug).write_text(yaml.safe_dump(data, sort_keys=False))
    return data


# ----------------------------------------------------------------- version


def read_version(slug: str) -> dict:
    return json.loads(version_path(slug).read_text())


def write_version(slug: str, data: dict) -> None:
    version_path(slug).parent.mkdir(parents=True, exist_ok=True)
    version_path(slug).write_text(json.dumps(data, indent=2) + "\n")


def bump(slug: str, *, level: str = "patch") -> str:
    """Bump the engagement plan version (semver)."""
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
    root = delivery_root()
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if (p / VERSION_FILE).is_file())
